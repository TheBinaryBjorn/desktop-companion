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

### Client Setup Guide

#### Prerequisites
- Raspberry Pi Zero 2 W
- MicroSD card (16GB+, Samsung Endurance or SanDisk Max Endurance recommended)
- INMP441 I2S microphone
- Fresh install of Raspberry Pi OS Lite (64-bit)

#### Installation Steps

#### 1. System Dependencies
```bash
sudo apt update && sudo apt install git python3-dev portaudio19-dev -y
```

#### 2. I2S Microphone Overlay
```bash
echo 'dtoverlay=googlevoicehat-soundcard' | sudo tee -a /boot/firmware/config.txt
sudo reboot
```

#### 3. Enable I2C (for OLED display)
```bash
sudo raspi-config
```
Navigate to: **Interface Options → I2C → Yes → OK → Finish**

#### 4. Clone the Repository
```bash
git clone https://github.com/TheBinaryBjorn/desktop-companion.git
cd desktop-companion/client
```

#### 5. Create Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### 6. Install Dependencies
```bash
pip install pyaudio webrtcvad-wheels numpy python-dotenv adafruit-circuitpython-ssd1306 Pillow RPi.GPIO websockets
```

#### 7. Install openWakeWord
```bash
pip install openwakeword
```

> **If you get a "No space left on device" error**, run this instead:
> ```bash
> export TMPDIR=/home/[your_pi_username]/tmp
> mkdir -p $TMPDIR
> pip install openwakeword --cache-dir /home/[your_pi_username]/pip-cache
> ```

#### 8. Create Environment File
```bash
nano .env
```
Add the following:
```
SERVER_IP=[Your Server IP]
```
You can find your server ip by running `ipconfig` on you server pc.

#### 9. Run
```bash
python main.py
```

### Optional: Extend SD Card Lifespan
```bash
sudo systemctl disable dphys-swapfile
echo 'gpu_mem=16' | sudo tee -a /boot/firmware/config.txt
sudo reboot
```
