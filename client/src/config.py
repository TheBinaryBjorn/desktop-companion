"""
This module is config constants for all hardware modules.
"""

# Microphone Service:
MICROPHONE_SERVICE_FORMAT = 8
MICROPHONE_SERVICE_CHANNELS = 1
MICROPHONE_SERVICE_RATE = 16000
MICROPHONE_SERVICE_CHUNK_SIZE = 1280

PCM_BYTE_CHUNK_SIZE = 1280

# Wakeword Service:
WAKEWORD_MODEL_PATH = "models/hey_jarvis_v0.1.onnx"
WAKEWORD = "hey_jarvis_v0.1"
WAKEWORD_THRESHOLD = 0.7
