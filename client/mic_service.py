# mic_service.py
import json, pyaudio, wave, time, numpy as np, onnxruntime as ort
from vosk import Model, KaldiRecognizer
from state_manager import JarvisState
from config import VOSK_MODEL_PATH, RATE

import onnxruntime as ort
import numpy as np

class SileroVAD:
    def __init__(self, model_path="models/silero_vad.onnx"):
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        self.session = ort.InferenceSession(model_path,
                                            sess_options=opts,
                                            providers=['CPUExecutionProvider'])
        self.reset_state()

    def reset_state(self):
        # Clears the RNN memory so old noise doesn't affect new detection
        self._state = np.zeros((2, 1, 128)).astype('float32')

    def is_speech(self, audio_data, threshold=0.7):
        # Input: 512 samples of float32 normalized audio
        inputs = {
            "input": audio_data.reshape(1, -1),
            "sr": np.array([16000], dtype=np.int64),
            "state": self._state
        }
        
        # Run Inference
        out, self._state = self.session.run(None, inputs)
        
        # Return True/False based on probability
        return out[0][0] > threshold

def detect_speech(vad, data):
    # Convert Int16 Bytes to Float32
    audio_int16 = np.frombuffer(data, dtype=np.int16)[:512]
    audio_float32 = audio_int16.astype(np.float32) / 32768.0
    return vad.is_speech(audio_float32)

def load_feedback_sound_bytes():
    with wave.open("sounds/wakeword_feedback_sound.wav", 'rb') as wf:
        return wf.readframes(wf.getnframes())

def play_wakeword_feedback(playback_queue, sound_bytes):
    playback_queue.put(sound_bytes)
    playback_queue.put(b'EOF')

def mic_loop(brain, audio_queue, playback_queue):
    model = Model(VOSK_MODEL_PATH)
    recognizer = KaldiRecognizer(model, RATE)
    vad = SileroVAD()
    audio = pyaudio.PyAudio()

    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=2000)
    stream.start_stream()
    beep_bytes = load_feedback_sound_bytes()
    user_voice_detected = False
    just_entered_listening = True
    entered_listening_timestamp = time.time()
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
            if just_entered_listening:
                entered_listening_timestamp = time.time()
                just_entered_listening = False
                user_voice_detected = False
                vad.reset_state()

            # Detect if the user spoke.
            is_speech = detect_speech(vad, data)

            if is_speech:
                user_voice_detected = True

            # Send audio bytes to network thread
            audio_queue.put(data)

            # If end of speech is detected, reset and switch state to thinking.
            if recognizer.AcceptWaveform(data):
                recognizer.Reset()
                user_voice_detected = False
                just_entered_listening = True
                vad.reset_state()
                audio_queue.put(b'EOF')
                brain.set_state(JarvisState.THINKING)

            # if no voice is detected, and 5.0 seconds pass since first entering the loop,
            # reset and switch to idle state.
            if not user_voice_detected and time.time() - entered_listening_timestamp > 5.0:
                # switch to idle
                recognizer.Reset()
                just_entered_listening = True
                vad.reset_state()
                brain.set_state(JarvisState.IDLE)
     
        # SPEAKING - Flush the input buffer to prevent Jarvis from hearing himself.
        elif brain.state == JarvisState.SPEAKING:
            _ = stream.read(2000, exception_on_overflow=False)
            continue