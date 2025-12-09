"""
Configuration Loader - Handles loading and validation of app configuration.

Loads settings from:
1. .env file (API keys and secrets)
2. config.yaml (device IDs, audio settings, UI settings)
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import yaml
from dotenv import load_dotenv


@dataclass
class DeviceConfig:
    """Audio device configuration."""

    mic_id: Optional[int]
    cable_id: Optional[int]
    speaker_id: Optional[int]


@dataclass
class AudioConfig:
    """Audio stream settings."""

    sample_rate: int
    channels: int
    dtype: str
    buffer_size: int


@dataclass
class UIConfig:
    """UI window settings."""

    window_title: str
    window_width: int
    window_height: int


@dataclass
class DebugConfig:
    """Debug and logging settings."""

    verbose_audio: bool
    print_transcripts: bool


@dataclass
class AppConfig:
    """Complete application configuration."""

    # API credentials (from .env)
    api_key: str
    agent_id: str

    # Settings (from config.yaml)
    devices: DeviceConfig
    audio: AudioConfig
    ui: UIConfig
    debug: DebugConfig


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""

    pass


def find_project_root() -> Path:
    """Find the project root directory (where config.yaml is located)."""
    # Start from current file's directory
    current = Path(__file__).parent.parent

    # Look for config.yaml
    if (current / "config.yaml").exists():
        return current

    # Try current working directory
    cwd = Path.cwd()
    if (cwd / "config.yaml").exists():
        return cwd

    # Try parent of cwd
    if (cwd.parent / "config.yaml").exists():
        return cwd.parent

    raise ConfigError(
        "Could not find config.yaml. Make sure you're running from the project directory."
    )


def load_config(
    config_path: Optional[str] = None, env_path: Optional[str] = None
) -> AppConfig:
    """
    Load application configuration from files.

    Args:
        config_path: Path to config.yaml (auto-detected if None)
        env_path: Path to .env file (auto-detected if None)

    Returns:
        AppConfig with all settings loaded

    Raises:
        ConfigError: If required configuration is missing or invalid
    """
    # Find project root
    project_root = find_project_root()

    # Load .env file
    env_file = Path(env_path) if env_path else project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        # Try loading from environment anyway
        load_dotenv()

    # Get API credentials from environment
    api_key = os.getenv("ELEVENLABS_API_KEY")
    agent_id = os.getenv("ELEVENLABS_AGENT_ID")

    if not api_key:
        raise ConfigError(
            "ELEVENLABS_API_KEY not found. "
            "Create a .env file with your API key or set the environment variable."
        )

    if not agent_id:
        raise ConfigError(
            "ELEVENLABS_AGENT_ID not found. "
            "Create a .env file with your agent ID or set the environment variable."
        )

    # Load config.yaml
    config_file = Path(config_path) if config_path else project_root / "config.yaml"

    if not config_file.exists():
        raise ConfigError(f"Config file not found: {config_file}")

    with open(config_file, "r") as f:
        yaml_config = yaml.safe_load(f)

    # Parse device config
    devices_yaml = yaml_config.get("devices", {})
    devices = DeviceConfig(
        mic_id=devices_yaml.get("mic_id"),
        cable_id=devices_yaml.get("cable_id"),
        speaker_id=devices_yaml.get("speaker_id"),
    )

    # Parse audio config
    audio_yaml = yaml_config.get("audio", {})
    audio = AudioConfig(
        sample_rate=audio_yaml.get("sample_rate", 16000),
        channels=audio_yaml.get("channels", 1),
        dtype=audio_yaml.get("dtype", "int16"),
        buffer_size=audio_yaml.get("buffer_size", 1024),
    )

    # Parse UI config
    ui_yaml = yaml_config.get("ui", {})
    ui = UIConfig(
        window_title=ui_yaml.get("window_title", "ElevenLabs Agent Controller"),
        window_width=ui_yaml.get("window_width", 400),
        window_height=ui_yaml.get("window_height", 300),
    )

    # Parse debug config
    debug_yaml = yaml_config.get("debug", {})
    debug = DebugConfig(
        verbose_audio=debug_yaml.get("verbose_audio", False),
        print_transcripts=debug_yaml.get("print_transcripts", True),
    )

    return AppConfig(
        api_key=api_key,
        agent_id=agent_id,
        devices=devices,
        audio=audio,
        ui=ui,
        debug=debug,
    )


def validate_config(config: AppConfig) -> tuple[bool, list[str]]:
    """
    Validate the configuration for completeness.

    Args:
        config: AppConfig to validate

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    errors = []

    # Check device IDs
    if config.devices.mic_id is None:
        errors.append("devices.mic_id is not configured in config.yaml")
    if config.devices.cable_id is None:
        errors.append("devices.cable_id is not configured in config.yaml")
    if config.devices.speaker_id is None:
        errors.append("devices.speaker_id is not configured in config.yaml")

    # Check audio settings
    if config.audio.sample_rate <= 0:
        errors.append("audio.sample_rate must be positive")
    if config.audio.channels <= 0:
        errors.append("audio.channels must be positive")

    return len(errors) == 0, errors


def print_config(config: AppConfig) -> None:
    """Print the current configuration (masking sensitive values)."""
    print("\n" + "=" * 50)
    print("CURRENT CONFIGURATION")
    print("=" * 50)

    print(f"\nAPI Key: {'*' * 8}...{config.api_key[-4:] if len(config.api_key) > 4 else '****'}")
    print(f"Agent ID: {config.agent_id}")

    print("\nDevices:")
    print(f"  Microphone ID: {config.devices.mic_id}")
    print(f"  Cable ID: {config.devices.cable_id}")
    print(f"  Speaker ID: {config.devices.speaker_id}")

    print("\nAudio Settings:")
    print(f"  Sample Rate: {config.audio.sample_rate} Hz")
    print(f"  Channels: {config.audio.channels}")
    print(f"  Data Type: {config.audio.dtype}")
    print(f"  Buffer Size: {config.audio.buffer_size}")

    print("\nDebug Settings:")
    print(f"  Verbose Audio: {config.debug.verbose_audio}")
    print(f"  Print Transcripts: {config.debug.print_transcripts}")

    print("=" * 50 + "\n")
