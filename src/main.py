"""
Main Application - ElevenLabs Agent Controller UI.

This module provides a Tkinter-based UI for controlling the ElevenLabs
conversational AI agent with virtual cable audio routing.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sys
from typing import Optional

from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation

from .config import load_config, validate_config, print_config, AppConfig, ConfigError
from .device_manager import validate_devices
from .audio_interface import VirtualCableInterface
from .monitor_loop import AudioMonitor


class AgentApp:
    """
    Main application class for the ElevenLabs Agent Controller.

    Manages the UI and orchestrates the conversation session,
    audio interface, and monitor loop.
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

        # Configure window
        self.root.title(config.ui.window_title)
        self.root.geometry(f"{config.ui.window_width}x{config.ui.window_height}")
        self.root.resizable(False, False)

        # Initialize ElevenLabs client
        self.client = ElevenLabs(api_key=config.api_key)

        # Initialize components (created on start)
        self.conversation: Optional[Conversation] = None
        self.audio_interface: Optional[VirtualCableInterface] = None
        self.monitor: Optional[AudioMonitor] = None

        # Build UI
        self._build_ui()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        """Build the user interface."""
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="Status", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 15))

        self.status_label = ttk.Label(
            status_frame,
            text="READY",
            font=("Helvetica", 18, "bold"),
            foreground="gray",
        )
        self.status_label.pack(pady=10)

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        # Start button
        self.start_btn = ttk.Button(
            button_frame,
            text="Start Conversation",
            command=self._start_conversation,
            style="Start.TButton",
        )
        self.start_btn.pack(fill=tk.X, pady=5)

        # Pause button
        self.pause_btn = ttk.Button(
            button_frame,
            text="Pause Audio",
            command=self._toggle_pause,
            state="disabled",
        )
        self.pause_btn.pack(fill=tk.X, pady=5)

        # Stop button
        self.stop_btn = ttk.Button(
            button_frame,
            text="Stop Conversation",
            command=self._stop_conversation,
            state="disabled",
            style="Stop.TButton",
        )
        self.stop_btn.pack(fill=tk.X, pady=5)

        # Info section
        info_frame = ttk.LabelFrame(main_frame, text="Info", padding="10")
        info_frame.pack(fill=tk.X, pady=(15, 0))

        agent_label = ttk.Label(
            info_frame,
            text=f"Agent: {self.config.agent_id[:20]}...",
            font=("Helvetica", 9),
        )
        agent_label.pack(anchor=tk.W)

        device_label = ttk.Label(
            info_frame,
            text=f"Mic: {self.config.devices.mic_id} | Cable: {self.config.devices.cable_id} | Speaker: {self.config.devices.speaker_id}",
            font=("Helvetica", 9),
        )
        device_label.pack(anchor=tk.W)

        # Configure button styles
        style = ttk.Style()
        style.configure("Start.TButton", font=("Helvetica", 11))
        style.configure("Stop.TButton", font=("Helvetica", 11))

    def _update_status(self, text: str, color: str) -> None:
        """Update the status label."""
        self.status_label.config(text=text, foreground=color)
        self.root.update_idletasks()

    def _start_conversation(self) -> None:
        """Start the conversation session."""
        try:
            self._update_status("CONNECTING...", "orange")

            # Create audio interface
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

            # Create and start monitor loop
            # Monitor uses output_channels since both BlackHole and speakers are stereo
            self.monitor = AudioMonitor(
                input_device_id=self.config.devices.cable_id,
                output_device_id=self.config.devices.speaker_id,
                sample_rate=self.config.audio.sample_rate,
                channels=self.config.audio.output_channels,
                dtype=self.config.audio.dtype,
                buffer_size=self.config.audio.buffer_size,
                verbose=self.config.debug.verbose_audio,
            )
            self.monitor.start()

            # Create conversation callbacks
            def on_agent_response(response: str) -> None:
                if self.config.debug.print_transcripts:
                    print(f"[Agent] {response}")

            def on_user_transcript(transcript: str) -> None:
                if self.config.debug.print_transcripts:
                    print(f"[User] {transcript}")

            # Create conversation
            self.conversation = Conversation(
                client=self.client,
                agent_id=self.config.agent_id,
                requires_auth=True,
                audio_interface=self.audio_interface,
                callback_agent_response=on_agent_response,
                callback_user_transcript=on_user_transcript,
            )

            # Start session (runs in background, non-blocking)
            self.conversation.start_session()

            # Update UI
            self._update_status("LIVE", "green")
            self.start_btn.config(state="disabled")
            self.pause_btn.config(state="normal")
            self.stop_btn.config(state="normal")

        except Exception as e:
            self._handle_error(str(e))

    def _toggle_pause(self) -> None:
        """Toggle pause state of audio interface."""
        if self.audio_interface:
            is_paused = self.audio_interface.toggle_pause()

            if is_paused:
                self._update_status("PAUSED", "blue")
                self.pause_btn.config(text="Resume Audio")
            else:
                self._update_status("LIVE", "green")
                self.pause_btn.config(text="Pause Audio")

    def _stop_conversation(self) -> None:
        """Stop the conversation session."""
        self._update_status("STOPPING...", "orange")

        # End conversation session
        if self.conversation:
            try:
                self.conversation.end_session()
            except Exception as e:
                print(f"[Stop Error] {e}")
            self.conversation = None

        # Stop monitor
        if self.monitor:
            self.monitor.stop()
            self.monitor = None

        # Clean up audio interface
        self.audio_interface = None

        # Reset UI
        self._update_status("STOPPED", "red")
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled", text="Pause Audio")
        self.stop_btn.config(state="disabled")

    def _on_session_end(self) -> None:
        """Handle natural session end."""
        if self.conversation:
            self._stop_conversation()
        print("[Session] Ended")

    def _handle_error(self, error: str) -> None:
        """Handle errors during conversation."""
        self._update_status("ERROR", "red")
        self.start_btn.config(state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")

        messagebox.showerror("Error", f"An error occurred:\n\n{error}")

    def _on_close(self) -> None:
        """Handle window close event."""
        if self.conversation:
            self._stop_conversation()
        self.root.destroy()


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
