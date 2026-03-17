from abc import ABC, abstractmethod
import config
from faster_whisper import WhisperModel

class stt_service(ABC):
    @abstractmethod
    def transcribe(self):
        pass

class faster_whisper_service(stt_service):
    def __init__(self):
        print("Loading Whisper STT...")
        # loading model can fail
        self.model = WhisperModel(config.STT_MODEL, device=config.STT_DEVICE, compute_type=config.STT_COMPUTE_TYPE)
    
    def transcribe(self, audio_np):
        # audio_np could be invalid
        segments, _ = self.model.transcribe(audio_np)
        return "".join([seg.text for seg in segments]).strip()