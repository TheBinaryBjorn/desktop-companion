import time
import ollama
from faster_whisper import WhisperModel
import subprocess
import atexit
import asyncio
import wave
import websockets

print("Starting Ollama...")
subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

print("Pre-warming Ollama...")
ollama.chat(model='gemma3:1b', messages=[{'role': 'user', 'content': 'hi'}])
print("Ready.")

print("Loading Whisper STT...")
stt_model = WhisperModel("tiny", device="cpu", compute_type="int8")

PIPER_EXE = r"C:\piper\piper.exe"
VOICE_MODEL = r"C:\piper\en_US-amy-medium.onnx"
INPUT_WAV = r"C:\piper\input.wav"

def shutdown():
    print("Shutting down Ollama...")
    subprocess.run("taskkill /F /IM ollama.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

atexit.register(shutdown)

def pcm_to_wav(pcm: bytes, rate: int = 16000) -> str:
    with wave.open(INPUT_WAV, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(pcm)
    return INPUT_WAV

async def handle_client(ws):
    print("Client connected.")
    pcm_buffer = bytearray()

    try:
        async for message in ws:
            if isinstance(message, bytes):
                pcm_buffer.extend(message)

            elif isinstance(message, str) and message == "done":
                t_start = time.time()

                # 1. Transcribe
                loop = asyncio.get_event_loop()
                pcm_to_wav(bytes(pcm_buffer))

                def transcribe():
                    segments, _ = stt_model.transcribe(INPUT_WAV)
                    return "".join([seg.text for seg in segments]).strip()

                user_text = await loop.run_in_executor(None, transcribe)
                t_whisper = time.time()
                print(f"[{t_whisper-t_start:.2f}s] Whisper done: '{user_text}'")

                # 2. Send transcript
                await ws.send(f"transcript:{user_text}")

                # 3. Start Piper
                piper_proc = subprocess.Popen(
                    [PIPER_EXE, "-m", VOICE_MODEL, "--output-raw"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )

                # 4. Feed Ollama tokens into Piper in background
                t_ollama_ref = [t_whisper]
                first_token_logged = [False]

                async def feed_piper():
                    stream = ollama.chat(
                        model='gemma3:1b',
                        messages=[
                            {'role': 'system', 'content': 'You are Jarvis. Be brief. One or two sentences max.'},
                            {'role': 'user', 'content': user_text}
                        ],
                        stream=True
                    )
                    full = ""
                    for chunk in stream:
                        token = chunk['message']['content']
                        if not first_token_logged[0]:
                            print(f"[{time.time()-t_ollama_ref[0]:.2f}s] Ollama first token")
                            first_token_logged[0] = True
                        full += token
                        piper_proc.stdin.write(token.encode())
                        piper_proc.stdin.flush()
                    piper_proc.stdin.close()
                    print(f"[{time.time()-t_start:.2f}s total] Jarvis: {full}")

                asyncio.create_task(feed_piper())

                # 5. Stream Piper audio back
                first_chunk_logged = False
                while True:
                    chunk = await loop.run_in_executor(None, piper_proc.stdout.read, 4096)
                    if not chunk:
                        break
                    if not first_chunk_logged:
                        print(f"[{time.time()-t_start:.2f}s] First audio chunk sent")
                        first_chunk_logged = True
                    await ws.send(chunk)

                # 6. Signal done
                await ws.send("audio_done")
                print(f"[{time.time()-t_start:.2f}s total] Audio stream complete")
                pcm_buffer.clear()

    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected.")

async def main():
    print("Server ready on ws://0.0.0.0:8000")
    async with websockets.serve(handle_client, "0.0.0.0", 8000):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())