# STT CONFIG
STT_MODEL="small"
STT_DEVICE="cuda"
STT_COMPUTE_TYPE="int8"

# LLM CONFIG
LLM_MODEL="gemma3:4b"
LLM_SYSTEM_PROMPT="You are Jarvis. Reply in 2 sentences max and english characters only. No exceptions"
MAX_HISTORY_LENGTH=5

# TTS CONFIG
PIPER_EXE_PATH=r"C:\piper\piper.exe"
PIPER_VOICE_MODEL_PATH=r"C:\piper\en_US-hfc_male-medium.onnx"