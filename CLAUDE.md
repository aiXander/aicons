# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a cross-platform application for routing ElevenLabs Conversational AI audio through a virtual audio cable with real-time monitoring. It implements a "Double-Hop" audio architecture:

1. **Agent Loop**: Microphone → ElevenLabs API → Virtual Cable (e.g., BlackHole on macOS, VB-Cable on Windows)
2. **Monitor Loop**: Virtual Cable → Speakers (for verification)

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# List audio devices (required for configuration)
python -m src.device_manager

# Run the application
python -m src.main
```

## Architecture

### Core Components

- **`src/main.py`**: Tkinter UI and session orchestration (`AgentApp` class). Coordinates conversation lifecycle, audio interface, and monitor loop.

- **`src/audio_interface.py`**: Custom `VirtualCableInterface` extending ElevenLabs' `AudioInterface`. Routes mic input to ElevenLabs and agent output to virtual cable. Supports pause/resume with silence injection. Handles mono-to-stereo conversion for multi-channel output devices.

- **`src/monitor_loop.py`**: `AudioMonitor` class provides pass-through from virtual cable to speakers for verification. Uses sounddevice callback-based streaming with underflow warning suppression.

- **`src/config.py`**: Dataclass-based configuration loading from `.env` (API credentials) and `config.yaml` (devices, audio settings). Includes validation helpers.

- **`src/device_manager.py`**: Cross-platform audio device discovery using sounddevice. Run directly to list available devices and get configuration suggestions. Auto-detects common virtual cables (BlackHole, VB-Cable, etc.).

### Configuration Files

- **`.env`**: Contains `ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID`
- **`config.yaml`**: Device IDs (mic, cable, speaker), audio settings (sample_rate: 16000, channels: 1, output_channels: 2, dtype: int16), UI settings, debug flags

### Audio Flow

Input audio uses PCM int16 at 16kHz mono. Output converts to stereo when `output_channels: 2` (required for most virtual cables). The input stream captures mic audio and sends bytes to ElevenLabs. The output stream writes received agent audio to the virtual cable with automatic mono-to-stereo duplication. The monitor stream (optional) passes virtual cable audio to speakers.

### Key Implementation Details

- **Mono-to-Stereo Conversion**: ElevenLabs outputs mono audio. When `output_channels > channels`, the audio is duplicated across channels using `np.column_stack()` for compatibility with stereo virtual cables.
- **Queue-based Output**: Non-blocking audio output using `queue.Queue` to prevent blocking on device writes.
- **Pause Implementation**: Sends silence instead of mic audio while keeping the ElevenLabs connection active.

## Key Dependencies

- `elevenlabs>=1.0.0`: Conversational AI SDK
- `sounddevice>=0.4.6`: PortAudio bindings for cross-platform audio I/O
- `numpy`, `python-dotenv`, `PyYAML`
- Tkinter (standard library) for UI

## Platform-Specific Setup

### macOS (BlackHole)
```bash
brew install blackhole-2ch
```

### Windows (VB-Cable)
Download from [VB-Audio](https://vb-audio.com/Cable/)

### Linux (PulseAudio)
```bash
# Create a virtual sink
pactl load-module module-null-sink sink_name=VirtualCable sink_properties=device.description=VirtualCable
```
