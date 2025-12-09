"""
Main Application - ElevenLabs Agent Controller.

This module provides the business logic and orchestration for the ElevenLabs
conversational AI agent with virtual cable audio routing.
"""

import tkinter as tk
import sys
import logging
import time
from typing import Optional

from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation

from .config import load_config, validate_config, print_config, AppConfig, ConfigError
from .device_manager import validate_devices
from .audio_interface import VirtualCableInterface
from .monitor_loop import AudioMonitor
from .ui import AgentUI, UICallbacks, TextHandler, Theme


class AgentApp:
    """
    Main application class for the ElevenLabs Agent Controller.

    Manages the conversation session, audio interface, and monitor loop.
    Delegates all UI to the AgentUI class.
    """

    def __init__(self, root: tk.Tk, config: AppConfig):
        """
        Initialize the application.

        Args:
            root: Tkinter root window
            config: Application configuration
        """
        self.root = root
        self.config = config

        # Initialize ElevenLabs client
        self.client = ElevenLabs(api_key=config.api_key)

        # Initialize components (created on start)
        self.conversation: Optional[Conversation] = None
        self.audio_interface: Optional[VirtualCableInterface] = None
        self.monitor: Optional[AudioMonitor] = None

        # Prepare config info for UI display
        config_info = {
            "Agent ID": f"{config.agent_id[:24]}...",
            "Microphone": f"Device {config.devices.mic_id}",
            "Virtual Cable": f"Device {config.devices.cable_id}",
            "Speakers": f"Device {config.devices.speaker_id}",
            "Sample Rate": f"{config.audio.sample_rate} Hz",
        }

        # Create UI callbacks
        callbacks = UICallbacks(
            on_toggle_conversation=self._toggle_conversation,
            on_toggle_pause=self._toggle_pause,
            on_close=self._on_close,
        )

        # Create UI
        self.ui = AgentUI(
            root=root,
            window_title=config.ui.window_title,
            config_info=config_info,
            callbacks=callbacks,
        )

        # Setup logging to debug panel
        self._setup_logging()

        # Log startup
        self.logger.info("Application initialized")
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        self.logger.debug(f"Screen size: {screen_width}x{screen_height}")

    def _setup_logging(self) -> None:
        """Setup logging to write to the debug panel."""
        self.logger = logging.getLogger("AgentApp")
        self.logger.setLevel(logging.DEBUG)

        # Create handler for debug text widget
        text_handler = TextHandler(self.ui.get_debug_log_widget())
        text_handler.setLevel(logging.DEBUG)

        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        text_handler.setFormatter(formatter)

        # Add handler to logger
        self.logger.addHandler(text_handler)

    def _start_conversation(self) -> None:
        """Start the conversation session."""
        try:
            self.ui.update_status("CONNECTING", "connecting")
            self.logger.info("Starting conversation session...")

            # Create audio interface (but don't start yet)
            self.audio_interface = VirtualCableInterface(
                input_device_id=self.config.devices.mic_id,
                output_device_id=self.config.devices.cable_id,
                sample_rate=self.config.audio.sample_rate,
                channels=self.config.audio.channels,
                output_channels=self.config.audio.output_channels,
                dtype=self.config.audio.dtype,
                buffer_size=self.config.audio.buffer_size,
                verbose=self.config.debug.verbose_audio,
            )
            self.logger.debug("Audio interface created")

            # Create monitor loop (but don't start yet - will be started after conversation)
            self.monitor = AudioMonitor(
                input_device_id=self.config.devices.cable_id,
                output_device_id=self.config.devices.speaker_id,
                sample_rate=self.config.audio.sample_rate,
                channels=self.config.audio.output_channels,
                dtype=self.config.audio.dtype,
                buffer_size=self.config.audio.buffer_size,
                verbose=self.config.debug.verbose_audio,
            )
            self.logger.debug("Monitor created")

            # Create conversation callbacks
            def on_agent_response(response: str) -> None:
                self.ui.add_conversation_message("agent", response)
                if self.config.debug.print_transcripts:
                    self.logger.debug(f"Agent response received: {len(response)} chars")

            def on_user_transcript(transcript: str) -> None:
                self.ui.add_conversation_message("user", transcript)
                if self.config.debug.print_transcripts:
                    self.logger.debug(f"User transcript received: {len(transcript)} chars")

            # Create conversation
            self.conversation = Conversation(
                client=self.client,
                agent_id=self.config.agent_id,
                requires_auth=True,
                audio_interface=self.audio_interface,
                callback_agent_response=on_agent_response,
                callback_user_transcript=on_user_transcript,
            )
            self.logger.debug("Conversation object created")

            # Start session (runs in background, non-blocking)
            self.conversation.start_session()
            self.logger.info("Session started successfully")

            # Small delay to let audio streams stabilize before starting monitor
            # This helps avoid macOS CoreAudio context errors
            time.sleep(0.3)

            # Now start the monitor loop (after conversation's audio interface is running)
            self.monitor.start()
            self.logger.debug("Monitor loop started")

            # Update UI
            self.ui.update_status("LIVE", "live")
            self.ui.set_conversation_running(True)

        except Exception as e:
            self.logger.error(f"Failed to start conversation: {e}")
            self._handle_error(str(e))

    def _toggle_conversation(self) -> None:
        """Toggle between starting and stopping conversation."""
        if self.ui.conversation_running:
            self._stop_conversation()
        else:
            self._start_conversation()

    def _toggle_pause(self) -> None:
        """Toggle pause state of audio interface."""
        if self.audio_interface:
            is_paused = self.audio_interface.toggle_pause()

            if is_paused:
                self.ui.update_status("PAUSED", "paused")
                self.ui.set_paused(True)
                self.logger.info("Audio paused")
            else:
                self.ui.update_status("LIVE", "live")
                self.ui.set_paused(False)
                self.logger.info("Audio resumed")

    def _stop_conversation(self) -> None:
        """Stop the conversation session."""
        self.ui.update_status("STOPPING", "stopping")
        self.logger.info("Stopping conversation...")

        # End conversation session
        if self.conversation:
            try:
                self.conversation.end_session()
                self.logger.debug("Conversation session ended")
            except Exception as e:
                self.logger.warning(f"Error ending session: {e}")
            self.conversation = None

        # Stop monitor
        if self.monitor:
            self.monitor.stop()
            self.logger.debug("Monitor stopped")
            self.monitor = None

        # Clean up audio interface
        self.audio_interface = None

        # Reset UI
        self.ui.update_status("STOPPED", "stopped")
        self.ui.set_conversation_running(False)
        self.logger.info("Conversation stopped")

    def _handle_error(self, error: str) -> None:
        """Handle errors during conversation."""
        self.ui.update_status("ERROR", "error")
        self.ui.set_conversation_running(False)
        self.logger.error(f"Error: {error}")
        self.ui.show_error("Error", f"An error occurred:\n\n{error}")

    def _on_close(self) -> None:
        """Handle window close event."""
        self.logger.info("Application closing...")
        if self.conversation:
            self._stop_conversation()
        self.ui.destroy()


