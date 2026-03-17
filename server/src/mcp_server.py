import base64
import time
import ollama
import whisper
import subprocess
import atexit
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

app = FastAPI()

print("Starting Ollama...")
subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(2)

print("Loading Whisper STT...")
stt_model = whisper.load_model("tiny")

PIPER_EXE = r"C:\piper\piper.exe"
VOICE_MODEL = r"C:\piper\en_US-amy-medium.onnx"
INPUT_WAV = r"C:\piper\input.wav"

def shutdown():
    print("Shutting down Ollama...")
    subprocess.run("taskkill /F /IM ollama.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

atexit.register(shutdown)

class AudioRequest(BaseModel):
    audio_base64: str

def generate_audio_stream(user_text: str):
    """Stream PCM audio chunks from Piper as Ollama generates tokens."""
    piper_proc = subprocess.Popen(
        [PIPER_EXE, "-m", VOICE_MODEL, "--output-raw"],  # raw PCM to stdout
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=False
    )

    # Feed Ollama tokens into Piper in a separate thread
    import threading

    def feed_piper():
        stream = ollama.chat(
            model='gemma3:1b',
            messages=[
                {'role': 'system', 'content': 'You are Jarvis. Be brief. One or two sentences max.'},
                {'role': 'user', 'content': user_text}
            ],
            stream=True
        )
        for chunk in stream:
            token = chunk['message']['content']
            piper_proc.stdin.write(token.encode())
            piper_proc.stdin.flush()
        piper_proc.stdin.close()

    feeder = threading.Thread(target=feed_piper)
    feeder.start()

    # Stream raw PCM chunks back to Pi as they come out of Piper
    while True:
        chunk = piper_proc.stdout.read(4096)
        if not chunk:
            break
        yield chunk

    feeder.join()
    piper_proc.wait()

@app.post("/process")
def process_voice(req: AudioRequest):
    # 1. Decode and save audio
    with open(INPUT_WAV, "wb") as f:
        f.write(base64.b64decode(req.audio_base64))

    # 2. Transcribe
    result = stt_model.transcribe(INPUT_WAV)
    user_text = result["text"].strip()
    print(f"User: {user_text}")

    # 3. Stream raw PCM audio back
    return StreamingResponse(
        generate_audio_stream(user_text),
        media_type="audio/raw",
        headers={
            "X-Sample-Rate": "22050",
            "X-Channels": "1",
            "X-Sample-Width": "2",
            "X-User-Text": user_text
        }
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)