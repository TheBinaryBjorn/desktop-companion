# mic_in.py
import sys, types

# Mock pkg_resources for Vosk performance on Pi
if "pkg_resources" not in sys.modules:
    mock = types.ModuleType("pkg_resources")
    class _Dist:
        def __init__(self, name):
            self.version = "0.0.0"
    mock.get_distribution = _Dist
    sys.modules["pkg_resources"] = mock

import time, json, subprocess
import webrtcvad
from vosk import Model, KaldiRecognizer
import config
import screen

class ConvoTimeout(Exception):
    pass

vad = webrtcvad.Vad(2)
vosk_model = Model(config.VOSK_MODEL_PATH)

wake_grammar = json.dumps(config.WAKE_PHRASES)
wake_rec = KaldiRecognizer(vosk_model, config.RATE, wake_grammar)
wake_rec.SetWords(False)

def start_arecord():
    return subprocess.Popen(
        ["arecord", "-q", "-D", config.MIC_DEVICE, "-c", "1", "-r", str(config.RATE),
         "-f", "S16_LE", "-t", "raw"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )

def detect_wake(frame: bytes) -> bool:
    if wake_rec.AcceptWaveform(frame):
        txt = json.loads(wake_rec.Result()).get("text", "").strip().lower()
    else:
        txt = json.loads(wake_rec.PartialResult()).get("partial", "").strip().lower()
    return any(phrase in txt for phrase in config.WAKE_PHRASES)

def transcribe_vosk(pcm: bytes) -> str:
    rec = KaldiRecognizer(vosk_model, config.RATE)
    rec.SetWords(False)
    for i in range(0, len(pcm), 4000):
        rec.AcceptWaveform(pcm[i:i+4000])
    return json.loads(rec.FinalResult()).get("text", "").strip()

def capture_utterance(proc) -> str | None:
    speech = bytearray()
    in_speech = False
    silence_ms, utter_ms, idle_ms = 0, 0, 0
    start_time = time.time()

    while True:
        f = proc.stdout.read(config.FRAME_BYTES)
        if not f or len(f) < config.FRAME_BYTES:
            time.sleep(0.01)
            continue

        is_speech = vad.is_speech(f, config.RATE)
        speech.extend(f)

        if is_speech:
            in_speech = True
            silence_ms = 0
            idle_ms = 0
            utter_ms += config.FRAME_MS
        elif in_speech:
            silence_ms += config.FRAME_MS
        else:
            idle_ms += config.FRAME_MS

        if not in_speech and idle_ms >= config.CONVO_TIMEOUT_MS:
            raise ConvoTimeout()

        if in_speech and silence_ms >= config.END_SILENCE_MS:
            break
        if utter_ms >= config.MAX_UTTERANCE_MS:
            break
        if time.time() - start_time > 15:
            break

    if utter_ms < config.MIN_UTTERANCE_MS:
        return None

    screen.draw_eyes("thinking")
    text = transcribe_vosk(bytes(speech)).strip()
    screen.draw_eyes("listening")
    return text or None