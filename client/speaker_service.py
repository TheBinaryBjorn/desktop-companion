import sounddevice as sd
import numpy as np
import time, queue
from scipy.signal import resample_poly
from state_manager import JarvisState

PIPER_RATE   = 22050   # what Piper outputs
OUTPUT_RATE  = 48000   # what MAX98357A accepts (or 44100)
OUTPUT_CHANNELS = 1
OUTPUT_DTYPE = "int16"
BLOCKSIZE    = 2048    # frames per write — tune if you get underruns


def find_max98357_device() -> int | None:
    """Find the MAX98357A by common ALSA/I2S name fragments."""
    for i, dev in enumerate(sd.query_devices()):
        name = dev["name"].lower()
        if any(k in name for k in ("max98357", "i2s", "sndrpii2s", "hifiberry", "seeed")):
            if dev["max_output_channels"] > 0:
                return i
    return None


def upsample_22k_to_48k(pcm16_bytes: bytes) -> bytes:
    """Resample int16 PCM from Piper's 22050 Hz to 48000 Hz."""
    audio = np.frombuffer(pcm16_bytes, dtype=np.int16).astype(np.float32)
    # 22050 → 48000: multiply by 160/73 (exact rational)
    resampled = resample_poly(audio, 160, 73)
    return np.clip(resampled, -32768, 32767).astype(np.int16).tobytes()


def thread_shutdown(stream: sd.OutputStream):
    stream.stop()
    stream.close()


def speaker_loop(brain, shutdown_event, startup_barrier, playback_queue):
    device = find_max98357_device()
    if device is not None:
        print(f"[Speaker Thread]: Using device {device}: {sd.query_devices(device)['name']}")
    else:
        print("[Speaker Thread]: MAX98357A not found by name — using system default output.")

    stream = sd.RawOutputStream(
        samplerate = OUTPUT_RATE,
        blocksize  = BLOCKSIZE,
        device     = device,
        channels   = OUTPUT_CHANNELS,
        dtype      = OUTPUT_DTYPE,
    )
    stream.start()

    # Accumulate resampled bytes and write in BLOCKSIZE-aligned chunks
    write_buffer = bytearray()
    block_bytes  = BLOCKSIZE * 2  # 2 bytes per int16 sample

    def flush_buffer():
        nonlocal write_buffer
        while len(write_buffer) >= block_bytes:
            block = bytes(write_buffer[:block_bytes])
            write_buffer = write_buffer[block_bytes:]
            stream.write(block)

    print("[Speaker Thread]: Ready!")
    startup_barrier.wait()
    print("[Speaker Thread]: Running!")

    while not shutdown_event.is_set():
        try:
            audio_data = playback_queue.get(timeout=1.0)

            if audio_data == b"EOF":
                # Flush any remaining audio before signalling done
                if write_buffer:
                    # Pad to block boundary with silence
                    padding = block_bytes - (len(write_buffer) % block_bytes)
                    write_buffer.extend(b"\x00" * padding)
                    flush_buffer()
                    write_buffer.clear()

                time.sleep(0.3)
                brain.set_state(JarvisState.LISTENING)

            else:
                upsampled = upsample_22k_to_48k(audio_data)
                write_buffer.extend(upsampled)
                flush_buffer()

        except queue.Empty:
            continue

    thread_shutdown(stream)