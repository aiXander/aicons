"""
Monitor Loop - Audio pass-through for verification.

This module provides the "end-to-end test" functionality by listening
to the virtual cable (BlackHole) and playing it through the speakers.

The "Double-Hop" Architecture:
1. Agent Loop: Mic -> ElevenLabs -> BlackHole (handled by audio_interface.py)
2. Monitor Loop: BlackHole -> Speakers (this module)

When deployed to production (e.g., Unreal Engine on Windows), you simply
don't start the Monitor Loop, and the audio only goes to the virtual cable.
"""

import sounddevice as sd
import numpy as np
from typing import Optional
import threading


class AudioMonitor:
    """
    Audio pass-through monitor for verifying virtual cable output.

    Listens to the virtual cable input and plays audio through speakers,
    allowing you to hear what's being sent to the virtual cable.
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
        Initialize the audio monitor.

        Args:
            input_device_id: Device ID for virtual cable input (BlackHole)
            output_device_id: Device ID for speaker output
            sample_rate: Audio sample rate (must match agent output)
            channels: Number of audio channels
            dtype: Audio data type
            buffer_size: Frames per buffer
            verbose: Print status messages
        """
        self.input_device_id = input_device_id
        self.output_device_id = output_device_id
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.buffer_size = buffer_size
        self.verbose = verbose

        self._running = False
        self._stream: Optional[sd.Stream] = None
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        """Check if the monitor is currently running."""
        with self._lock:
            return self._running

    def _audio_callback(self, indata, outdata, frames, time_info, status):
        """
        Audio stream callback - passes input directly to output.

        Args:
            indata: Input audio data from virtual cable
            outdata: Output buffer for speakers
            frames: Number of frames
            time_info: Timing information
            status: Stream status
        """
        if status and self.verbose:
            print(f"[Monitor] Status: {status}")

        # Direct pass-through: what comes in goes out
        outdata[:] = indata

    def start(self) -> None:
        """Start the monitor loop."""
        with self._lock:
            if self._running:
                print("[Monitor] Already running")
                return

            self._running = True

        if self.verbose:
            print(f"[Monitor] Starting (Cable ID: {self.input_device_id} -> Speaker ID: {self.output_device_id})")

        try:
            self._stream = sd.Stream(
                device=(self.input_device_id, self.output_device_id),
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.buffer_size,
                callback=self._audio_callback,
            )
            self._stream.start()

            if self.verbose:
                print("[Monitor] Started successfully")

        except Exception as e:
            with self._lock:
                self._running = False
            raise RuntimeError(f"Failed to start monitor: {e}")

    def stop(self) -> None:
        """Stop the monitor loop."""
        with self._lock:
            if not self._running:
                return
            self._running = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                if self.verbose:
                    print(f"[Monitor] Error stopping stream: {e}")
            finally:
                self._stream = None

        if self.verbose:
            print("[Monitor] Stopped")


class MonitorThread:
    """
    Wrapper to run AudioMonitor in a background thread.

    Useful for running the monitor alongside other operations
    without blocking the main thread.
    """

    def __init__(self, monitor: AudioMonitor):
        """
        Initialize the monitor thread wrapper.

        Args:
            monitor: AudioMonitor instance to run
        """
        self.monitor = monitor
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the monitor in a background thread."""
        if self._thread and self._thread.is_alive():
            print("[MonitorThread] Already running")
            return

        def run():
            self.monitor.start()
            # Keep thread alive while monitor is running
            while self.monitor.is_running:
                threading.Event().wait(0.1)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the monitor and wait for thread to finish."""
        self.monitor.stop()
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
