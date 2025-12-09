"""
Device Manager - Cross-platform audio device discovery and identification.

Run this module directly to list all available audio devices:
    python -m src.device_manager
"""

import sounddevice as sd
import platform
from typing import Optional

# Common virtual cable device names by platform
VIRTUAL_CABLE_NAMES = [
    # macOS
    "blackhole",
    # Windows
    "cable",  # VB-Cable shows as "CABLE Input" / "CABLE Output"
    "vb-audio",
    "virtual cable",
    "voicemeeter",
    # Linux
    "virtualcable",
    "null",  # PulseAudio null sink
    "pipewire",  # PipeWire virtual devices
]

# Common microphone names by platform
MICROPHONE_NAMES = [
    # macOS
    "macbook",
    "built-in",
    # Windows
    "microphone",
    "realtek",
    "high definition audio",
    # Linux
    "capture",
    "input",
    "alsa",
]

# Common speaker names by platform
SPEAKER_NAMES = [
    # macOS
    "macbook",
    "built-in",
    "speakers",
    # Windows
    "speakers",
    "realtek",
    "high definition audio",
    # Linux
    "output",
    "playback",
    "alsa",
]


def get_platform_info() -> str:
    """Get current platform information."""
    return f"{platform.system()} {platform.release()}"


def list_devices() -> None:
    """List all available audio devices with their properties."""
    print("\n" + "=" * 60)
    print(f"AUDIO DEVICES ({get_platform_info()})")
    print("=" * 60)

    devices = sd.query_devices()

    # Separate input and output devices for clearer display
    input_devices = []
    output_devices = []

    for i, device in enumerate(devices):
        device_info = {
            "id": i,
            "name": device["name"],
            "inputs": device["max_input_channels"],
            "outputs": device["max_output_channels"],
            "default_sr": device["default_samplerate"],
        }

        if device["max_input_channels"] > 0:
            input_devices.append(device_info)
        if device["max_output_channels"] > 0:
            output_devices.append(device_info)

    print("\n--- INPUT DEVICES (Microphones) ---")
    for dev in input_devices:
        print(f"  ID {dev['id']:2d}: {dev['name']}")
        print(f"          Channels: {dev['inputs']}, Sample Rate: {dev['default_sr']:.0f} Hz")

    print("\n--- OUTPUT DEVICES (Speakers/Virtual Cables) ---")
    for dev in output_devices:
        print(f"  ID {dev['id']:2d}: {dev['name']}")
        print(f"          Channels: {dev['outputs']}, Sample Rate: {dev['default_sr']:.0f} Hz")


def find_device_by_name(name: str, kind: Optional[str] = None) -> Optional[int]:
    """
    Find a device ID by partial name match.

    Args:
        name: Partial name to search for (case-insensitive)
        kind: 'input', 'output', or None for both

    Returns:
        Device ID if found, None otherwise
    """
    devices = sd.query_devices()
    name_lower = name.lower()

    for i, device in enumerate(devices):
        if name_lower in device["name"].lower():
            if kind == "input" and device["max_input_channels"] == 0:
                continue
            if kind == "output" and device["max_output_channels"] == 0:
                continue
            return i

    return None


def find_virtual_cables() -> list[dict]:
    """
    Find all virtual audio cables on the system.

    Returns:
        List of device info dicts for detected virtual cables
    """
    devices = sd.query_devices()
    cables = []

    for i, device in enumerate(devices):
        name_lower = device["name"].lower()
        for cable_name in VIRTUAL_CABLE_NAMES:
            if cable_name in name_lower and device["max_output_channels"] > 0:
                cables.append({
                    "id": i,
                    "name": device["name"],
                    "channels": device["max_output_channels"],
                    "sample_rate": device["default_samplerate"],
                })
                break

    return cables


def get_device_info(device_id: int) -> dict:
    """Get detailed information about a specific device."""
    device = sd.query_devices(device_id)
    return {
        "id": device_id,
        "name": device["name"],
        "max_input_channels": device["max_input_channels"],
        "max_output_channels": device["max_output_channels"],
        "default_samplerate": device["default_samplerate"],
        "default_low_input_latency": device.get("default_low_input_latency"),
        "default_low_output_latency": device.get("default_low_output_latency"),
    }


