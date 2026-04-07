"""
This module tests the microphone service file
"""
from unittest.mock import MagicMock, patch
from src.hardware_services.microphone_service import PyAudioMicrophoneService
from src.hardware_services.config import MICROPHONE_SERVICE_FORMAT, MICROPHONE_SERVICE_CHANNELS, MICROPHONE_SERVICE_RATE, MICROPHONE_SERVICE_CHUNK_SIZE

@patch("microphone_service.pyaudio.PyAudio")
def test_read_pcm_bytes(mock_pyaudio_class):
    mock_pyaudio_instance= MagicMock()
    mock_stream = MagicMock()
    mock_pyaudio_class.return_value = mock_pyaudio_instance
    mock_pyaudio_instance.open.return_value = mock_stream
    mock_stream.read.return_value = b"fake_audio_data"

    service = PyAudioMicrophoneService()
    result = service.read_pcm_bytes()

    assert result == b"fake_audio_data"
    mock_stream.read.assert_called_once_with(service.chunk_size)

@patch("microphone_service.pyaudio.PyAudio")
def test_stream_opened_with_correct_params(mock_pyaudio_class):
    mock_pyaudio_instance = MagicMock()
    mock_pyaudio_class.return_value = mock_pyaudio_instance

    service = PyAudioMicrophoneService(stream_format=MICROPHONE_SERVICE_FORMAT,
                             channels=MICROPHONE_SERVICE_CHANNELS,
                             rate=MICROPHONE_SERVICE_RATE,
                             chunk_size=MICROPHONE_SERVICE_CHUNK_SIZE)
    
    mock_pyaudio_instance.open.assert_called_once_with(
        format=MICROPHONE_SERVICE_FORMAT,
        channels=MICROPHONE_SERVICE_CHANNELS,
        rate=MICROPHONE_SERVICE_RATE,
        input=True,
        frames_per_buffer=MICROPHONE_SERVICE_CHUNK_SIZE
    )