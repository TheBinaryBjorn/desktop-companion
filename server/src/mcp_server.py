import os
import base64
import tempfile
import ollama
import whisper
import subprocess
from fastmcp import FastMCP

mcp = FastMCP("Jarvis-Brain")

print("Loading Whisper STT...")
stt_model = whisper.load_model("base")

PIPER_EXE = "C:/piper/piper.exe"
VOICE_MODEL = "C:/piper/en_US-amy-medium.onnx"

@mcp.tool()
def process_voice_pipeline(audio_base64: str) -> dict:
    """Receives Base64 audio, processes it, and returns Base64 speech."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_in:
        input_wav = tmp_in.name
        tmp_in.write(base64.b64decode(audio_base64))

    result = stt_model.transcribe(input_wav)
    user_text = result["text"].strip()
    print(f"User: {user_text}")

    response = ollama.chat(model='gemma3:1b', messages=[
        {'role': 'system', 'content': 'You are Jarvis. Be brief.'},
        {'role': 'user', 'content': user_text}
    ])
    ai_text = response['message']['content']
    print(f"Jarvis: {ai_text}")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_out:
        output_wav = tmp_out.name

    command = [PIPER_EXE, "-m", VOICE_MODEL, "-f", output_wav]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, text=True)
    process.communicate(input=ai_text)

    with open(output_wav, "rb") as f:
        reply_audio_base64 = base64.b64encode(f.read()).decode('utf-8')

    os.unlink(input_wav)
    os.unlink(output_wav)

    return {
        "user_text": user_text,
        "ai_text": ai_text,
        "audio_base64": reply_audio_base64
    }

if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)