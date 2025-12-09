# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AICONS is a cross-platform desktop application for routing ElevenLabs Conversational AI audio through a virtual audio cable with real-time monitoring. It implements a "Double-Hop" audio architecture:

1. **Agent Loop**: Microphone → ElevenLabs API → Virtual Cable (e.g., BlackHole on macOS, VB-Cable on Windows)
2. **Monitor Loop**: Virtual Cable → Speakers (for verification)

The primary use case is integration with applications like Unreal Engine that require audio input from a virtual device.

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

## Project Structure

```
AICONS/
├── .env.example          # Template for API credentials
├── .env                  # API credentials (create from .env.example)
├── config.yaml           # Application configuration
├── requirements.txt      # Python dependencies
├── assets/
│   └── img.jpeg          # Profile image for UI
└── src/
    ├── __init__.py       # Package marker
    ├── main.py           # Application entry point & business logic
    ├── ui.py             # Tkinter UI components (dark purple theme)
    ├── config.py         # Configuration loading & validation
    ├── audio_interface.py # Custom ElevenLabs audio handler
    ├── monitor_loop.py   # Virtual cable → speakers pass-through
    └── device_manager.py # Cross-platform audio device discovery
```

## Architecture

### Core Components

- **`src/main.py`**: Application entry point and business logic (`AgentApp` class). Coordinates conversation lifecycle, audio interface, and monitor loop. Sets up logging to the debug panel via custom `TextHandler`.

- **`src/ui.py`**: Complete Tkinter UI with modern dark purple theme (`AgentUI` class). Includes:
  - `Theme` class with color palette constants
  - `TextHandler` for logging to Tkinter Text widgets
  - `UICallbacks` dataclass for event callbacks
  - Status indicator with color-coded states (READY, CONNECTING, LIVE, PAUSED, STOPPING, STOPPED, ERROR)
  - Conversation log with timestamped, color-coded messages (user/agent)
  - Collapsible debug log panel
  - Profile image display with center-crop-to-square
  - Platform-specific window handling (fullscreen on Windows/Linux, windowed on macOS)

- **`src/audio_interface.py`**: Custom `VirtualCableInterface` extending ElevenLabs' `AudioInterface`. Routes mic input to ElevenLabs and agent output to virtual cable. Supports pause/resume with silence injection. Handles mono-to-stereo conversion for multi-channel output devices. Includes `wait_until_ready()` for stream synchronization.

- **`src/monitor_loop.py`**: `AudioMonitor` class provides pass-through from virtual cable to speakers for verification. Uses sounddevice callback-based streaming with underflow warning suppression. `MonitorThread` wrapper for background execution.

- **`src/config.py`**: Dataclass-based configuration loading from `.env` (API credentials) and `config.yaml` (devices, audio settings). Includes three-stage validation: file existence, device capability checks, and audio settings validation.

- **`src/device_manager.py`**: Cross-platform audio device discovery using sounddevice. Run directly to list available devices and get configuration suggestions. Auto-detects common virtual cables (BlackHole, VB-Cable, VoiceMeeter, PulseAudio, PipeWire).

### Configuration Files

- **`.env`**: Contains `ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID`
- **`config.yaml`**: Device IDs (mic, cable, speaker), audio settings (sample_rate: 16000, channels: 1, output_channels: 2, dtype: int16, buffer_size: 1024), UI settings, debug flags

### Audio Flow

Input audio uses PCM int16 at 16kHz mono. Output converts to stereo when `output_channels: 2` (required for most virtual cables). The input stream captures mic audio and sends bytes to ElevenLabs. The output stream writes received agent audio to the virtual cable with automatic mono-to-stereo duplication. The monitor stream (optional) passes virtual cable audio to speakers.

### Key Implementation Details

- **UI/Logic Separation**: UI components (`ui.py`) are completely separated from business logic (`main.py`) using a callback pattern via `UICallbacks` dataclass.
- **Mono-to-Stereo Conversion**: ElevenLabs outputs mono audio. When `output_channels > channels`, the audio is duplicated across channels using `np.column_stack()` for compatibility with stereo virtual cables.
- **Queue-based Output**: Non-blocking audio output using `queue.Queue` to prevent blocking on device writes.
- **Pause Implementation**: Sends silence instead of mic audio while keeping the ElevenLabs connection active.
- **Stream Readiness**: `wait_until_ready()` method on audio interface coordinates startup timing between components.
- **Monitor Startup Order**: Monitor is started BEFORE audio interface to avoid macOS CoreAudio race conditions.
- **Logging Integration**: Custom `TextHandler` pipes Python logging to the debug panel with level-based color coding.
- **Focus Handling**: Platform-specific focus handling for macOS to ensure proper click-through behavior.

### Threading Model

- **Main Thread**: Tkinter event loop + UI updates
- **Audio Input Thread**: sounddevice's internal thread for input callback
- **Audio Output Thread**: Background thread writing queued audio to device
- **Monitor Thread**: Optional background thread for monitor loop
- **Conversation Thread**: ElevenLabs SDK's internal thread

## Key Dependencies

- `elevenlabs>=1.0.0`: Conversational AI SDK
- `sounddevice>=0.4.6`: PortAudio bindings for cross-platform audio I/O
- `numpy>=1.24.0`: Audio array processing
- `python-dotenv>=1.0.0`: Environment file loading
- `PyYAML>=6.0`: Configuration parsing
- `Pillow>=10.0.0`: Image processing for profile display
- Tkinter (standard library): GUI framework

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

## UI Theme

The application uses a dark purple theme with the following color scheme:
- **Primary background**: `#0d0d14` (deep dark purple-black)
- **Panel background**: `#13131f`
- **Status colors**: Green (LIVE), Blue (PAUSED), Orange (CONNECTING), Red (ERROR/STOPPED)
- **Font**: SF Pro Display (macOS) or system default
