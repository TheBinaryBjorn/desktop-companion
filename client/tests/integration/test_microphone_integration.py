# client/tests/integration/test_microphone_integration.py
import pytest
from src.hardware_services.microphone_service import PyAudioMicrophoneService
from src.hardware_services.config import MICROPHONE_SERVICE_CHUNK_SIZE

def test_reads_pcm_bytes_from_hardware():
    service = PyAudioMicrophoneService()
    result = service.read_pcm_bytes()

    assert isinstance(result, bytes)
    assert len(result) == MICROPHONE_SERVICE_CHUNK_SIZE * 2

def test_reads_multiple_chunks():
    service = PyAudioMicrophoneService()
    
    for _ in range(10):
        result = service.read_pcm_bytes()
        assert isinstance(result, bytes)
        assert len(result) == MICROPHONE_SERVICE_CHUNK_SIZE * 2