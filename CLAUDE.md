# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a macOS application for routing ElevenLabs Conversational AI audio through a virtual audio cable (BlackHole) with real-time monitoring. It implements a "Double-Hop" audio architecture:

1. **Agent Loop**: Microphone → ElevenLabs API → BlackHole (Virtual Cable)
2. **Monitor Loop**: BlackHole → MacBook Speakers (for verification)

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# List audio devices (required for configuration)
python -m src.device_manager

# Run the application
python -m src.main
```

## Architecture

### Core Components

- **`src/main.py`**: Tkinter UI and session orchestration (`AgentApp` class). Coordinates conversation lifecycle, audio interface, and monitor loop.

- **`src/audio_interface.py`**: Custom `VirtualCableInterface` extending ElevenLabs' `AudioInterface`. Routes mic input to ElevenLabs and agent output to BlackHole. Supports pause/resume with silence injection.

- **`src/monitor_loop.py`**: `AudioMonitor` class provides pass-through from BlackHole to speakers for verification. Uses sounddevice callback-based streaming.

- **`src/config.py`**: Dataclass-based configuration loading from `.env` (API credentials) and `config.yaml` (devices, audio settings). Includes validation helpers.

- **`src/device_manager.py`**: Audio device discovery using sounddevice. Run directly to list available devices and get configuration suggestions.

### Configuration Files

- **`.env`**: Contains `ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID`
- **`config.yaml`**: Device IDs (mic, cable, speaker), audio settings (sample_rate: 16000, channels: 1, dtype: int16), UI settings, debug flags

### Audio Flow

All audio uses PCM int16 at 16kHz mono. The input stream captures mic audio and sends bytes to ElevenLabs. The output stream writes received agent audio to BlackHole. The monitor stream (optional) passes BlackHole audio to speakers.

## Key Dependencies

- `elevenlabs>=1.0.0`: Conversational AI SDK
- `sounddevice>=0.4.6`: PortAudio bindings for audio I/O
- `numpy`, `python-dotenv`, `PyYAML`
- Tkinter (standard library) for UI

## Prerequisites

BlackHole virtual audio driver must be installed:
```bash
brew install blackhole-2ch
```
