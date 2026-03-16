import os
import base64
import ollama
import whisper
import subprocess
from fastmcp import FastMCP

mcp = FastMCP("Jarvis-Brain")

# Load models once
print("Loading Whisper STT...")
stt_model = whisper.load_model("base")

# Config for Piper
PIPER_EXE = "C:/piper/piper.exe"
VOICE_MODEL = "C:/piper/en_US-amy-medium.onnx"

@mcp.tool()
def process_voice_pipeline(audio_base64: str) -> dict:
    """
    Receives Base64 audio, processes it, and returns Base64 speech.
    """
    # 1. Decode Pi's audio
    input_wav = "pi_in.wav"
    with open(input_wav, "wb") as f:
        f.write(base64.b64decode(audio_base64))

    # 2. STT (Whisper)
    result = stt_model.transcribe(input_wav)
    user_text = result["text"].strip()
    print(f"User: {user_text}")

    # 3. LLM (Gemma 3)
    response = ollama.chat(model='gemma3:1b', messages=[
        {'role': 'system', 'content': 'You are Jarvis. Be brief.'},
        {'role': 'user', 'content': user_text}
    ])
    ai_text = response['message']['content']
    print(f"Jarvis: {ai_text}")

    # 4. TTS (Piper)
    output_wav = "jarvis_out.wav"
    # Note: Use --text flag for simple execution or stdin for long text
    command = [PIPER_EXE, "-m", VOICE_MODEL, "-f", output_wav]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, text=True)
    process.communicate(input=ai_text)

    # 5. Encode speech result
    with open(output_wav, "rb") as f:
        reply_audio_base64 = base64.b64encode(f.read()).decode('utf-8')

    return {
        "user_text": user_text,
        "ai_text": ai_text,
        "audio_base64": reply_audio_base64
    }

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)