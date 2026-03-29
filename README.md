# desktop-companion
## Setup
### Server
1. install ollama, faster_whisper, websockets and piper_tts:
`pip install ollama faster_whisper websockets piper_tts`
2. Set up piper tts: 
      1. Download piper from [/rhasspy/piper](https://github.com/rhasspy/piper)
      2. Pick a voice model from [Voice Samples](https://rhasspy.github.io/piper-samples/)
      3. download `.onnx` and `.onnx.json` files from [HuggingFace](https://huggingface.co/rhasspy/piper-voices/tree/main) and place them in your piper installation folder.
      4. Update path in server/config.py
```
# TTS CONFIG
PIPER_EXE_PATH=r"path to your piper.exe"
PIPER_VOICE_MODEL_PATH=r"path to your voice model .onnx file"
```
3. For GPU systems: `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12`
4. copy `cublas64_12.dll` from `venv/Lib/site-packages/nvidia/cublas/bin` to `venv/Lib/site-packages/ctranslate`
5. set device to "cuda" in `server/config.py`
```
# STT CONFIG
STT_MODEL="small"
STT_DEVICE="cpu" <- set to "cuda"
STT_COMPUTE_TYPE="int8"
```

### Client
