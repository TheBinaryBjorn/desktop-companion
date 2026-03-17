import asyncio
import aiohttp
import pyaudio
import config
import io

SAMPLE_RATE = 22050
CHANNELS = 1

def process_voice_remote(wav_io: io.BytesIO) -> tuple:
    return asyncio.run(_stream_to_server(wav_io))

async def _stream_to_server(wav_io: io.BytesIO) -> tuple:
    uri = f"http://{config.VIVOBOOK_IP}:8000/stream"

    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(uri) as ws:
            # 1. Extract raw PCM (skip 44-byte WAV header)
            wav_io.seek(44)
            pcm = wav_io.read()

            # 2. Stream PCM chunks to server
            chunk_size = 4096
            for i in range(0, len(pcm), chunk_size):
                await ws.send_bytes(pcm[i:i+chunk_size])

            # 3. Signal end of speech
            await ws.send_str("done")

            # 4. Wait for transcript
            user_text = ""
            msg = await ws.receive()
            if msg.type == aiohttp.WSMsgType.TEXT and msg.data.startswith("transcript:"):
                user_text = msg.data[len("transcript:"):]

            # 5. Play audio as it streams in
            p = pyaudio.PyAudio()
            stream = p.open(
                format=pyaudio.paInt16,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True
            )

            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT and msg.data == "audio_done":
                    break
                if msg.type == aiohttp.WSMsgType.BINARY:
                    stream.write(msg.data)

            stream.stop_stream()
            stream.close()
            p.terminate()

            return user_text, "", None