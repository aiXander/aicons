# AICONS - ElevenLabs Virtual Audio Router

A cross-platform application for routing ElevenLabs Conversational AI audio through a virtual audio cable with real-time monitoring capabilities.

## Overview

This project implements a "Double-Hop" audio architecture:

1. **Agent Loop**: Microphone → ElevenLabs API → Virtual Cable
2. **Monitor Loop**: Virtual Cable → Speakers (for verification)

The monitor loop allows you to hear what's being sent to the virtual cable. When deploying to production (e.g., Unreal Engine), you simply disable the monitor loop and connect your target application to the virtual cable.

## Prerequisites

### 1. Virtual Audio Driver

#### macOS (BlackHole)
```bash
brew install blackhole-2ch
```
Or download directly from [BlackHole GitHub](https://github.com/ExistentialAudio/BlackHole).

#### Windows (VB-Cable)
Download and install from [VB-Audio](https://vb-audio.com/Cable/).

#### Linux (PulseAudio/PipeWire)
```bash
# PulseAudio: Create a virtual sink
pactl load-module module-null-sink sink_name=VirtualCable sink_properties=device.description=VirtualCable

# To make it persistent, add to /etc/pulse/default.pa:
# load-module module-null-sink sink_name=VirtualCable sink_properties=device.description=VirtualCable
```

### 2. Python Environment

Requires Python 3.10 or higher.

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

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
git clone <repository-url>
cd AICONS

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

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

DETECTED VIRTUAL CABLES:
  - BlackHole 2ch (ID: 2)

CONFIGURATION INSTRUCTIONS
Update your config.yaml with these device IDs:
devices:
  mic_id: 0      # MacBook Pro Microphone
  cable_id: 2    # BlackHole 2ch
  speaker_id: 1  # MacBook Pro Speakers
```

### Step 4: Configure Device IDs

Edit `config.yaml` with your device IDs:

```yaml
devices:
  mic_id: 0        # Your microphone ID
  cable_id: 2      # Virtual cable ID (BlackHole/VB-Cable)
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
  cable_id: null    # Virtual cable output device ID
  speaker_id: null  # Speaker output device ID for monitoring
```

#### Audio Settings
```yaml
audio:
  sample_rate: 16000    # Hz (ElevenLabs standard)
  channels: 1           # Input channels (1 = mono for ElevenLabs)
  output_channels: 2    # Output channels (2 for stereo virtual cables)
  dtype: int16          # PCM 16-bit
  buffer_size: 1024     # Frames per buffer
```

**Note**: Most virtual cables (BlackHole 2ch, VB-Cable) require stereo output (`output_channels: 2`). The application automatically converts mono audio from ElevenLabs to stereo by duplicating the channel.

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
AICONS/
├── .env.example          # Example environment file
├── .env                  # Your API credentials (create this)
├── config.yaml           # Application configuration
├── requirements.txt      # Python dependencies
├── README.md             # This file
├── CLAUDE.md             # Developer guidance for Claude AI
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
│  Microphone │ ──► │  ElevenLabs  │ ──► │   Virtual   │
│   (Input)   │     │     API      │     │    Cable    │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
                                         ┌─────────────┐
                                         │   Speakers  │
                                         │  (Monitor)  │
                                         └─────────────┘
```

### Component Responsibilities

- **`device_manager.py`**: Cross-platform audio device discovery and identification
- **`audio_interface.py`**: Custom ElevenLabs `AudioInterface` for device routing with mono-to-stereo conversion
- **`monitor_loop.py`**: Pass-through from virtual cable to speakers
- **`config.py`**: Loads and validates configuration
- **`main.py`**: Tkinter UI and session orchestration

## Troubleshooting

### "Virtual cable not found"

**macOS:**
```bash
brew install blackhole-2ch
# Restart audio services:
sudo launchctl kickstart -kp system/com.apple.audio.coreaudiod
```

**Windows:**
Download and install [VB-Cable](https://vb-audio.com/Cable/), then restart your computer.

**Linux:**
```bash
pactl load-module module-null-sink sink_name=VirtualCable sink_properties=device.description=VirtualCable
```

### "No audio heard through speakers"

1. Check that `cable_id` in config.yaml matches your virtual cable's ID
2. Verify `output_channels` matches your virtual cable (usually 2 for stereo)
3. Verify the virtual cable is set to the same sample rate (16000 Hz or configure accordingly)
4. Check your OS sound settings to ensure the correct output device is selected

### "Microphone not capturing"

1. Grant microphone permission to Terminal/your IDE
   - **macOS**: System Preferences → Security & Privacy → Microphone
   - **Windows**: Settings → Privacy → Microphone
   - **Linux**: Check PulseAudio/PipeWire permissions
2. Verify `mic_id` matches your microphone in `config.yaml`

### "Connection errors"

1. Verify your API key is correct in `.env`
2. Check your internet connection
3. Verify the Agent ID exists in your ElevenLabs dashboard

### Sample Rate Mismatch

If you hear distorted audio, ensure all components use the same sample rate:
1. Check virtual cable sample rate in your OS audio settings
2. Match `audio.sample_rate` in config.yaml
3. ElevenLabs typically uses 16000 Hz

### Mono/Stereo Issues

If audio is only playing in one ear or sounds distorted:
1. Check `output_channels` in config.yaml matches your virtual cable
2. Most virtual cables are stereo (`output_channels: 2`)
3. The app automatically converts mono ElevenLabs audio to stereo

## Production Deployment

When moving to production (e.g., Unreal Engine integration):

1. Remove or don't start the monitor loop
2. Configure the target application to read from the virtual cable
3. Audio flows: Mic → ElevenLabs → Virtual Cable → Target Application

## License

MIT License - See LICENSE file for details.
