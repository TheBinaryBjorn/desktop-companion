import json, websockets, asyncio
from state_manager import JarvisState
from config import SERVER_IP

async def network_task(brain, audio_queue, playback_queue):
    uri = f"ws://{SERVER_IP}:8000/stream"
    print("[Network Thread]: Ready!")
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