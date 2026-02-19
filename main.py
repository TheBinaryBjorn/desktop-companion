import sys, types

if "pkg_resources" not in sys.modules:
    mock = types.ModuleType("pkg_resources")

    class _Dist:
        def __init__(self, name):
            self.version = "0.0.0"

    mock.get_distribution = _Dist
    sys.modules["pkg_resources"] = mock

import os, time, json, subprocess
from collections import deque
from dotenv import load_dotenv
from google import genai
import webrtcvad
from vosk import Model, KaldiRecognizer

import board, busio
from PIL import Image, ImageDraw
import adafruit_ssd1306

# -----------------------
# Config
# -----------------------
load_dotenv()
gclient = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

COMPANION_NAME = "Jarvis"

MIC_DEVICE = "plughw:1,0"
RATE = 16000
SAMPLE_WIDTH = 2  # 16-bit PCM
FRAME_MS = 30     # 10/20/30 only
FRAME_BYTES = int(RATE * (FRAME_MS/1000) * SAMPLE_WIDTH)

# Wake phrases derived from COMPANION_NAME
WAKE_PHRASES = [f"hey {COMPANION_NAME.lower()}", COMPANION_NAME.lower()]

# VAD tuning
vad = webrtcvad.Vad(2)          # 0..3 (more aggressive -> fewer false triggers)
END_SILENCE_MS = 600            # silence within an utterance to stop capture
MIN_UTTERANCE_MS = 300          # ignore tiny blips
MAX_UTTERANCE_MS = 8000         # cap per utterance (safety)

# Conversation mode: how long to wait (ms) for a follow-up before going back
# to wake-word detection. Resets after each exchange.
CONVO_TIMEOUT_MS = 8000         # 8 seconds of silence = end of conversation

# OLED
W, H = 128, 64
i2c = busio.I2C(board.SCL, board.SDA)
display = adafruit_ssd1306.SSD1306_I2C(W, H, i2c)
display.fill(0); display.show()

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

def speak(text: str):
    draw_eyes("speaking")
    subprocess.run(["espeak", text], check=False)
    draw_eyes("idle")
    # Drain ~500ms of stale mic audio accumulated during TTS playback
    drain_frames = int(500 / FRAME_MS)
    for _ in range(drain_frames):
        proc.stdout.read(FRAME_BYTES)

def gemini_reply(user_text: str) -> str:
    history.append(f"User: {user_text}")
    context = "\n".join(history)
    prompt = f"You are a cute desk companion named {COMPANION_NAME}. Reply in 1–2 short sentences.\n{context}\nAssistant:"
    r = gclient.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
    reply = (r.text or "").strip()
    history.append(f"Assistant: {reply}")
    return reply

# -----------------------
# Audio stream (continuous)
# -----------------------
def start_arecord():
    return subprocess.Popen(
        ["arecord", "-q", "-D", MIC_DEVICE, "-c", "1", "-r", str(RATE), "-f", "S16_LE", "-t", "raw"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )

# -----------------------
# Vosk setup
# -----------------------
VOSK_MODEL_PATH = "/home/daniel/deskpet/models/vosk-model-small-en-us-0.15"
vosk_model = Model(VOSK_MODEL_PATH)

wake_grammar = json.dumps(WAKE_PHRASES)
wake_rec = KaldiRecognizer(vosk_model, RATE, wake_grammar)
wake_rec.SetWords(False)

def detect_wake(frame: bytes) -> bool:
    if wake_rec.AcceptWaveform(frame):
        txt = json.loads(wake_rec.Result()).get("text", "").strip().lower()
    else:
        txt = json.loads(wake_rec.PartialResult()).get("partial", "").strip().lower()
    return any(phrase in txt for phrase in WAKE_PHRASES)

def transcribe_vosk(pcm: bytes) -> str:
    rec = KaldiRecognizer(vosk_model, RATE)
    rec.SetWords(False)
    for i in range(0, len(pcm), 4000):
        rec.AcceptWaveform(pcm[i:i+4000])
    return json.loads(rec.FinalResult()).get("text", "").strip()

def capture_utterance() -> str | None:
    """
    Listen for a single utterance using VAD.
    Returns transcribed text, or None if:
      - nothing was said within CONVO_TIMEOUT_MS (caller should end conversation)
      - utterance was too short (blip)
    Raises ConvoTimeout if the user stayed silent too long.
    """
    speech = bytearray()
    in_speech = False
    silence_ms = 0
    utter_ms = 0
    idle_ms = 0          # tracks silence before speech even starts
    start_time = time.time()

    while True:
        f = proc.stdout.read(FRAME_BYTES)
        if not f or len(f) < FRAME_BYTES:
            time.sleep(0.01)
            continue

        is_speech = vad.is_speech(f, RATE)
        speech.extend(f)

        if is_speech:
            in_speech = True
            silence_ms = 0
            idle_ms = 0
            utter_ms += FRAME_MS
        elif in_speech:
            silence_ms += FRAME_MS
        else:
            idle_ms += FRAME_MS

        # User stayed silent too long without saying anything → end conversation
        if not in_speech and idle_ms >= CONVO_TIMEOUT_MS:
            raise ConvoTimeout()

        # End of utterance after speech detected
        if in_speech and silence_ms >= END_SILENCE_MS:
            break
        if utter_ms >= MAX_UTTERANCE_MS:
            break
        if time.time() - start_time > 15:
            break

    if utter_ms < MIN_UTTERANCE_MS:
        return None

    draw_eyes("thinking")
    text = transcribe_vosk(bytes(speech)).strip()
    draw_eyes("listening")
    return text or None


class ConvoTimeout(Exception):
    pass


# -----------------------
# Main loop
# -----------------------
print(f"{COMPANION_NAME} running: wake word + continuous conversation (Ctrl+C to stop)")

# Conversation memory (last 4 exchanges = 8 entries)
history = deque(maxlen=8)

draw_eyes("idle")

try:
    proc = start_arecord()

    while True:
        # --- Waiting for wake word ---
        frame = proc.stdout.read(FRAME_BYTES)
        if not frame or len(frame) < FRAME_BYTES:
            time.sleep(0.01)
            continue

        if not detect_wake(frame):
            continue

        # --- Wake word detected: enter conversation mode ---
        wake_rec.Reset()
        draw_eyes("listening")
        #speak(f"Hello, I'm {COMPANION_NAME}")
        history.clear()  # fresh history each new conversation

        print(f"[Conversation started — will end after {CONVO_TIMEOUT_MS//1000}s of silence]")

        while True:  # conversation loop
            try:
                text = capture_utterance()
            except ConvoTimeout:
                print("[Conversation ended — no follow-up detected]")
                speak("Talk to you later!")
                draw_eyes("idle")
                wake_rec.Reset()
                break

            if not text:
                # Short blip, stay in conversation and keep listening
                draw_eyes("listening")
                continue

            print("You:", text)
            draw_eyes("thinking")
            reply = gemini_reply(text)
            print(f"{COMPANION_NAME}:", reply)

            if reply:
                speak(reply)

            # Stay in listening state, ready for follow-up
            draw_eyes("listening")

except KeyboardInterrupt:
    pass
finally:
    try:
        proc.terminate()
    except Exception:
        pass
    display.fill(0); display.show()
    print("\nStopped.")
