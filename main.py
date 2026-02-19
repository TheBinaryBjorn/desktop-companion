import sys, types

if "pkg_resources" not in sys.modules:
    mock = types.ModuleType("pkg_resources")

    class _Dist:
        def __init__(self, name):
            self.version = "0.0.0"

    mock.get_distribution = _Dist
    sys.modules["pkg_resources"] = mock

import os, time, json, subprocess, threading
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
SAMPLE_WIDTH = 2
FRAME_MS = 30
FRAME_BYTES = int(RATE * (FRAME_MS/1000) * SAMPLE_WIDTH)

WAKE_PHRASES = [f"hey {COMPANION_NAME.lower()}", COMPANION_NAME.lower()]

vad = webrtcvad.Vad(2)
END_SILENCE_MS = 600
MIN_UTTERANCE_MS = 300
MAX_UTTERANCE_MS = 8000
CONVO_TIMEOUT_MS = 8000

# espeak default speed is ~160 wpm (~2.7 words/sec)
# Each mouth open/close cycle should feel like one syllable beat (~0.15s)
MOUTH_BEAT_SEC = 0.02

# OLED
W, H = 128, 64
i2c = busio.I2C(board.SCL, board.SDA)
display = adafruit_ssd1306.SSD1306_I2C(W, H, i2c)
display.fill(0); display.show()

# -----------------------
# Drawing
# -----------------------

def _draw_frame(img):
    display.image(img); display.show()

def _make_eyes(d, state="idle"):
    if state == "idle":
        d.ellipse((20, 20, 50, 50), fill=255)
        d.ellipse((78, 20, 108, 50), fill=255)
    elif state == "listening":
        d.ellipse((15, 15, 55, 55), fill=255)
        d.ellipse((73, 15, 113, 55), fill=255)
    elif state == "thinking":
        d.ellipse((20, 25, 50, 45), fill=255)
        d.ellipse((78, 25, 108, 45), fill=255)
    elif state == "blink":
        d.rectangle((20, 30, 50, 34), fill=255)
        d.rectangle((78, 30, 108, 34), fill=255)

def _rounded_rect(d, x0, y0, x1, y1, radius, fill=255):
    """Draw a filled rounded rectangle."""
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    d.rectangle((x0 + r, y0, x1 - r, y1), fill=fill)
    d.rectangle((x0, y0 + r, x1, y1 - r), fill=fill)
    d.ellipse((x0, y0, x0 + 2*r, y0 + 2*r), fill=fill)
    d.ellipse((x1 - 2*r, y0, x1, y0 + 2*r), fill=fill)
    d.ellipse((x0, y1 - 2*r, x0 + 2*r, y1), fill=fill)
    d.ellipse((x1 - 2*r, y1 - 2*r, x1, y1), fill=fill)

def _draw_mouth(d, amount):
    """
    Draw a rounded-rectangle mouth below the eyes.
    amount: 0.0 (closed) to 1.0 (fully open)
    """
    mx = 64
    my = 57
    half_w = 20
    min_h = 2
    max_h = 9
    radius = 3

    h = int(min_h + amount * (max_h - min_h))
    x0, y0 = mx - half_w, my - h
    x1, y1 = mx + half_w, my + h

    if h <= min_h:
        d.rectangle((x0, my - 1, x1, my + 1), fill=255)
    else:
        _rounded_rect(d, x0, y0, x1, y1, radius)

def draw_eyes(state="idle"):
    img = Image.new("1", (W, H))
    d = ImageDraw.Draw(img)
    _make_eyes(d, state)
    _draw_frame(img)

# -----------------------
# Mouth animation
# Fixed to espeak's default rate (~160wpm), one beat per syllable (~0.15s)
# -----------------------
_speaking = False

def _animate_mouth():
    # Each step in pattern = one MOUTH_BEAT_SEC interval
    # Two steps per open/close cycle gives a natural lip-flap rhythm
    pattern = [0.0, 1.0, 0.0, 1.0, 0.0, 0.8,
               0.0, 1.0, 0.0, 0.6, 0.0, 1.0]
    i = 0
    while _speaking:
        img = Image.new("1", (W, H))
        d = ImageDraw.Draw(img)
        _make_eyes(d, "idle")
        _draw_mouth(d, pattern[i % len(pattern)])
        _draw_frame(img)
        i += 1
        time.sleep(MOUTH_BEAT_SEC)
    draw_eyes("idle")

def speak(text: str):
    global _speaking
    _speaking = True
    anim_thread = threading.Thread(target=_animate_mouth, daemon=True)
    anim_thread.start()

    subprocess.run(["espeak", text], check=False)

    _speaking = False
    anim_thread.join(timeout=0.5)

    # Drain ~500ms of stale mic audio accumulated during TTS
    drain_frames = int(500 / FRAME_MS)
    for _ in range(drain_frames):
        proc.stdout.read(FRAME_BYTES)

# -----------------------
# Gemini
# -----------------------

def gemini_reply(user_text: str) -> str:
    history.append(f"User: {user_text}")
    context = "\n".join(history)
    prompt = (
        f"You are a cute desk companion named {COMPANION_NAME}. "
        f"Reply in 1–2 short sentences. "
        f"Reply with plain text only — no markdown, no asterisks, no formatting of any kind.\n"
        f"{context}\nAssistant:"
    )
    try:
        r = gclient.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt)
        reply = (r.text or "").strip()
    except Exception as e:
        print(f"[Gemini error: {e}]")
        reply = "Sorry, something went wrong."
    history.append(f"Assistant: {reply}")
    return reply

# -----------------------
# Audio stream
# -----------------------

def start_arecord():
    return subprocess.Popen(
        ["arecord", "-q", "-D", MIC_DEVICE, "-c", "1", "-r", str(RATE),
         "-f", "S16_LE", "-t", "raw"],
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
    speech = bytearray()
    in_speech = False
    silence_ms = 0
    utter_ms = 0
    idle_ms = 0
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

        if not in_speech and idle_ms >= CONVO_TIMEOUT_MS:
            raise ConvoTimeout()

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

history = deque(maxlen=8)

draw_eyes("idle")

try:
    proc = start_arecord()

    while True:
        frame = proc.stdout.read(FRAME_BYTES)
        if not frame or len(frame) < FRAME_BYTES:
            time.sleep(0.01)
            continue

        if not detect_wake(frame):
            continue

        wake_rec.Reset()
        draw_eyes("listening")
        history.clear()

        print(f"[Conversation started — will end after {CONVO_TIMEOUT_MS//1000}s of silence]")

        while True:
            try:
                text = capture_utterance()
            except ConvoTimeout:
                print("[Conversation ended — no follow-up detected]")
                draw_eyes("idle")
                wake_rec.Reset()
                break

            if not text:
                draw_eyes("listening")
                continue

            print("You:", text)
            draw_eyes("thinking")
            reply = gemini_reply(text)
            print(f"{COMPANION_NAME}:", reply)

            if reply:
                speak(reply)

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
