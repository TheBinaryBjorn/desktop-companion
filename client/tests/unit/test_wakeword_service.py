from unittest.mock import MagicMock
import pytest
from src.software_services.wakeword_service import OpenWakeWordService
from src.config import WAKEWORD, WAKEWORD_THRESHOLD, PCM_BYTE_CHUNK_SIZE

def test_detect_wakeword_above_threshold():
    mock_model = MagicMock()
    mock_model.predict.return_value = {WAKEWORD: WAKEWORD_THRESHOLD + 0.1}

    service = OpenWakeWordService(model=mock_model)
    result = service.detect_wakeword(b"\x00\x01" * 512)

    assert result is True

def test_detect_wakeword_below_threshold():
    mock_model = MagicMock()
    mock_model.predict.return_value = {WAKEWORD: WAKEWORD_THRESHOLD - 0.1}

    service = OpenWakeWordService(model=mock_model)
    result = service.detect_wakeword(b"\x00\x01" * PCM_BYTE_CHUNK_SIZE)

    assert result is False

def test_detect_wakeword_exact_threshold():
    mock_model = MagicMock()
    mock_model.predict.return_value = {WAKEWORD: WAKEWORD_THRESHOLD}

    service = OpenWakeWordService(model=mock_model)
    result = service.detect_wakeword(b"\x00\x01" * PCM_BYTE_CHUNK_SIZE)

    assert result is True

def test_detect_wakeword_with_not_bytes_input():
    mock_model = MagicMock()
    service = OpenWakeWordService(model=mock_model)
    
    with pytest.raises((ValueError, TypeError)):
        service.detect_wakeword("not bytes")

def test_detect_wakeword_with_wrong_chunk_size():
    mock_model = MagicMock()
    service = OpenWakeWordService(model=mock_model)

    with pytest.raises((ValueError, TypeError)):
        service.detect_wakeword(b"\x00\x01")