def main() -> None:
    """Main entry point for the application."""
    print("\n" + "=" * 50)
    print("ElevenLabs Agent Controller")
    print("=" * 50)

    # Load configuration
    try:
        config = load_config()
    except ConfigError as e:
        print(f"\n[Config Error] {e}")
        print("\nPlease check your configuration files:")
        print("  1. Copy .env.example to .env and add your API credentials")
        print("  2. Run 'python -m src.device_manager' to find device IDs")
        print("  3. Update config.yaml with the correct device IDs")
        sys.exit(1)

    # Validate configuration
    is_valid, errors = validate_config(config)
    if not is_valid:
        print("\n[Config Error] Invalid configuration:")
        for error in errors:
            print(f"  - {error}")
        print("\nRun 'python -m src.device_manager' to find your device IDs")
        sys.exit(1)

    # Validate audio devices
    devices_valid, device_errors = validate_devices(
        config.devices.mic_id,
        config.devices.cable_id,
        config.devices.speaker_id,
    )
    if not devices_valid:
        print("\n[Device Error] Invalid device configuration:")
        for error in device_errors:
            print(f"  - {error}")
        print("\nRun 'python -m src.device_manager' to see available devices")
        sys.exit(1)

    # Print configuration (if debug enabled)
    if config.debug.verbose_audio:
        print_config(config)

    print("\nStarting application...")
    print("Press Start Conversation to begin.\n")

    # Create and run application
    root = tk.Tk()
    app = AgentApp(root, config)
    root.mainloop()


if __name__ == "__main__":
    main()
