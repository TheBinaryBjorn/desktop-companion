"""
Integration tests for the microphone service.
"""
import pytest
from src.hardware_services.microphone_service import PyAudioMicrophoneService
from src.config import (
    MICROPHONE_SERVICE_CHUNK_SIZE,
    MICROPHONE_SERVICE_CHANNELS,
)

EXPECTED_CHUNK_BYTES = MICROPHONE_SERVICE_CHUNK_SIZE * MICROPHONE_SERVICE_CHANNELS * 2  # 2 bytes per sample (paInt16)


@pytest.fixture
def service():
    service = PyAudioMicrophoneService()
    yield service
    if service.microphone_audio_stream and service.microphone_audio_stream.is_active():
        service.close_stream()


def test_open_stream_is_active(service):
    service.open_stream()
    assert service.microphone_audio_stream.is_active()
    assert not service.microphone_audio_stream.is_stopped()


def test_close_stream_is_stopped(service):
    service.open_stream()
    service.close_stream()
    assert service.microphone_audio_stream.is_stopped()
    assert not service.microphone_audio_stream.is_active()


def test_read_pcm_bytes_returns_bytes(service):
    service.open_stream()
    result = service.read_pcm_bytes()
    assert isinstance(result, bytes)
    assert len(result) == EXPECTED_CHUNK_BYTES


def test_read_pcm_bytes_multiple_chunks(service):
    service.open_stream()
    for _ in range(10):
        result = service.read_pcm_bytes()
        assert isinstance(result, bytes)
        assert len(result) == EXPECTED_CHUNK_BYTES


def test_open_close_cycle_multiple_times(service):
    for _ in range(3):
        service.open_stream()
        assert service.microphone_audio_stream.is_active()
        service.close_stream()
        assert service.microphone_audio_stream.is_stopped()


def test_read_pcm_bytes_raises_after_close(service):
    service.open_stream()
    service.close_stream()
    with pytest.raises(OSError):
        service.read_pcm_bytes()