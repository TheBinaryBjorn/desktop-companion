import os
import base64
import ollama
import whisper
import subprocess
import atexit
from fastmcp import FastMCP
import time

mcp = FastMCP("Jarvis-Brain")

print("Starting Ollama...")
subprocess.Popen(
    ["ollama", "serve"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

# Wait for Ollama to be ready
print("Waiting for Ollama...")
for i in range(10):
    try:
        ollama.list()
        print("Ollama is ready.")
        break
    except Exception:
        time.sleep(1)
else:
    print("Warning: Ollama may not be ready.")
def shutdown():
    print("Shutting down Ollama...")
    subprocess.run("taskkill /F /IM ollama.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

atexit.register(shutdown)

print("Loading Whisper STT...")
stt_model = whisper.load_model("tiny")

PIPER_EXE = r"C:\piper\piper.exe"
VOICE_MODEL = r"C:\piper\en_US-amy-medium.onnx"
INPUT_WAV = r"C:\piper\input.wav"
OUTPUT_WAV = r"C:\piper\output.wav"

@mcp.tool()
def process_voice_pipeline(audio_base64: str) -> dict:
    """Receives Base64 audio, processes it, and returns Base64 speech."""
    print("Started process_voice")
    with open(INPUT_WAV, "wb") as f:
        f.write(base64.b64decode(audio_base64))
    print("Opened base64 file")

    result = stt_model.transcribe(INPUT_WAV)
    user_text = result["text"].strip()
    print(f"User: {user_text}")

    response = ollama.chat(model='gemma3:1b', messages=[
        {'role': 'system', 'content': 'You are Jarvis. Be brief.'},
        {'role': 'user', 'content': user_text}
    ])
    ai_text = response['message']['content']
    print(f"Jarvis: {ai_text}")

    command = f'"{PIPER_EXE}" -m "{VOICE_MODEL}" -f "{OUTPUT_WAV}"'
    subprocess.run(command, input=ai_text, text=True, shell=True)

    with open(OUTPUT_WAV, "rb") as f:
        reply_audio_base64 = base64.b64encode(f.read()).decode('utf-8')

    return {
        "user_text": user_text,
        "ai_text": ai_text,
        "audio_base64": reply_audio_base64
    }

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)