import wave, time, pyaudio, webrtcvad, numpy as np
from openwakeword.model import Model
from config import RATE, WAKEWORD, WAKEWORD_MODEL_PATH
from state_manager import JarvisState

OWW_CHUNK = 1280 # 1280 samples (80ms at 16kHz)
VAD_CHUNK = 320 # 320 samples (20ms at 16kHz)
NO_SPEECH_TIMEOUT = 5.0 # Seconds with no speech detected before returning to IDLE
POST_SPEECH_SILENCE = 1.0 # Seconds of silence after speech before treating utterance as complete
WAKEWORD_THRESHOLD = 0.5 # openWakeWord detection threshold
GAIN = 10.0

def _amplify(data: bytes, gain: float) -> bytes:
    samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
    amplified = np.clip(samples * gain, -32768, 32767)
    return amplified.astype(np.int16).tobytes()

def detect_wakeword(model: Model, data: bytes) -> bool:
    audio_array = np.frombuffer(data, dtype=np.int16)
    prediction = model.predict(audio_array)
    return prediction[WAKEWORD] > WAKEWORD_THRESHOLD

def detect_speech(vad: webrtcvad.Vad, data: bytes) -> bool:
    n_windows = len(data) // (VAD_CHUNK * 2)
    for i in range(n_windows):
        window = data[i * VAD_CHUNK * 2 : (i + 1) * VAD_CHUNK * 2]
        if vad.is_speech(window, RATE):
            return True
    return False

def load_feedback_sound_bytes() -> bytes:
    with wave.open("sounds/wakeword_feedback_sound.wav", "rb") as wf:
        return wf.readframes(wf.getnframes())

def play_wakeword_feedback(playback_queue, sound_bytes: bytes):
    playback_queue.put(sound_bytes)
    playback_queue.put(b"EOF")

def post_speech_timeout_passed(now, last_speech_at, post_speech_silence):
    return now - last_speech_at > post_speech_silence

def listening_state_timeout_passed(now, listening_entered_at, no_speech_timeout):
    return now - listening_entered_at > no_speech_timeout

def mic_loop(brain, audio_queue, playback_queue):
    oww_model = Model([WAKEWORD_MODEL_PATH])
    vad = webrtcvad.Vad(2)
    audio = pyaudio.PyAudio()
    stream = audio.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=RATE,
        input=True,
        frames_per_buffer=OWW_CHUNK,
    )
    stream.start_stream()
    beep_bytes = load_feedback_sound_bytes()

    # Listening state bookkeeping
    prev_state = None
    user_voice_detected = False
    listening_entered_at = 0.0
    last_speech_at = 0.0
    last_wakeword_time = 0.0

    print("[Mic Thread]: Ready!")

    while True:
        current_state = brain.state

        # State entry setup
        if current_state != prev_state:
            if current_state == JarvisState.LISTENING:
                user_voice_detected = False
                listening_entered_at = time.time()
                last_speech_at = time.time()
            prev_state = current_state

        # IDLE: listen for wakeword
        if current_state == JarvisState.IDLE:
            data = stream.read(OWW_CHUNK, exception_on_overflow=False)
            #data = _amplify(data, GAIN)
            now = time.time()
            if detect_wakeword(oww_model, data) and now - last_wakeword_time > 2.0:
                last_wakeword_time = now
                play_wakeword_feedback(playback_queue, beep_bytes)

        # LISTENING: record speech until silence
        elif current_state == JarvisState.LISTENING:

            # Read one OWW_CHUNK
            data = stream.read(OWW_CHUNK, exception_on_overflow=False)
            #data = _amplify(data, GAIN)

            # Detect speech in voice chunk
            if detect_speech(vad, data):
                user_voice_detected = True
                last_speech_at = time.time()

            # Only queue audio once speech has started
            if user_voice_detected:
                audio_queue.put(data)

            now = time.time()
            # End of speech, silence after talking
            if user_voice_detected and post_speech_timeout_passed(now, last_speech_at, POST_SPEECH_SILENCE):
                audio_queue.put(b"EOF")
                brain.set_state(JarvisState.THINKING)

            # No speech at all within timeout — give up
            elif not user_voice_detected and listening_state_timeout_passed(now, listening_entered_at, NO_SPEECH_TIMEOUT):
                brain.set_state(JarvisState.IDLE)

        # SPEAKING: flush mic so Jarvis doesn't hear himself
        elif current_state == JarvisState.SPEAKING:
            stream.read(OWW_CHUNK, exception_on_overflow=False)

