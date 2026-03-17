import pytest
import os
from unittest.mock import MagicMock, patch
from fastmcp import Client
from server import mcp

@pytest.fixture
async def mcp_client():
    """Fixture to provide a local MCP client."""
    async with Client(mcp) as client:
        yield client

@pytest.mark.asyncio
async def test_process_voice_command_full_flow(mcp_client):
    """
    Tests the full STT -> LLM -> TTS pipeline using mocks.
    This ensures the logic flows correctly without needing the models loaded.
    """
    
    # 1. Mock Whisper (STT)
    mock_stt_result = {"text": "Hello Jarvis, how are you?"}
    
    # 2. Mock Ollama (LLM)
    mock_llm_response = {
        'message': {
            'content': 'I am functioning within normal parameters.'
        }
    }

    # Use 'patch' to intercept the calls inside the tool
    with patch('whisper.load_model'), \
         patch('mcp_server.stt_model.transcribe', return_value=mock_stt_result), \
         patch('ollama.chat', return_value=mock_llm_response), \
         patch('subprocess.Popen') as mock_popen:
        
        # Setup the mock for Piper subprocess
        mock_process = MagicMock()
        mock_process.communicate.return_value = (None, None)
        mock_popen.return_value = mock_process

        # --- EXECUTE ---
        # We pass a fake path because Whisper is mocked anyway
        result = await mcp_client.call_tool("process_voice_command", {
            "audio_path": "fake_mic_input.wav"
        })

        # --- ASSERTIONS ---
        # Note: MCP returns results as a list of content blocks
        data = result[0].content 
        
        # Check if the transcription matches our mock
        assert data['user_transcription'] == "Hello Jarvis, how are you?"
        
        # Check if the AI reply matches our mock
        assert data['ai_response_text'] == "I am functioning within normal parameters."
        
        # Check if it points to a .wav file
        assert data['audio_response_path'].endswith(".wav")
        
        # Verify that Piper was actually "called"
        mock_popen.assert_called_once()

@pytest.mark.asyncio
async def test_file_not_found_behavior(mcp_client):
    """
    Test how the system handles a missing audio file.
    (Optional: You can add error handling in your server for this)
    """
    # This is a placeholder to remind you to test edge cases!
    pass