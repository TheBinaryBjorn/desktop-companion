import base64
import httpx
import pyaudio
import config
import io

CHUNK_SIZE = 4096
SAMPLE_RATE = 22050
CHANNELS = 1
SAMPLE_WIDTH = 2  # 16-bit

def process_voice_remote(wav_io: io.BytesIO) -> tuple:
    encoded_input = base64.b64encode(wav_io.getvalue()).decode('utf-8')

    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        output=True
    )

    user_text = ""
    with httpx.stream(
        "POST",
        f"http://{config.VIVOBOOK_IP}:8000/process",
        json={"audio_base64": encoded_input},
        timeout=30.0
    ) as response:
        user_text = response.headers.get("X-User-Text", "")
        for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
            stream.write(chunk)

    stream.stop_stream()
    stream.close()
    p.terminate()

    return user_text, "", None  # ai_text and reply_io no longer needed