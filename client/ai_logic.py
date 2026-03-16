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

async def _call_brain(local_wav_path):
    # 1. Prepare audio for transport
    with open(local_wav_path, "rb") as f:
        encoded_input = base64.b64encode(f.read()).decode('utf-8')

    # 2. Connect via SSE (The standard for HTTP MCP)
    url = f"http://{config.VIVOBOOK_IP}:8000/sse" # Note the /sse endpoint
    
    async with sse_client(url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            
            # 3. Call the pipeline tool
            # result is a CallToolResult object
            result = await session.call_tool("process_voice_pipeline", {
                "audio_base64": encoded_input
            })
            
            # The result content is a list of blocks. 
            # We need to parse the JSON string from the first block.
            response_data = json.loads(result.content[0].text)

            # 4. Save incoming speech
            reply_path = "jarvis_voice_local.wav"
            with open(reply_path, "wb") as f:
                f.write(base64.b64decode(response_data["audio_base64"]))

            return response_data["user_text"], response_data["ai_text"], reply_path