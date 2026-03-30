# mic_service.py
import json
import pyaudio
from vosk import Model, KaldiRecognizer
from state_manager import JarvisState
from config import VOSK_MODEL_PATH, RATE, WAKE_PHRASES

def mic_loop(brain, audio_queue):
    model = Model(VOSK_MODEL_PATH)
    recognizer = KaldiRecognizer(model, RATE)

    audio = pyaudio.PyAudio() # why do we need pyAudio here?

    # What are the parameters? what are they used for?
    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=2000)
    stream.start_stream()
    while True:
        data = stream.read(2000, exception_on_overflow=False)
        # IDLE or SPEAKING State
        if brain.state == JarvisState.IDLE:
            # It could be redundant to wait for the end of the speech if we detect jarvis in partial result
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                if "jarvis" in result.get("text", ""):
                    brain.set_state(JarvisState.LISTENING)
            else:
                partial = json.loads(recognizer.PartialResult())
                if "jarvis" in partial.get("partial", ""):
                    brain.set_state(JarvisState.LISTENING)
                    recognizer.Reset()
        # LISTENING State
        elif brain.state == JarvisState.LISTENING:
            audio_queue.put(data)
            # This silence detection could be why it rushes to send silence/jarvis speech to the server
            if recognizer.AcceptWaveform(data):
                brain.set_state(JarvisState.THINKING)
                audio_queue.put(b'EOF')
                recognizer.Reset()
        # SPEAKING - Flush the input buffer to prevent Jarvis from hearing himself.
        elif brain.state == JarvisState.SPEAKING:
            _ = stream.read(2000, exception_on_overflow=False)
            continue

"""
import sys, types
import io
import wave

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
import client.screen_service as screen_service

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


def capture_utterance(proc) -> io.BytesIO | None:
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

    # --- IN-MEMORY WAV CREATION ---
    # Create a byte stream in RAM
    wav_io = io.BytesIO()
    
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(config.RATE)
        wf.writeframes(bytes(speech))
    
    # Seek to the start so the next function can read it from the beginning
    wav_io.seek(0)
    
    return wav_io
"""