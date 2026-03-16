import base64
import asyncio
import config
import json
import io
from fastmcp import Client

def process_voice_remote(wav_io: io.BytesIO):
    return asyncio.run(_call_brain(wav_io))

async def _call_brain(wav_io: io.BytesIO):
    encoded_input = base64.b64encode(wav_io.getvalue()).decode('utf-8')

    async with Client(f"http://{config.VIVOBOOK_IP}:8000/sse") as client:
        result = await client.call_tool("process_voice_pipeline", {
            "audio_base64": encoded_input
        })

    data = json.loads(result.content[0].text)
    reply_io = io.BytesIO(base64.b64decode(data["audio_base64"]))
    return data["user_text"], data["ai_text"], reply_io