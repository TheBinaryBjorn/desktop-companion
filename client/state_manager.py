import threading
from enum import Enum, auto

class JarvisState(Enum):
    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()

"""
This is a singleton class to manage the states of Jarvis across multiple threads.
"""
class StateManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(StateManager, cls).__new__(cls)
                cls._instance.state = JarvisState.IDLE
        return cls._instance
    
    def set_state(self, new_state):
        if not isinstance(new_state, JarvisState):
            print(f"[Error] Invalid state rejected: {new_state}")
            return

        with self._lock:
            print(f"[System] State: {self.state.name} -> {new_state.name}")
            self.state = new_state
        