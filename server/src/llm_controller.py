from abc import ABC, abstractmethod
from collections import deque
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
    def __init__(self):
        self.history = deque(maxlen=config.MAX_HISTORY_LENGTH)

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
        self.history.append({'role' : 'user', 'content' : prompt})

        stream = ollama.chat(
                        model=config.LLM_MODEL,
                        messages=[
                            {'role': 'system', 'content': config.LLM_SYSTEM_PROMPT},
                            *self.history
                        ],
                        stream=True
                    )
        return stream
    
    def save_response(self, response: str):
        self.history.append({'role': 'assistant', 'content': response})

    def reset_history(self):
        self.history.clear()
        
        