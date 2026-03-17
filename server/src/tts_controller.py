from abc import ABC, abstractmethod
import config, subprocess, time, asyncio

class tts_service(ABC):
    @abstractmethod
    async def synthesize_stream(self, stream):
        pass

class piper_service(tts_service):
    async def synthesize_stream(self, stream):
        t_start = time.time()
        # Start Piper subprocess for this request
        piper_proc = subprocess.Popen(
                    [config.PIPER_EXE_PATH, "-m", config.PIPER_VOICE_MODEL_PATH, "--output-raw"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL
                )
        
        # Feed tokens to Piper in background
        async def feed_piper():
            full = ""
            for chunk in stream:
                token = chunk['message']['content']
                full += token
                piper_proc.stdin.write(token.encode())
                piper_proc.stdin.flush()
            piper_proc.stdin.close()
            print(f"[{time.time()-t_start:.2f}s total] Jarvis: {full}")
        
        # Start feeding task
        feed_task = asyncio.create_task(feed_piper())
        
        # Return the process for reading audio
        return piper_proc
