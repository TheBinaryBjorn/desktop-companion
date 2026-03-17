from abc import ABC, abstractmethod

class stream_service(ABC):
    @abstractmethod
    async def stream_to_client(self, ws):
        pass

class websocket_stream_service(stream_service):
    async def stream_to_client(self, websocket, event_loop, tts_proc, feed_task):
        while True:
            chunk = await event_loop.run_in_executor(None, tts_proc.stdout.read, 4096)
            if not chunk:
                break
            await websocket.send(chunk)
        #await feed_task