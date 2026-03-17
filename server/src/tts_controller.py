from abc import ABC, abstractmethod
import config, subprocess, time, asyncio

class tts_service(ABC):
    @abstractmethod
    async def synthesize_stream(self, stream, llm_service):
        pass

class piper_service(tts_service):
    async def synthesize_stream(self, stream, llm_service):
        t_start = time.time()

        piper_proc = subprocess.Popen(
            [config.PIPER_EXE_PATH, "-m", config.PIPER_VOICE_MODEL_PATH, "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )

        async def feed_piper():
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

            # Flush any remaining text
            if buffer.strip():
                piper_proc.stdin.write(buffer.encode())
                piper_proc.stdin.flush()

            piper_proc.stdin.close()
            llm_service.save_response(full)
            print(f"[{time.time()-t_start:.2f}s total] Jarvis: {full}")

        feed_task = asyncio.create_task(feed_piper())
        return piper_proc, feed_task