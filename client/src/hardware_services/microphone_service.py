"""
This module is a microservice to handle communication with the
INMP microphone.
"""

from abc import ABC, abstractmethod
import pyaudio
from src.config import (
    MICROPHONE_SERVICE_FORMAT,
    MICROPHONE_SERVICE_CHANNELS,
    MICROPHONE_SERVICE_RATE,
    MICROPHONE_SERVICE_CHUNK_SIZE,
)


class MicrophoneService(ABC):
    """
    This abstract class provides an interface for interactions with
    the microphone hardware.
    """

    @abstractmethod
    def read_pcm_bytes(self):
        """This function reads raw pcm bytes from an audio stream"""


class PyAudioMicrophoneService(MicrophoneService):
    """This class is a pyaudio wrapper to implement the microphone service."""

    def __init__(
        self,
        stream_format=MICROPHONE_SERVICE_FORMAT,
        channels=MICROPHONE_SERVICE_CHANNELS,
        rate=MICROPHONE_SERVICE_RATE,
        chunk_size=MICROPHONE_SERVICE_CHUNK_SIZE,
    ):
        self.chunk_size = chunk_size
        self.stream_format = stream_format
        self.channels = channels
        self.rate = rate
        self.pyaudio_object = pyaudio.PyAudio()
        self.microphone_audio_stream = self.pyaudio_object.open(
            format=stream_format,
            channels=channels,
            rate=rate,
            input=True,
            frames_per_buffer=chunk_size,
        )

    def read_pcm_bytes(self):
        pcm_bytes = self.microphone_audio_stream.read(self.chunk_size)
        return pcm_bytes
