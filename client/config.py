import os
from dotenv import load_dotenv

load_dotenv() # Load variables from .env

# Fallback to localhost if the variable isn't found
SERVER_IP = os.getenv("SERVER_IP", "127.0.0.1")

# config.py
COMPANION_NAME = "Jarvis"

# Audio Settings
MIC_DEVICE = "plughw:1,0"
RATE = 16000
SAMPLE_WIDTH = 2
FRAME_MS = 30
FRAME_BYTES = int(RATE * (FRAME_MS / 1000) * SAMPLE_WIDTH)

# Voice Activity Detection (VAD) Settings
END_SILENCE_MS = 600
MIN_UTTERANCE_MS = 300
MAX_UTTERANCE_MS = 8000
CONVO_TIMEOUT_MS = 8000
WAKE_PHRASES = [f"hey {COMPANION_NAME.lower()}", COMPANION_NAME.lower()]

# Screen Settings
MOUTH_BEAT_SEC = 0.02
W, H = 128, 64

# File Paths
WAKEWORD = "hey_jarvis"
WAKEWORD_MODEL_PATH = ["hey_jarvis"]