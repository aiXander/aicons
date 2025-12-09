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
import queue
import time


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
        output_channels: int = 2,
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
            channels: Number of audio channels for input (1 = mono for ElevenLabs)
            output_channels: Number of channels for output device (2 for BlackHole 2ch)
            dtype: Audio data type ('int16' for ElevenLabs compatibility)
            buffer_size: Frames per buffer for audio streams
            verbose: Print debug information for audio streams
        """
        self.input_device_id = input_device_id
        self.output_device_id = output_device_id
        self.sample_rate = sample_rate
        self.channels = channels
        self.output_channels = output_channels
        self.dtype = dtype
        self.buffer_size = buffer_size
        self.verbose = verbose

        self._paused = False
        self._lock = threading.Lock()
        self._stream_in: Optional[sd.InputStream] = None
        self._stream_out: Optional[sd.RawOutputStream] = None
        self._input_callback: Optional[Callable] = None

        # Audio output queue and thread (like DefaultAudioInterface)
        self._output_queue: queue.Queue = queue.Queue()
        self._should_stop = threading.Event()
        self._output_thread: Optional[threading.Thread] = None

    @property
    def paused(self) -> bool:
        """Check if audio streams are paused."""
        with self._lock:
            return self._paused

    def _output_thread_func(self) -> None:
        """Thread function that writes audio from queue to output stream."""
        while not self._should_stop.is_set():
            try:
                audio = self._output_queue.get(timeout=0.25)
                if self._stream_out is not None:
                    self._stream_out.write(audio)
            except queue.Empty:
                pass
            except Exception as e:
                if self.verbose:
                    print(f"[Audio Output Thread] Error: {e}")

    def start(self, input_callback: Callable[[bytes], None]) -> None:
        """
        Start the audio streams.

        Args:
            input_callback: Function to call with captured audio data (bytes)
        """
        self._input_callback = input_callback
        self._should_stop.clear()

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

        # Create output stream (ElevenLabs -> Virtual Cable) using RawOutputStream
        # for blocking writes (like DefaultAudioInterface pattern)
        self._stream_out = sd.RawOutputStream(
            device=self.output_device_id,
            channels=self.output_channels,
            samplerate=self.sample_rate,
            dtype=self.dtype,
        )

        # Start streams with small delay between them to avoid macOS CoreAudio errors
        # The error -10863 (kAudioUnitErr_CannotDoInCurrentContext) happens when
        # starting multiple streams too quickly on macOS
        self._stream_in.start()
        time.sleep(0.1)  # Small delay to let CoreAudio stabilize
        self._stream_out.start()

        # Start output thread for blocking writes
        self._output_thread = threading.Thread(target=self._output_thread_func)
        self._output_thread.start()

        if self.verbose:
            print(f"[Audio Interface] Started - Input: {self.input_device_id}, Output: {self.output_device_id}")

    def stop(self) -> None:
        """Stop and close all audio streams."""
        # Signal output thread to stop
        self._should_stop.set()

        # Wait for output thread to finish
        if self._output_thread is not None:
            self._output_thread.join(timeout=1.0)
            self._output_thread = None

        if self._stream_in:
            self._stream_in.stop()
            self._stream_in.close()
            self._stream_in = None

        if self._stream_out:
            self._stream_out.stop()
            self._stream_out.close()
            self._stream_out = None

        # Clear the output queue
        while not self._output_queue.empty():
            try:
                self._output_queue.get_nowait()
            except queue.Empty:
                break

        if self.verbose:
            print("[Audio Interface] Stopped")

    def output(self, audio: bytes) -> None:
        """
        Output audio received from ElevenLabs to the virtual cable.

        Args:
            audio: PCM audio data as bytes (int16, mono from ElevenLabs)
        """
        with self._lock:
            if self._paused:
                return

        try:
            # Convert mono to stereo if output device requires more channels
            if self.output_channels > self.channels:
                # Convert bytes to numpy array (mono from ElevenLabs)
                audio_np = np.frombuffer(audio, dtype=self.dtype)
                # Duplicate mono channel to create stereo (interleaved)
                audio_stereo = np.column_stack([audio_np] * self.output_channels).flatten()
                audio = audio_stereo.tobytes()

            # Enqueue audio bytes for output thread to write
            self._output_queue.put(audio)
        except Exception as e:
            if self.verbose:
                print(f"[Audio Output] Error: {e}")

    def interrupt(self) -> None:
        """
        Handle interruption (e.g., user starts speaking while agent is talking).

        This is called by the ElevenLabs SDK when the user interrupts.
        Clears pending audio so the agent response stops immediately.
        """
        # Clear pending audio from queue
        try:
            while True:
                self._output_queue.get_nowait()
        except queue.Empty:
            pass

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
