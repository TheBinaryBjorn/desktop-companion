import base64
import asyncio
import config
import json
from mcp import ClientSession
from mcp.client.sse import sse_client

def start_new_chat():
    pass

def process_voice_remote(local_wav_path):
    """Wrapper to run the async network call."""
    return asyncio.run(_call_brain(local_wav_path))

async def _call_brain(wav_io):
    # 1. Read the audio directly from RAM and encode to Base64
    # .getvalue() gets all the bytes from the BytesIO object
    encoded_input = base64.b64encode(wav_io.getvalue()).decode('utf-8')

    url = f"http://{config.VIVOBOOK_IP}:8000/sse"
    
    async with sse_client(url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            result = await session.call_tool("process_voice_pipeline", {
                "audio_base64": encoded_input
            })
            
            response_data = json.loads(result.content[0].text)

            # --- OPTIONAL: Keep the Response in RAM too? ---
            # If you want to play it immediately without saving:
            reply_audio_bytes = base64.b64decode(response_data["audio_base64"])
            reply_io = io.BytesIO(reply_audio_bytes)

            return response_data["user_text"], response_data["ai_text"], reply_io