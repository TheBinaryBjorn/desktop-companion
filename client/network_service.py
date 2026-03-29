import json, websockets, asyncio
from state_manager import JarvisState
from config import SERVER_IP

async def network_task(brain, audio_queue, playback_queue):
    uri = f"ws://{SERVER_IP}:8000/stream"
    while True:
            try:
                async with websockets.connect(uri) as ws:
                    print("Connected to server.")
                    if brain.state == JarvisState.ERROR:
                        brain.set_state(JarvisState.IDLE)

                    async def receive_handler():
                        first_chunk_received = False
                        while True:
                            try:
                                
                                message = await asyncio.wait_for(ws.recv(), timeout=10.0)
                                if isinstance(message, bytes):
                                    if not first_chunk_received:
                                        brain.set_state(JarvisState.SPEAKING)
                                        first_chunk_received = True
                                    playback_queue.put(message)
                                elif isinstance(message, str):
                                    payload = json.loads(message)
                                    if payload.get("type") == "eof":
                                        playback_queue.put(b'EOF')
                                        first_chunk_received = False
                            except asyncio.TimeoutError:
                                if brain.state == JarvisState.THINKING:
                                    print("Server response timeout! Returning to IDLE.")
                                    brain.set_state(JarvisState.IDLE)
                                    while not playback_queue.empty():
                                        playback_queue.get()
                                continue

                    async def send_handler():
                        loop = asyncio.get_event_loop()
                        while True:
                            data = await loop.run_in_executor(None, audio_queue.get)

                            if data == b'EOF':
                                await ws.send(json.dumps({"type":"eof"}))
                            else:
                                await ws.send(data)
                    await asyncio.gather(receive_handler(), send_handler())
                    
            except (websockets.exceptions.ConnectionClosed, OSError):
                print("Connection to Server lost or unavailable. Retrying...")
                brain.set_state(JarvisState.ERROR)
                await asyncio.sleep(5)

def network_loop(brain, audio_queue, playback_queue):
    asyncio.run(network_task(brain, audio_queue, playback_queue))
"""
import asyncio
import websockets
import pyaudio
import config
import io

SAMPLE_RATE = 22050
CHANNELS = 1

_ws = None
_loop = asyncio.new_event_loop()

async def _ensure_connected():
    global _ws
    try:
        if _ws is None:
            raise Exception("No connection")
        await _ws.ping()
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
    return _loop.run_until_complete(_stream_to_server(wav_io))
"""