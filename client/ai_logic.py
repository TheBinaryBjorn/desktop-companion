import asyncio
import websockets
import pyaudio
import config
import io

SAMPLE_RATE = 22050
CHANNELS = 1

_ws = None

async def _ensure_connected():
    global _ws
    try:
        if _ws is None:
            raise Exception("No connection")
        await _ws.ping()  # will raise if connection is dead
    except Exception:
        print("Connecting to server...")
        _ws = await websockets.connect(f"ws://{config.VIVOBOOK_IP}:8000")
        print("Connected.")
    return _ws

async def _stream_to_server(wav_io: io.BytesIO) -> tuple:
    global _ws
    ws = await _ensure_connected()

    try:
        # 1. Extract raw PCM (skip 44-byte WAV header)
        wav_io.seek(44)
        pcm = wav_io.read()

        # 2. Stream PCM chunks
        chunk_size = 4096
        for i in range(0, len(pcm), chunk_size):
            await ws.send(pcm[i:i+chunk_size])

        # 3. Signal end of speech
        await ws.send("done")

        # 4. Wait for transcript
        user_text = ""
        msg = await ws.recv()
        if isinstance(msg, str) and msg.startswith("transcript:"):
            user_text = msg[len("transcript:"):]

        # 5. Play audio as it streams in
        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            output=True
        )

        while True:
            msg = await ws.recv()
            if isinstance(msg, str) and msg == "audio_done":
                break
            if isinstance(msg, bytes):
                stream.write(msg)

        stream.stop_stream()
        stream.close()
        p.terminate()

        return user_text, "", None

    except websockets.exceptions.ConnectionClosed:
        print("Connection lost, will reconnect on next call.")
        _ws = None
        return "", "", None

def process_voice_remote(wav_io: io.BytesIO) -> tuple:
    return asyncio.run(_stream_to_server(wav_io))