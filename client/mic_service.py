import wave, time, pyaudio, webrtcvad, numpy as np
from collections import deque
from openwakeword.model import Model
from config import RATE, WAKEWORD, WAKEWORD_MODEL_PATH
from state_manager import JarvisState

OWW_CHUNK = 1280 # 1280 samples (80ms at 16kHz)
VAD_CHUNK = 320 # 320 samples (20ms at 16kHz)
NO_SPEECH_TIMEOUT = 5.0 # Seconds with no speech detected before returning to IDLE
POST_SPEECH_SILENCE = 1.0 # Seconds of silence after speech before treating utterance as complete
WAKEWORD_THRESHOLD = 0.5 # openWakeWord detection threshold
VAD_AGGRESSIVENESS = 2

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
    time.sleep(1.0) # wait for the sound to die down

def post_speech_timeout_passed(now, last_speech_at, post_speech_silence):
    return now - last_speech_at > post_speech_silence

def listening_state_timeout_passed(now, listening_entered_at, no_speech_timeout):
    return now - listening_entered_at > no_speech_timeout

def thread_shutdown(stream, audio):
    stream.stop_stream()
    stream.close()
    audio.terminate()

def mic_loop(brain, shutdown_event, startup_barrier, audio_queue, playback_queue):
    oww_model = Model([WAKEWORD_MODEL_PATH])
    vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
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
    speech_frame_count = 0
    preroll_buffer = deque(maxlen=5)

    print("[Mic Thread]: Ready!")
    startup_barrier.wait()
    print("[Mic Thread]: Running!")
    while not shutdown_event.is_set():
        current_state = brain.state

        # State entry setup
        if current_state != prev_state:
            if current_state == JarvisState.LISTENING:
                user_voice_detected = False
                listening_entered_at = time.time()
                last_speech_at = time.time()
                speech_frame_count = 0
                preroll_buffer.clear()
                stream.stop_stream()
                stream.start_stream()
                time.sleep(0.5)
            prev_state = current_state

        # IDLE: listen for wakeword
        if current_state == JarvisState.IDLE:
            data = stream.read(OWW_CHUNK, exception_on_overflow=False)
            now = time.time()
            if detect_wakeword(oww_model, data) and now - last_wakeword_time > 2.0:
                last_wakeword_time = now
                oww_model.reset()
                play_wakeword_feedback(playback_queue, beep_bytes)

        # LISTENING: record speech until silence
        elif current_state == JarvisState.LISTENING:

            # Read one OWW_CHUNK
            data = stream.read(OWW_CHUNK, exception_on_overflow=False)
            data_contains_speech = detect_speech(vad, data)
            # Detect speech in voice chunk
            if not user_voice_detected:
                preroll_buffer.append(data)
                if data_contains_speech:
                    speech_frame_count += 1
                    last_speech_at = time.time()
                    if speech_frame_count >= 3:
                        user_voice_detected = True
                        while len(preroll_buffer) > 0:
                            audio_queue.put(preroll_buffer.popleft())
                else:
                    speech_frame_count = 0
            # Only queue audio once speech has started 
            else:
                audio_queue.put(data)
                if data_contains_speech:
                    last_speech_at = time.time()

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
    thread_shutdown(stream, audio)

