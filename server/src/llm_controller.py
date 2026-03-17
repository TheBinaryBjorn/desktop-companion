from abc import ABC, abstractmethod
import config, time, subprocess, ollama

class llm_service(ABC):
    @abstractmethod
    def start_service(self):
        pass
    @abstractmethod
    def _prewarm(self):
        pass
    @abstractmethod
    def send_prompt(self):
        pass

class ollama_service(llm_service):
    def start_service(self):
        print("Starting Ollama...")
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
        self._prewarm()

    def _prewarm(self):
        print("Pre-warming Ollama...")
        ollama.chat(model='gemma3:1b', messages=[{'role': 'user', 'content': 'hi'}])
        print("Ready.")

    def send_prompt(self, prompt):
        # Try to send a message, raise exception if failed
        return ollama.chat(
                        model=config.LLM_MODEL,
                        messages=[
                            {'role': 'system', 'content': config.LLM_SYSTEM_PROMPT},
                            {'role': 'user', 'content': prompt}
                        ],
                        stream=True
                    )
        
        