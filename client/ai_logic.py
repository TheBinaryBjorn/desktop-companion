import asyncio
import websockets
import pyaudio
import config
import io

CHUNK_SIZE = 4096
SAMPLE_RATE = 22050
CHANNELS = 1

def process_voice_remote(wav_io: io.BytesIO) -> tuple:
    return asyncio.run(_stream_to_server(wav_io))

async def _stream_to_server(wav_io: io.BytesIO) -> tuple:
    uri = f"ws://{config.VIVOBOOK_IP}:8000/stream"

    async with websockets.connect(uri) as ws:
        # 1. Extract raw PCM from WAV (skip 44-byte header)
        wav_io.seek(44)
        pcm = wav_io.read()

        # 2. Stream PCM in chunks — this already happened during speech
        #    so network transfer is near-instant from Pi's perspective
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

def process_voice_remote(wav_io: io.BytesIO) -> tuple:
    return asyncio.run(_stream_to_server(wav_io))