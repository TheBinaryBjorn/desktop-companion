import os
import base64
import time
import ollama
import whisper
import subprocess
import atexit
from fastapi import FastAPI
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
OUTPUT_WAV = r"C:\piper\output.wav"

def shutdown():
    print("Shutting down Ollama...")
    subprocess.run("taskkill /F /IM ollama.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

atexit.register(shutdown)

class AudioRequest(BaseModel):
    audio_base64: str

@app.post("/process")
def process_voice(req: AudioRequest):
    # 1. Decode and save audio
    with open(INPUT_WAV, "wb") as f:
        f.write(base64.b64decode(req.audio_base64))

    # 2. Transcribe
    result = stt_model.transcribe(INPUT_WAV)
    user_text = result["text"].strip()
    print(f"User: {user_text}")

    # 3. Stream Ollama tokens directly into Piper stdin
    piper_proc = subprocess.Popen(
        [PIPER_EXE, "-m", VOICE_MODEL, "-f", OUTPUT_WAV],
        stdin=subprocess.PIPE,
        text=True
    )

    full_response = ""
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
        full_response += token
        piper_proc.stdin.write(token)
        piper_proc.stdin.flush()

    piper_proc.stdin.close()
    piper_proc.wait()
    print(f"Jarvis: {full_response}")

    # 4. Encode and return audio + transcripts
    with open(OUTPUT_WAV, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode('utf-8')

    return {
        "user_text": user_text,
        "ai_text": full_response,
        "audio_base64": audio_b64
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)