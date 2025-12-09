"""
Audio Interface - Custom ElevenLabs audio handler for virtual cable routing.

This module extends the ElevenLabs SDK to support specific device routing
and provides pause/resume functionality for audio streams.
"""

import sounddevice as sd
import numpy as np
from elevenlabs.conversational_ai.conversation import AudioInterface
from typing import Callable, Optional
import threading


class VirtualCableInterface(AudioInterface):
    """
    Custom audio interface for routing audio through a virtual cable.

    This interface:
    - Captures audio from a microphone and sends it to ElevenLabs
    - Receives audio from ElevenLabs and outputs to a virtual cable (BlackHole)
    - Supports pause/resume functionality for muting during conversations
    """

    def __init__(
        self,
        input_device_id: int,
        output_device_id: int,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "int16",
        buffer_size: int = 1024,
        verbose: bool = False,
    ):
        """
        Initialize the virtual cable audio interface.

        Args:
            input_device_id: Device ID for microphone input
            output_device_id: Device ID for virtual cable output (BlackHole)
            sample_rate: Audio sample rate in Hz (ElevenLabs uses 16000)
            channels: Number of audio channels (1 = mono)
            dtype: Audio data type ('int16' for ElevenLabs compatibility)
            buffer_size: Frames per buffer for audio streams
            verbose: Print debug information for audio streams
        """
        self.input_device_id = input_device_id
        self.output_device_id = output_device_id
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.buffer_size = buffer_size
        self.verbose = verbose

        self._paused = False
        self._lock = threading.Lock()
        self._stream_in: Optional[sd.InputStream] = None
        self._stream_out: Optional[sd.OutputStream] = None
        self._input_callback: Optional[Callable] = None

    @property
    def paused(self) -> bool:
        """Check if audio streams are paused."""
        with self._lock:
            return self._paused

    def start(self, input_callback: Callable[[bytes], None]) -> None:
        """
        Start the audio streams.

        Args:
            input_callback: Function to call with captured audio data (bytes)
        """
        self._input_callback = input_callback

        def sd_input_callback(indata, frames, time_info, status):
            """Callback for input stream - sends mic audio to ElevenLabs."""
            if status and self.verbose:
                print(f"[Audio Input] Status: {status}")

            with self._lock:
                if not self._paused:
                    # Convert numpy array to bytes and send to ElevenLabs
                    audio_bytes = bytes(indata)
                    self._input_callback(audio_bytes)
                else:
                    # Send silence when paused to keep connection alive
                    silence = np.zeros(frames * self.channels, dtype=self.dtype).tobytes()
                    self._input_callback(silence)

        # Create input stream (Microphone -> ElevenLabs)
        self._stream_in = sd.InputStream(
            device=self.input_device_id,
            channels=self.channels,
            samplerate=self.sample_rate,
            dtype=self.dtype,
            blocksize=self.buffer_size,
            callback=sd_input_callback,
        )

        # Create output stream (ElevenLabs -> Virtual Cable)
        self._stream_out = sd.OutputStream(
            device=self.output_device_id,
            channels=self.channels,
            samplerate=self.sample_rate,
            dtype=self.dtype,
            blocksize=self.buffer_size,
        )

        # Start both streams
        self._stream_in.start()
        self._stream_out.start()

        if self.verbose:
            print(f"[Audio Interface] Started - Input: {self.input_device_id}, Output: {self.output_device_id}")

    def stop(self) -> None:
        """Stop and close all audio streams."""
        if self._stream_in:
            self._stream_in.stop()
            self._stream_in.close()
            self._stream_in = None

        if self._stream_out:
            self._stream_out.stop()
            self._stream_out.close()
            self._stream_out = None

        if self.verbose:
            print("[Audio Interface] Stopped")

    def output(self, audio: bytes) -> None:
        """
        Output audio received from ElevenLabs to the virtual cable.

        Args:
            audio: PCM audio data as bytes (int16)
        """
        with self._lock:
            if self._paused:
                return

        if self._stream_out and self._stream_out.active:
            try:
                # Convert bytes to numpy array
                audio_np = np.frombuffer(audio, dtype=self.dtype)
                self._stream_out.write(audio_np)
            except Exception as e:
                if self.verbose:
                    print(f"[Audio Output] Error: {e}")

    def interrupt(self) -> None:
        """
        Handle interruption (e.g., user starts speaking while agent is talking).

        This is called by the ElevenLabs SDK when the user interrupts.
        """
        if self.verbose:
            print("[Audio Interface] Interrupted")

    def toggle_pause(self) -> bool:
        """
        Toggle the pause state of audio streams.

        When paused:
        - Input stream sends silence instead of mic audio
        - Output stream ignores incoming audio

        Returns:
            True if now paused, False if now active
        """
        with self._lock:
            self._paused = not self._paused
            state = "PAUSED" if self._paused else "ACTIVE"
            print(f"[Audio Interface] State: {state}")
            return self._paused

    def set_paused(self, paused: bool) -> None:
        """
        Explicitly set the pause state.

        Args:
            paused: True to pause, False to resume
        """
        with self._lock:
            self._paused = paused
            if self.verbose:
                state = "PAUSED" if self._paused else "ACTIVE"
                print(f"[Audio Interface] State set to: {state}")
