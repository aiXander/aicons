# Loopback MVP

A macOS application for routing ElevenLabs Conversational AI audio through a virtual audio cable (BlackHole) with real-time monitoring capabilities.

## Overview

This project implements a "Double-Hop" audio architecture:

1. **Agent Loop**: Microphone → ElevenLabs API → BlackHole (Virtual Cable)
2. **Monitor Loop**: BlackHole → MacBook Speakers (for verification)

The monitor loop allows you to hear what's being sent to the virtual cable. When deploying to production (e.g., Unreal Engine on Windows), you simply disable the monitor loop.

## Prerequisites

### 1. Install BlackHole (Virtual Audio Driver)

```bash
brew install blackhole-2ch
```

Or download directly from [BlackHole GitHub](https://github.com/ExistentialAudio/BlackHole).

### 2. Python Environment

Requires Python 3.10 or higher.

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. ElevenLabs Account

- Sign up at [ElevenLabs](https://elevenlabs.io/)
- Create a Conversational AI Agent
- Get your API key and Agent ID

## Quick Start

### Step 1: Clone and Setup

```bash
cd loopback_mvp

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure API Credentials

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

Add your ElevenLabs credentials:
```
ELEVENLABS_API_KEY=your_actual_api_key_here
ELEVENLABS_AGENT_ID=your_actual_agent_id_here
```

### Step 3: Find Your Audio Device IDs

```bash
python -m src.device_manager
```

This will output something like:
```
--- INPUT DEVICES (Microphones) ---
  ID  0: MacBook Pro Microphone
          Channels: 1, Sample Rate: 48000 Hz

--- OUTPUT DEVICES (Speakers/Virtual Cables) ---
  ID  1: MacBook Pro Speakers
          Channels: 2, Sample Rate: 48000 Hz
  ID  2: BlackHole 2ch
          Channels: 2, Sample Rate: 48000 Hz
```

### Step 4: Configure Device IDs

Edit `config.yaml` with your device IDs:

```yaml
devices:
  mic_id: 0        # Your microphone ID
  cable_id: 2      # BlackHole 2ch ID
  speaker_id: 1    # Your speakers ID
```

### Step 5: Run the Application

```bash
python -m src.main
```

## Usage

### UI Controls

- **Start Conversation**: Connects to ElevenLabs and begins the audio session
- **Pause Audio**: Mutes the microphone (sends silence) without disconnecting
- **Stop Conversation**: Ends the session and resets everything

### Status Indicators

- **READY** (Gray): Application initialized, ready to start
- **CONNECTING** (Orange): Establishing connection to ElevenLabs
- **LIVE** (Green): Active conversation in progress
- **PAUSED** (Blue): Audio muted but session still active
- **STOPPED** (Red): Session ended
- **ERROR** (Red): An error occurred

## Configuration Reference

### `.env` - API Credentials

| Variable | Description |
|----------|-------------|
| `ELEVENLABS_API_KEY` | Your ElevenLabs API key |
| `ELEVENLABS_AGENT_ID` | Your Conversational AI Agent ID |

### `config.yaml` - Application Settings

#### Devices
```yaml
devices:
  mic_id: null      # Microphone input device ID
  cable_id: null    # Virtual cable output (BlackHole) device ID
  speaker_id: null  # Speaker output device ID for monitoring
```

#### Audio Settings
```yaml
audio:
  sample_rate: 16000  # Hz (ElevenLabs standard)
  channels: 1         # Mono
  dtype: int16        # PCM 16-bit
  buffer_size: 1024   # Frames per buffer
```

#### UI Settings
```yaml
ui:
  window_title: "ElevenLabs Agent Controller"
  window_width: 400
  window_height: 300
```

#### Debug Settings
```yaml
debug:
  verbose_audio: false     # Print audio stream status
  print_transcripts: true  # Print conversation to console
```

## Project Structure

```
loopback_mvp/
├── .env.example          # Example environment file
├── .env                  # Your API credentials (create this)
├── config.yaml           # Application configuration
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── src/
    ├── __init__.py
    ├── config.py         # Configuration loader
    ├── device_manager.py # Audio device discovery
    ├── audio_interface.py # ElevenLabs audio handler
    ├── monitor_loop.py   # Virtual cable → speakers
    └── main.py           # UI and orchestration
```

## Architecture

### The "Double-Hop" Design

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Microphone │ ──► │  ElevenLabs  │ ──► │  BlackHole  │
│   (Input)   │     │     API      │     │   (Cable)   │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                 │
                                                 ▼
                                         ┌─────────────┐
                                         │   Speakers  │
                                         │  (Monitor)  │
                                         └─────────────┘
```

### Component Responsibilities

- **`device_manager.py`**: Scans and identifies audio devices
- **`audio_interface.py`**: Custom ElevenLabs `AudioInterface` for device routing
- **`monitor_loop.py`**: Pass-through from virtual cable to speakers
- **`config.py`**: Loads and validates configuration
- **`main.py`**: Tkinter UI and session orchestration

## Troubleshooting

### "BlackHole not found"

Ensure BlackHole is installed:
```bash
brew install blackhole-2ch
```

After installation, restart your Mac or run:
```bash
sudo launchctl kickstart -kp system/com.apple.audio.coreaudiod
```

### "No audio heard through speakers"

1. Check that `cable_id` in config.yaml matches BlackHole's ID
2. Verify BlackHole is set to the same sample rate (16000 Hz or configure accordingly)
3. Check macOS System Preferences → Sound → Output is set correctly

### "Microphone not capturing"

1. Grant microphone permission to Terminal/your IDE
2. System Preferences → Security & Privacy → Microphone
3. Verify `mic_id` matches your microphone in `config.yaml`

### "Connection errors"

1. Verify your API key is correct in `.env`
2. Check your internet connection
3. Verify the Agent ID exists in your ElevenLabs dashboard

### Sample Rate Mismatch

If you hear distorted audio, ensure all components use the same sample rate:
1. Check BlackHole sample rate in Audio MIDI Setup
2. Match `audio.sample_rate` in config.yaml
3. ElevenLabs typically uses 16000 Hz

## Production Deployment

When moving to production (e.g., Unreal Engine integration):

1. Remove or don't start the monitor loop
2. Configure the target application to read from BlackHole
3. Audio flows: Mic → ElevenLabs → BlackHole → Target Application

## License

MIT License - See LICENSE file for details.
