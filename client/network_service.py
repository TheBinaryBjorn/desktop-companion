import json, websockets, asyncio, queue
from state_manager import JarvisState
from config import SERVER_IP

async def network_task(brain, shutdown_event, startup_barrier, audio_queue, playback_queue):
    uri = f"ws://{SERVER_IP}:8000/stream"
    is_first_connection = True
    print("[Network Thread]: Connecting to the server...")
    while not shutdown_event.is_set():
        try:
            async with websockets.connect(uri) as ws:
                print("Connected to server.")
                if brain.state == JarvisState.ERROR:
                    brain.set_state(JarvisState.IDLE)
                if is_first_connection:
                    print("[Network Thread]: Waiting for hardware...")
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, startup_barrier.wait)
                    is_first_connection = False
                    print("[Network Thread]: All systems go! Ready to stream.")
                async def receive_handler():
                    first_chunk_received = False
                    while not shutdown_event.is_set():
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
                    while not shutdown_event.is_set():
                        try:
                            data = await loop.run_in_executor(None, lambda: audio_queue.get(timeout=1.0))

                            if data == b'EOF':
                                await ws.send(json.dumps({"type":"eof"}))
                            else:
                                await ws.send(data)
                        except queue.Empty:
                            continue
                await asyncio.gather(receive_handler(), send_handler())
                
        except (websockets.exceptions.ConnectionClosed, OSError):
            if shutdown_event.is_set():
                break
            print("Connection to Server lost or unavailable. Retrying...")
            brain.set_state(JarvisState.ERROR)
            await asyncio.sleep(5)

def network_loop(brain, shutdown_event, startup_barrier, audio_queue, playback_queue):
    asyncio.run(network_task(brain, shutdown_event, startup_barrier, audio_queue, playback_queue))