# STT CONFIG
STT_MODEL="base"
STT_DEVICE="cpu"
STT_COMPUTE_TYPE="int8"

# LLM CONFIG
LLM_MODEL="gemma3:1b"
LLM_SYSTEM_PROMPT="You are Jarvis. Be brief. One or two sentences max. No special characters."
MAX_HISTORY_LENGTH=5

# TTS CONFIG
PIPER_EXE_PATH=r"C:\piper\piper.exe"
PIPER_VOICE_MODEL_PATH=r"C:\piper\en_US-amy-medium.onnx"