# mic_service.py
import json, pyaudio, numpy as np, wave
from vosk import Model, KaldiRecognizer
from state_manager import JarvisState
from config import VOSK_MODEL_PATH, RATE

def load_feedback_sound_bytes():
    with wave.open("sounds/wakeword_feedback_sound.wav", 'rb') as wf:
        return wf.readframes(wf.getnframes())

def play_wakeword_feedback(playback_queue, sound_bytes):
    playback_queue.put(sound_bytes)
    playback_queue.put(b'EOF')

def mic_loop(brain, audio_queue, playback_queue):
    model = Model(VOSK_MODEL_PATH)
    recognizer = KaldiRecognizer(model, RATE)

    audio = pyaudio.PyAudio()

    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=2000)
    stream.start_stream()
    beep_bytes = load_feedback_sound_bytes()
    print("[Mic Thread]: Ready!")
    while True:
        data = stream.read(2000, exception_on_overflow=False)
        # IDLE or SPEAKING State
        if brain.state == JarvisState.IDLE:
            # It could be redundant to wait for the end of the speech if we detect jarvis in partial result
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                if "jarvis" in result.get("text", ""):
                    recognizer.Reset()
                    play_wakeword_feedback(playback_queue, beep_bytes)
            else:
                partial = json.loads(recognizer.PartialResult())
                if "jarvis" in partial.get("partial", ""):
                    recognizer.Reset()
                    play_wakeword_feedback(playback_queue, beep_bytes)
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