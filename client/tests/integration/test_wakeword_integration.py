from src.software_services.wakeword_service import OpenWakeWordService
from src.hardware_services.microphone_service import PyAudioMicrophoneService
from openwakeword import Model
from src.config import WAKEWORD_MODEL_PATH, MICROPHONE_SERVICE_RATE, PCM_BYTE_CHUNK_SIZE


def test_detects_wakeword_from_hardware():
    microphone = PyAudioMicrophoneService()
    wakeword_model = Model(WAKEWORD_MODEL_PATH)
    service = OpenWakeWordService(model=wakeword_model)

    for _ in range(MICROPHONE_SERVICE_RATE // PCM_BYTE_CHUNK_SIZE * 2):
        pcm_bytes = microphone.read_pcm_bytes()
        result = service.detect_wakeword(pcm_bytes)
        assert isinstance(result, bool)


def test_reset_model_clears_internal_state_integration():
    microphone = PyAudioMicrophoneService()
    wakeword_model = Model(WAKEWORD_MODEL_PATH)
    wakeword_service = OpenWakeWordService(model=wakeword_model)

    for _ in range(3):
        pcm_bytes = microphone.read_pcm_bytes()
        result = wakeword_service.detect_wakeword(pcm_bytes)
        assert isinstance(result, bool)
        wakeword_service.reset_model()
