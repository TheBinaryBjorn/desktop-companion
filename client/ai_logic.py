import base64
import asyncio
import config
from mcp import ClientSession
from mcp.client.http import HttpClient

def start_new_chat():
    """Reset any local session state if necessary."""
    pass

def process_voice_remote(local_wav_path):
    """Wrapper to run the async network call in your synchronous main loop."""
    return asyncio.run(_call_brain(local_wav_path))

async def _call_brain(local_wav_path):
    # 1. Read local mic recording and encode to Base64
    with open(local_wav_path, "rb") as f:
        encoded_input = base64.b64encode(f.read()).decode('utf-8')

    # 2. Connect to the Vivobook MCP Server
    url = f"http://{config.VIVOBOOK_IP}:8000/mcp"
    async with HttpClient(url) as client:
        async with ClientSession(client) as session:
            await session.initialize()
            
            # Call the pipeline tool
            result = await session.call_tool("process_voice_pipeline", {
                "audio_base64": encoded_input
            })
            
            # result.data is the dictionary returned by the server
            data = result.data

            # 3. Decode the Jarvis voice and save it locally for playback
            reply_wav = "jarvis_voice_local.wav"
            with open(reply_wav, "wb") as f:
                f.write(base64.b64decode(data["audio_base64"]))

            return data["user_text"], data["ai_text"], reply_wav