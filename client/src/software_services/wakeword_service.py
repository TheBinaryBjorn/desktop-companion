"""
This Module is in charge of wake word detection
in audio (PCM Bytes).
"""

from abc import ABC, abstractmethod
import numpy as np
from openwakeword.model import Model
from src.config import WAKEWORD, WAKEWORD_THRESHOLD, PCM_BYTE_CHUNK_SIZE


class WakeWordDetectionService(ABC):
    """
    This class is an interface for wakeword detection service.
    """

    @abstractmethod
    def detect_wakeword(self, pcm_bytes):
        """This method detects a wake word in raw pcm bytes"""

    @abstractmethod
    def reset_model(self):
        """This method resets the model to prevent wakeword detection duplications"""


class OpenWakeWordService(WakeWordDetectionService):
    """
    This class is an implementation for wakeword service using
    openwakeword
    """

    def __init__(self, model: Model):
        self.model = model

    def detect_wakeword(self, pcm_bytes):
        """This method detects a wake word in raw pcm bytes"""
        if not isinstance(pcm_bytes, bytes):
            raise ValueError(f"Expected bytes, got {type(pcm_bytes).__name__}")
        if len(pcm_bytes) != PCM_BYTE_CHUNK_SIZE * 2:
            raise ValueError(
                f"Expected {PCM_BYTE_CHUNK_SIZE * 2} bytes, got {len(pcm_bytes)}"
            )
        audio_array = np.frombuffer(pcm_bytes, dtype=np.int16)
        prediction = self.model.predict(audio_array)
        return prediction[WAKEWORD] >= WAKEWORD_THRESHOLD
    
    def reset_model(self):
        """This method resets the model to prevent wakeword detection duplications"""
        self.model.reset()
