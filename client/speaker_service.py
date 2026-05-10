import sounddevice as sd
import numpy as np
import time, queue
from scipy.signal import resample_poly
from state_manager import JarvisState

PIPER_RATE      = 22050
OUTPUT_RATE     = 48000
OUTPUT_CHANNELS = 2        # driver requires stereo
OUTPUT_DTYPE    = "int32"  # driver requires S32_LE
BLOCKSIZE       = 2048


def find_output_device() -> int | None:
    for i, dev in enumerate(sd.query_devices()):
        if "googlevoice" in dev["name"].lower() and dev["max_output_channels"] > 0:
            return i
    return None


def upsample_to_48k(pcm16_bytes: bytes) -> np.ndarray:
    """22050 Hz int16 mono → 48000 Hz int32 stereo (what the driver needs)."""
    audio = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32)

    # Resample 22050 → 48000
    resampled = resample_poly(audio, 320, 147).astype(np.float32)

    # Scale int16 range → int32 range
    resampled_32 = (resampled * (2**15)).astype(np.int32)

    # Mono → stereo (duplicate channel)
    stereo = np.column_stack((resampled_32, resampled_32))

    return stereo  # shape: (n_samples, 2)


def thread_shutdown(stream: sd.RawOutputStream):
    stream.stop()
    stream.close()


def speaker_loop(brain, shutdown_event, startup_barrier, playback_queue):
    device = find_output_device()
    if device is not None:
        print(f"[Speaker Thread]: Using device {device}: {sd.query_devices(device)['name']}")
    else:
        print("[Speaker Thread]: googlevoicehat not found — using system default.")

    stream = sd.OutputStream(
        samplerate = OUTPUT_RATE,
        blocksize  = BLOCKSIZE,
        device     = device,
        channels   = OUTPUT_CHANNELS,
        dtype      = OUTPUT_DTYPE,
    )
    stream.start()

    print("[Speaker Thread]: Ready!")
    startup_barrier.wait()
    print("[Speaker Thread]: Running!")

    while not shutdown_event.is_set():
        try:
            audio_data = playback_queue.get(timeout=1.0)

            if audio_data == b"EOF":
                time.sleep(0.3)
                brain.set_state(JarvisState.LISTENING)

            else:
                stereo32 = upsample_to_48k(audio_data)
                stream.write(stereo32)

        except queue.Empty:
            continue

    thread_shutdown(stream)