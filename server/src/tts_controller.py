from abc import ABC, abstractmethod
import config, subprocess, time, asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=2)

class tts_service(ABC):
    @abstractmethod
    async def synthesize_stream(self, stream, llm_service):
        pass

class piper_service(tts_service):
    async def synthesize_stream(self, stream, llm_service):
        t_start = time.time()
        loop = asyncio.get_event_loop()

        piper_proc = subprocess.Popen(
            [config.PIPER_EXE_PATH, "-m", config.PIPER_VOICE_MODEL_PATH, "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        def feed_piper_blocking():
            """Runs in thread pool — blocking Ollama stream + blocking Piper stdin writes."""
            full = ""
            buffer = ""
            sentence_endings = {'.', '!', '?', '\n'}

            for chunk in stream:
                token = chunk['message']['content']
                full += token
                buffer += token

                if any(buffer.rstrip().endswith(ending) for ending in sentence_endings):
                    if buffer.strip():
                        piper_proc.stdin.write(buffer.encode())
                        piper_proc.stdin.flush()
                        buffer = ""

            # Flush remaining
            if buffer.strip():
                piper_proc.stdin.write(buffer.encode())
                piper_proc.stdin.flush()

            piper_proc.stdin.close()
            llm_service.save_response(full)
            print(f"[{time.time()-t_start:.2f}s total] Jarvis: {full}")

        feed_task = loop.run_in_executor(_executor, feed_piper_blocking)
        return piper_proc, feed_task