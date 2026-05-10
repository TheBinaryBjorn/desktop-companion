import wave, time, webrtcvad, numpy as np
import sounddevice as sd
from collections import deque
from openwakeword.model import Model
from config import RATE, WAKEWORD, WAKEWORD_MODEL_PATH
from state_manager import JarvisState

OWW_CHUNK        = 1280   # samples per chunk (80ms at 16kHz)
VAD_CHUNK        = 320    # samples per VAD window (20ms at 16kHz)
NO_SPEECH_TIMEOUT   = 5.0
POST_SPEECH_SILENCE = 1.0
WAKEWORD_THRESHOLD  = 0.7
WAKEWORD_COOLDOWN   = 7.0
VAD_AGGRESSIVENESS  = 2

# ICS43434 specifics
ICS_SAMPLE_RATE  = 48000  # native rate of the ICS43434
ICS_CHANNELS     = 2      # I2S always delivers stereo frame; we take left channel
ICS_DTYPE        = "int32"
ICS_DEVICE       = None   # set to device index/name, or None for system default

def find_ics_device() -> int | None:
    """Return the sounddevice index whose name contains 'ICS' or common Pi I2S names."""
    for i, dev in enumerate(sd.query_devices()):
        name = dev["name"].lower()
        if any(k in name for k in ("ics43434", "i2s", "sndrpii2s", "seeed")):
            return i
    return None  # caller falls back to system default


def read_chunk_int32(stream_iter, n_samples: int) -> np.ndarray:
    """
    Pull n_samples stereo int32 frames from the RawInputStream iterator,
    keep only the LEFT channel, down-shift 24-bit data into int16 range.
    Returns int16 numpy array of length n_samples.
    """
    # sounddevice gives us raw bytes; we asked for int32
    raw_samples = n_samples * ICS_CHANNELS  # total int32 values
    raw_bytes   = raw_samples * 4           # 4 bytes per int32
    buf = bytearray()
    while len(buf) < raw_bytes:
        chunk, _ = next(stream_iter)
        buf.extend(bytes(chunk))
    arr32 = np.frombuffer(buf[:raw_bytes], dtype=np.int32)
    # stereo de-interleave: take every other sample (left channel)
    left = arr32[0::2]
    # ICS43434 data is 24-bit left-justified in 32-bit word → shift right 8 bits
    # then scale into int16
    left16 = (left >> 16).astype(np.int16)
    return left16


def resample_to_16k(audio16: np.ndarray, orig_rate: int = ICS_SAMPLE_RATE) -> np.ndarray:
    """Simple decimation for 48000→16000 (factor 3). Use scipy for other ratios."""
    if orig_rate == RATE:
        return audio16
    if orig_rate % RATE != 0:
        from scipy.signal import resample_poly
        g = np.gcd(RATE, orig_rate)
        return resample_poly(audio16, RATE // g, orig_rate // g).astype(np.int16)
    factor = orig_rate // RATE  # = 3 for 48k→16k
    return audio16[::factor]


def pcm16_bytes(audio16: np.ndarray) -> bytes:
    return audio16.tobytes()


# ── unchanged helpers ────────────────────────────────────────────────────────

def detect_wakeword(model: Model, data: bytes) -> bool:
    audio_array = np.frombuffer(data, dtype=np.int16)
    prediction  = model.predict(audio_array)
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
    time.sleep(1.0)

def post_speech_timeout_passed(now, last_speech_at, silence):
    return now - last_speech_at > silence

def listening_state_timeout_passed(now, entered_at, timeout):
    return now - entered_at > timeout

def wakeword_cooldown_passed(now, last_ww, cooldown):
    return now - last_ww > cooldown

def thread_shutdown(stream):
    stream.stop()
    stream.close()


# ── main loop ────────────────────────────────────────────────────────────────

def mic_loop(brain, shutdown_event, startup_barrier, audio_queue, playback_queue):
    oww_model = Model([WAKEWORD_MODEL_PATH])
    vad       = webrtcvad.Vad(VAD_AGGRESSIVENESS)

    device = find_ics_device() or ICS_DEVICE
    if device is not None:
        print(f"[Mic Thread]: Using device {device}: {sd.query_devices(device)['name']}")
    else:
        print("[Mic Thread]: ICS43434 not found by name — using system default input.")

    # How many 48 kHz frames equal one OWW_CHUNK at 16 kHz?
    native_chunk = OWW_CHUNK * (ICS_SAMPLE_RATE // RATE)  # 1280 * 3 = 3840

    stream = sd.RawInputStream(
        samplerate = ICS_SAMPLE_RATE,
        blocksize  = native_chunk,
        device     = device,
        channels   = ICS_CHANNELS,
        dtype      = ICS_DTYPE,
    )
    stream.start()
    stream_iter = iter(lambda: stream.read(native_chunk), None)
    beep_bytes  = load_feedback_sound_bytes()

    def read_oww_chunk() -> bytes:
        """Read one OWW_CHUNK worth of int16 16 kHz PCM, as bytes."""
        raw16 = read_chunk_int32(stream_iter, native_chunk)
        down  = resample_to_16k(raw16)
        return pcm16_bytes(down)

    # ── bookkeeping ──────────────────────────────────────────────────────────
    prev_state          = None
    user_voice_detected = False
    listening_entered_at = 0.0
    last_speech_at      = 0.0
    last_wakeword_time  = 0.0
    speech_frame_count  = 0
    preroll_buffer      = deque(maxlen=5)

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
            data = read_oww_chunk()
            now  = time.time()
            if detect_wakeword(oww_model, data) and wakeword_cooldown_passed(now, last_wakeword_time, WAKEWORD_COOLDOWN):
                last_wakeword_time = now
                oww_model.reset()
                play_wakeword_feedback(playback_queue, beep_bytes)

        # LISTENING ───────────────────────────────────────────────────────────
        elif current_state == JarvisState.LISTENING:
            data               = read_oww_chunk()
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
            stream.read(native_chunk)   # flush — discard Jarvis's own voice

    thread_shutdown(stream)