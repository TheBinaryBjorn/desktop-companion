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
1. install Raspberry Pi OS Lite
2. `sudo apt update && sudo apt install git -y`
3. `sudo apt install python3-dev -y`
4. pyaudio dependency: `sudo apt install portaudio19-dev -y`
5. enable i2c: `sudo raspi-config` Interface Options->I2C->Yes->Ok->Finish
6. `git clone https://github.com/TheBinaryBjorn/desktop-companion.git`
7. `cd desktop-companion/client`
8. install venv: `python -m venv .venv`
9. activate virtual environment: `source .venv/bin/activate`
10. install dependencies: `pip install pyaudio webrtcvad-wheels numpy dotenv adafruit-circuitpython-ssd1306 Pillow RPi.GPIO websockets`
11. install openwakeword: `pip install openwakeword` in case this causes a no disk space error, use:
    ```
    export TMPDIR=/home/[your_pi_username]/tmp
    mkdir -p $TMPDIR
    pip install openwakeword --cache-dir /home/[your_pi_username]/pip-cache
    ```
12. start the program: `python main.py`
