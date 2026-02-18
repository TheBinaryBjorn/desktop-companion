import os, time, subprocess, json
from dotenv import load_dotenv
from google import genai

import board, busio
from PIL import Image, ImageDraw
import adafruit_ssd1306

from vosk import Model, KaldiRecognizer

load_dotenv()
gclient = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

MIC_DEVICE = "plughw:1,0"
RATE = 16000
W, H = 128, 64

# OLED
i2c = busio.I2C(board.SCL, board.SDA)
display = adafruit_ssd1306.SSD1306_I2C(W, H, i2c)
display.fill(0); display.show()

# Companion Settings
COMPANION_NAME = "Jarvis"

def draw_eyes(state="idle"):
    img = Image.new("1", (W, H))
    d = ImageDraw.Draw(img)
    if state == "idle":
        d.ellipse((20,20,50,50), fill=255); d.ellipse((78,20,108,50), fill=255)
    elif state == "listening":
        d.ellipse((15,15,55,55), fill=255); d.ellipse((73,15,113,55), fill=255)
    elif state == "thinking":
        d.ellipse((20,25,50,45), fill=255); d.ellipse((78,25,108,45), fill=255)
    elif state == "speaking":
        d.pieslice((18,18,52,52), 200, 340, fill=255)
        d.pieslice((76,18,110,52), 200, 340, fill=255)
    elif state == "blink":
        d.rectangle((20,30,50,34), fill=255); d.rectangle((78,30,108,34), fill=255)
    display.image(img); display.show()

def blink():
    draw_eyes("blink"); time.sleep(0.12); draw_eyes("idle")

def gemini_reply(user_text: str) -> str:
    prompt = f"You are a cute desk companion, your name is {COMPANION_NAME}. Reply in 1–2 short sentences using text only.\nUser: {user_text}"
    try:
        r = gclient.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    except Exception:
        error_message = "Sorry, something went wrong..."
        return error_message
    return (r.text or "").strip()

def speak(text: str):
    draw_eyes("speaking")
    subprocess.run(["espeak", text], check=False)
    draw_eyes("idle")

# Load Vosk model (path you unzipped)
vosk_model_path = "/home/daniel/deskpet/models/vosk-model-small-en-us-0.15"
model = Model(vosk_model_path)
rec = KaldiRecognizer(model, RATE)

def record_and_transcribe(seconds=4) -> str:
    # stream raw PCM from arecord and feed to Vosk
    draw_eyes("listening")
    p = subprocess.Popen(
        ["arecord", "-q", "-D", MIC_DEVICE, "-c", "1", "-r", str(RATE), "-f", "S16_LE", "-t", "raw", "-d", str(seconds)],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )
    rec.Reset()
    while True:
        data = p.stdout.read(4000)
        if not data:
            break
        rec.AcceptWaveform(data)
    result = json.loads(rec.FinalResult())
    return (result.get("text") or "").strip()

print("Deskpet: OLED + Vosk STT + Gemini text (Ctrl+C to stop)")
draw_eyes("idle")

try:
    while True:
        blink()
        text = record_and_transcribe(seconds=4)

        if not text:
            draw_eyes("idle")
            print("No speech."); continue

        draw_eyes("thinking")
        print("You:", text)

        reply = gemini_reply(text)
        print("Deskpet:", reply)

        if reply:
            speak(reply)

        time.sleep(0.2)

except KeyboardInterrupt:
    display.fill(0); display.show()
    print("\nStopped.")
