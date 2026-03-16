import base64
import httpx
import config
import io

def process_voice_remote(wav_io: io.BytesIO) -> tuple:
    encoded_input = base64.b64encode(wav_io.getvalue()).decode('utf-8')

    response = httpx.post(
        f"http://{config.VIVOBOOK_IP}:8000/process",
        json={"audio_base64": encoded_input},
        timeout=30.0
    )

    data = response.json()
    reply_io = io.BytesIO(base64.b64decode(data["audio_base64"]))
    return data["user_text"], data["ai_text"], reply_io