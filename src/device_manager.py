"""
Device Manager - Audio device discovery and identification.

Run this module directly to list all available audio devices:
    python -m src.device_manager
"""

import sounddevice as sd
from typing import Optional


def list_devices() -> None:
    """List all available audio devices with their properties."""
    print("\n" + "=" * 60)
    print("AUDIO DEVICES")
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

    # Try to auto-detect common devices
    blackhole = find_device_by_name("blackhole", "output")
    speakers = find_device_by_name("macbook", "output") or find_device_by_name("speaker", "output")
    mic = find_device_by_name("macbook", "input") or find_device_by_name("microphone", "input")

    print("\nUpdate your config.yaml with these device IDs:")
    print("\ndevices:")

    if mic is not None:
        dev = sd.query_devices(mic)
        print(f"  mic_id: {mic}      # {dev['name']}")
    else:
        print("  mic_id: <YOUR_MIC_ID>      # Find your microphone above")

    if blackhole is not None:
        dev = sd.query_devices(blackhole)
        print(f"  cable_id: {blackhole}    # {dev['name']}")
    else:
        print("  cable_id: <BLACKHOLE_ID>   # Install BlackHole: brew install blackhole-2ch")

    if speakers is not None:
        dev = sd.query_devices(speakers)
        print(f"  speaker_id: {speakers}  # {dev['name']}")
    else:
        print("  speaker_id: <SPEAKER_ID>   # Find your speakers above")

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
