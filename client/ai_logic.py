import base64
import asyncio
import config
import json
import io
from fastmcp import Client

def process_voice_remote(wav_io):
    """Bridge function for the main loop"""
    return asyncio.run(_call_brain(wav_io))

async def _call_brain(wav_io):
    # 1. Prepare audio
    encoded_input = base64.b64encode(wav_io.getvalue()).decode('utf-8')

    # 2. Use the simplified FastMCP Client
    # Point it directly to the base /mcp endpoint
    async with Client(f"http://{config.VIVOBOOK_IP}:8000/mcp") as client:
        # 3. Call the tool
        result = await client.call_tool("process_voice_pipeline", {
            "audio_base64": encoded_input
        })
        
        # FastMCP client automatically parses the result for you
        # result is usually a stringified JSON if you returned a dict
        data = json.loads(result)

        # 4. Save incoming speech to RAM
        reply_audio_bytes = base64.b64decode(data["audio_base64"])
        reply_io = io.BytesIO(reply_audio_bytes)

        return data["user_text"], data["ai_text"], reply_io