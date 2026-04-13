"""
Unit tests for the microphone service.
"""
import pytest
from unittest.mock import MagicMock, patch
from src.hardware_services.microphone_service import PyAudioMicrophoneService
from src.config import (
    MICROPHONE_SERVICE_FORMAT,
    MICROPHONE_SERVICE_CHANNELS,
    MICROPHONE_SERVICE_RATE,
    MICROPHONE_SERVICE_CHUNK_SIZE,
)


@patch("src.hardware_services.microphone_service.pyaudio.PyAudio")
def test_stream_opened_with_correct_params(mock_pyaudio_class):
    mock_pyaudio_instance = MagicMock()
    mock_pyaudio_class.return_value = mock_pyaudio_instance

    service = PyAudioMicrophoneService(
        stream_format=MICROPHONE_SERVICE_FORMAT,
        channels=MICROPHONE_SERVICE_CHANNELS,
        rate=MICROPHONE_SERVICE_RATE,
        chunk_size=MICROPHONE_SERVICE_CHUNK_SIZE,
    )
    service.open_stream()

    mock_pyaudio_instance.open.assert_called_once_with(
        format=MICROPHONE_SERVICE_FORMAT,
        channels=MICROPHONE_SERVICE_CHANNELS,
        rate=MICROPHONE_SERVICE_RATE,
        input=True,
        frames_per_buffer=MICROPHONE_SERVICE_CHUNK_SIZE,
    )


@patch("src.hardware_services.microphone_service.pyaudio.PyAudio")
def test_open_stream_calls_pyaudio_open(mock_pyaudio_class):
    mock_pyaudio_instance = MagicMock()
    mock_pyaudio_class.return_value = mock_pyaudio_instance

    service = PyAudioMicrophoneService()
    service.open_stream()

    mock_pyaudio_instance.open.assert_called_once()


@patch("src.hardware_services.microphone_service.pyaudio.PyAudio")
def test_open_stream_does_not_reopen_active_stream(mock_pyaudio_class):
    mock_pyaudio_instance = MagicMock()
    mock_stream = MagicMock()
    mock_stream.is_active.return_value = True
    mock_pyaudio_instance.open.return_value = mock_stream
    mock_pyaudio_class.return_value = mock_pyaudio_instance

    service = PyAudioMicrophoneService()
    service.open_stream()
    service.open_stream()

    mock_pyaudio_instance.open.assert_called_once()


@patch("src.hardware_services.microphone_service.pyaudio.PyAudio")
def test_close_stream_stops_and_closes(mock_pyaudio_class):
    mock_pyaudio_instance = MagicMock()
    mock_stream = MagicMock()
    mock_pyaudio_instance.open.return_value = mock_stream
    mock_pyaudio_class.return_value = mock_pyaudio_instance

    service = PyAudioMicrophoneService()
    service.open_stream()
    service.close_stream()

    mock_stream.stop_stream.assert_called_once()
    mock_stream.close.assert_called_once()


@patch("src.hardware_services.microphone_service.pyaudio.PyAudio")
def test_close_stream_returns_false_when_no_stream(mock_pyaudio_class):
    mock_pyaudio_class.return_value = MagicMock()

    service = PyAudioMicrophoneService()
    result = service.close_stream()

    assert result is False


@patch("src.hardware_services.microphone_service.pyaudio.PyAudio")
def test_read_pcm_bytes_returns_audio_data(mock_pyaudio_class):
    mock_pyaudio_instance = MagicMock()
    mock_stream = MagicMock()
    mock_stream.is_active.return_value = True
    mock_stream.read.return_value = b"fake_audio_data"
    mock_pyaudio_instance.open.return_value = mock_stream
    mock_pyaudio_class.return_value = mock_pyaudio_instance

    service = PyAudioMicrophoneService()
    service.open_stream()
    result = service.read_pcm_bytes()

    assert result == b"fake_audio_data"
    mock_stream.read.assert_called_once_with(service.chunk_size)


@patch("src.hardware_services.microphone_service.pyaudio.PyAudio")
def test_read_pcm_bytes_raises_when_stream_inactive(mock_pyaudio_class):
    mock_pyaudio_instance = MagicMock()
    mock_stream = MagicMock()
    mock_stream.is_active.return_value = False
    mock_pyaudio_instance.open.return_value = mock_stream
    mock_pyaudio_class.return_value = mock_pyaudio_instance

    service = PyAudioMicrophoneService()
    service.open_stream()

    with pytest.raises(OSError):
        service.read_pcm_bytes()


@patch("src.hardware_services.microphone_service.pyaudio.PyAudio")
def test_read_pcm_bytes_raises_when_no_stream(mock_pyaudio_class):
    mock_pyaudio_class.return_value = MagicMock()

    service = PyAudioMicrophoneService()

    with pytest.raises(OSError):
        service.read_pcm_bytes()