def print_configuration_help() -> None:
    """Print instructions for configuring the application."""
    print("\n" + "=" * 60)
    print("CONFIGURATION INSTRUCTIONS")
    print("=" * 60)

    # Detect virtual cables
    cables = find_virtual_cables()
    if cables:
        print("\nDETECTED VIRTUAL CABLES:")
        for cable in cables:
            print(f"  - {cable['name']} (ID: {cable['id']}, Channels: {cable['channels']})")
    else:
        print("\nNO VIRTUAL CABLES DETECTED")
        system = platform.system()
        if system == "Darwin":
            print("  Install BlackHole: brew install blackhole-2ch")
        elif system == "Windows":
            print("  Install VB-Cable: https://vb-audio.com/Cable/")
        else:
            print("  Create a virtual sink with PulseAudio:")
            print("  pactl load-module module-null-sink sink_name=VirtualCable")

    # Try to auto-detect common devices
    # Look for virtual cable first
    cable = None
    for cable_name in VIRTUAL_CABLE_NAMES:
        cable = find_device_by_name(cable_name, "output")
        if cable is not None:
            break

    # Look for microphone
    mic = None
    for mic_name in MICROPHONE_NAMES:
        mic = find_device_by_name(mic_name, "input")
        if mic is not None:
            break

    # Look for speakers (exclude virtual cables)
    speakers = None
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        if device["max_output_channels"] > 0:
            name_lower = device["name"].lower()
            # Skip if it's a virtual cable
            is_cable = any(cn in name_lower for cn in VIRTUAL_CABLE_NAMES)
            if not is_cable:
                for speaker_name in SPEAKER_NAMES:
                    if speaker_name in name_lower:
                        speakers = i
                        break
            if speakers is not None:
                break

    print("\nSUGGESTED config.yaml:")
    print("\ndevices:")

    if mic is not None:
        dev = sd.query_devices(mic)
        print(f"  mic_id: {mic}      # {dev['name']}")
    else:
        print("  mic_id: <YOUR_MIC_ID>      # Find your microphone above")

    if cable is not None:
        dev = sd.query_devices(cable)
        print(f"  cable_id: {cable}    # {dev['name']}")
    else:
        print("  cable_id: <CABLE_ID>       # Install a virtual audio cable first")

    if speakers is not None:
        dev = sd.query_devices(speakers)
        print(f"  speaker_id: {speakers}  # {dev['name']}")
    else:
        print("  speaker_id: <SPEAKER_ID>   # Find your speakers above")

    # Print output_channels recommendation based on detected cable
    if cables:
        cable_channels = cables[0]["channels"]
        print(f"\naudio:")
        print(f"  output_channels: {cable_channels}  # Matches {cables[0]['name']}")

    print("\n" + "=" * 60)


def validate_devices(mic_id: int, cable_id: int, speaker_id: int) -> tuple[bool, list[str]]:
    """
    Validate that the configured device IDs are valid.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []
    devices = sd.query_devices()
    num_devices = len(devices)

    # Check mic
    if mic_id is None:
        errors.append("mic_id is not configured")
    elif mic_id >= num_devices:
        errors.append(f"mic_id {mic_id} does not exist")
    elif devices[mic_id]["max_input_channels"] == 0:
        errors.append(f"Device {mic_id} ({devices[mic_id]['name']}) has no input channels")

    # Check cable (needs output)
    if cable_id is None:
        errors.append("cable_id is not configured")
    elif cable_id >= num_devices:
        errors.append(f"cable_id {cable_id} does not exist")
    elif devices[cable_id]["max_output_channels"] == 0:
        errors.append(f"Device {cable_id} ({devices[cable_id]['name']}) has no output channels")

    # Check speaker
    if speaker_id is None:
        errors.append("speaker_id is not configured")
    elif speaker_id >= num_devices:
        errors.append(f"speaker_id {speaker_id} does not exist")
    elif devices[speaker_id]["max_output_channels"] == 0:
        errors.append(f"Device {speaker_id} ({devices[speaker_id]['name']}) has no output channels")

    return len(errors) == 0, errors


if __name__ == "__main__":
    list_devices()
    print_configuration_help()
