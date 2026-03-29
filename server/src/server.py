import os

base = os.path.join(os.path.dirname(__file__), ".venv", "Lib", "site-packages")
os.add_dll_directory(os.path.join(base, "nvidia", "cublas", "bin"))
os.add_dll_directory(os.path.join(base, "nvidia", "cudnn", "bin"))
os.add_dll_directory(os.path.join(base, "ctranslate2"))

import time, json

from llm_controller import ollama_service
from stt_controller import faster_whisper_service
from tts_controller import piper_service
from stream_controller import websocket_stream_service
import numpy as np

import subprocess
import atexit
import asyncio
import wave
import websockets

llm_model = ollama_service()
llm_model.start_service()
stt_model = faster_whisper_service()
tts_model = piper_service()
stream_service = websocket_stream_service()



# TO LLM CONTROLLER -----------------------------
def shutdown():
    print("Shutting down Ollama...")
    subprocess.run("taskkill /F /IM ollama.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
atexit.register(shutdown)
# -----------------------------------------------

async def handle_client(ws):
    if ws.path != "/stream":
        print(f"Rejected connection to {ws.path}")
        return
    print("Client connected.")
    pcm_buffer = bytearray()

    try:
        async for message in ws:
            if isinstance(message, bytes):
                pcm_buffer.extend(message)

            elif isinstance(message, str):
                
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    continue
                if payload.get("type") == "eof":
                    t_start = time.time()
                    # 1. Transcribe
                    loop = asyncio.get_event_loop()

                    audio_np = np.frombuffer(pcm_buffer, dtype=np.int16).astype(np.float32) / 32768.0
                    #Whisper is CPU bound, therefor running in the executor.
                    user_text =  await loop.run_in_executor(None, stt_model.transcribe, audio_np)

                    t_whisper = time.time()
                    print(f"[{t_whisper-t_start:.2f}s] Whisper done: '{user_text}'")

                    # 2. Send transcript - why?
                    #await ws.send(f"transcript:{user_text}")
                    
                    # 3. Start synthesis and get Piper process
                    t_sythesis_start = time.time()
                    tts_proc, feed_task = await tts_model.synthesize_stream(llm_model.send_prompt(user_text), llm_model)
                    t_synthesis_end = time.time()
                    print(f"[{t_synthesis_end-t_sythesis_start:.2f}s] Piper done.")

                    # 4. Stream Piper audio back
                    t_stream_start = time.time()
                    await stream_service.stream_to_client(ws, loop, tts_proc, feed_task)

                    # 5. Signal done
                    await ws.send(json.dumps({"type":"eof"}))
                    print(f"[{time.time()-t_stream_start:.2f}s] Audio stream complete")

                    pcm_buffer.clear()
                    print(f"[{time.time()-t_start:.2f}s] Total time.")

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected.")

async def main():
    print("Server ready on ws://0.0.0.0:8000/stream")
    async with websockets.serve(handle_client, "0.0.0.0", 8000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())