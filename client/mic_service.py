import time, webrtcvad, numpy as np
from collections import deque
from openwakeword.model import Model
from config import RATE, WAKEWORD, WAKEWORD_MODEL_PATH
from state_manager import JarvisState
import sounddevice as sd
from scipy.signal import resample_poly

OWW_CHUNK           = 1280  # samples at 16kHz (80ms)
VAD_CHUNK           = 320   # samples at 16kHz (20ms)
NO_SPEECH_TIMEOUT   = 5.0
POST_SPEECH_SILENCE = 1.0
WAKEWORD_THRESHOLD  = 0.7
WAKEWORD_COOLDOWN   = 7.0
VAD_AGGRESSIVENESS  = 2

# INMP441 / hardware constraints
HW_RATE     = 48000
HW_CHANNELS = 2
HW_DTYPE    = "int32"
# How many 48kHz frames = one 16kHz OWW_CHUNK
HW_CHUNK    = OWW_CHUNK * (HW_RATE // RATE)  # 1280 * 3 = 3840


def find_input_device() -> int | None:
    for i, dev in enumerate(sd.query_devices()):
        if "googlevoice" in dev["name"].lower() and dev["max_input_channels"] > 0:
            return i
    return None


def read_chunk(stream: sd.RawInputStream) -> bytes:
    raw, _ = stream.read(HW_CHUNK)
    arr32  = np.frombuffer(raw, dtype=np.int32)
    left   = arr32[0::2]
    left16 = (left >> 9).astype(np.int16)
    down   = resample_poly(left16, 1, 3)
    result = down.astype(np.int16).tobytes()
    return result


def detect_wakeword(model: Model, data: bytes) -> bool:
    audio_array = np.frombuffer(data, dtype=np.int16)
    prediction  = model.predict(audio_array)
    score = prediction[WAKEWORD]
    if score > 0.3:  # low threshold just to see scores
        print(f"[Wakeword score]: {score:.3f}")
    return score > WAKEWORD_THRESHOLD


def detect_speech(vad: webrtcvad.Vad, data: bytes) -> bool:
    n_windows = len(data) // (VAD_CHUNK * 2)
    for i in range(n_windows):
        window = data[i * VAD_CHUNK * 2 : (i + 1) * VAD_CHUNK * 2]
        if vad.is_speech(window, RATE):
            return True
    return False


def load_feedback_sound_bytes() -> bytes:
    import wave
    with wave.open("sounds/wakeword_feedback_sound.wav", "rb") as wf:
        return wf.readframes(wf.getnframes())


def play_wakeword_feedback(playback_queue, sound_bytes: bytes):
    playback_queue.put(sound_bytes)
    playback_queue.put(b"EOF")
    time.sleep(1.0)


def post_speech_timeout_passed(now, last_speech_at, silence):
    return now - last_speech_at > silence


def listening_state_timeout_passed(now, entered_at, timeout):
    return now - entered_at > timeout


def wakeword_cooldown_passed(now, last_ww, cooldown):
    return now - last_ww > cooldown


def thread_shutdown(stream: sd.RawInputStream):
    stream.stop()
    stream.close()


def mic_loop(brain, shutdown_event, startup_barrier, audio_queue, playback_queue):
    oww_model = Model([WAKEWORD_MODEL_PATH])
    vad       = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    device = find_input_device()
    if device is not None:
        print(f"[Mic Thread]: Using device {device}: {sd.query_devices(device)['name']}")
    else:
        print("[Mic Thread]: googlevoicehat not found — using system default.")

    stream = sd.RawInputStream(
        samplerate = HW_RATE,
        blocksize  = HW_CHUNK,
        device     = device,
        channels   = HW_CHANNELS,
        dtype      = HW_DTYPE,
    )
    stream.start()
    beep_bytes = load_feedback_sound_bytes()

    prev_state           = None
    user_voice_detected  = False
    listening_entered_at = 0.0
    last_speech_at       = 0.0
    last_wakeword_time   = 0.0
    speech_frame_count   = 0
    preroll_buffer       = deque(maxlen=5)

    print("[Mic Thread]: Ready!")
    startup_barrier.wait()
    print("[Mic Thread]: Running!")

    while not shutdown_event.is_set():
        current_state = brain.state

        if current_state != prev_state:
            if current_state == JarvisState.LISTENING:
                user_voice_detected  = False
                listening_entered_at = time.time()
                last_speech_at       = time.time()
                speech_frame_count   = 0
                preroll_buffer.clear()
                stream.stop()
                stream.start()
                time.sleep(0.5)
            prev_state = current_state

        # IDLE ────────────────────────────────────────────────────────────────
        if current_state == JarvisState.IDLE:
            data = read_chunk(stream)
            now  = time.time()
            if detect_wakeword(oww_model, data) and wakeword_cooldown_passed(now, last_wakeword_time, WAKEWORD_COOLDOWN):
                last_wakeword_time = now
                oww_model.reset()
                play_wakeword_feedback(playback_queue, beep_bytes)

        # LISTENING ───────────────────────────────────────────────────────────
        elif current_state == JarvisState.LISTENING:
            data                 = read_chunk(stream)
            data_contains_speech = detect_speech(vad, data)

            if not user_voice_detected:
                preroll_buffer.append(data)
                if data_contains_speech:
                    speech_frame_count += 1
                    last_speech_at = time.time()
                    if speech_frame_count >= 3:
                        user_voice_detected = True
                        while preroll_buffer:
                            audio_queue.put(preroll_buffer.popleft())
                else:
                    speech_frame_count = 0
            else:
                audio_queue.put(data)
                if data_contains_speech:
                    last_speech_at = time.time()

            now = time.time()
            if user_voice_detected and post_speech_timeout_passed(now, last_speech_at, POST_SPEECH_SILENCE):
                audio_queue.put(b"EOF")
                brain.set_state(JarvisState.THINKING)
            elif not user_voice_detected and listening_state_timeout_passed(now, listening_entered_at, NO_SPEECH_TIMEOUT):
                brain.set_state(JarvisState.IDLE)

        # SPEAKING ────────────────────────────────────────────────────────────
        elif current_state == JarvisState.SPEAKING:
            stream.read(HW_CHUNK)  # flush — discard playback bleed

    thread_shutdown(stream)