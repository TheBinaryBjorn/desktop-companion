import subprocess
import config
import screen
import io

def play_file(audio_obj, mic_proc):
    """
    Plays a WAV file (from RAM or Disk) and drains the mic buffer.
    """
    screen.start_talking()

    try:
        if isinstance(audio_obj, io.BytesIO):
            # Play directly from RAM by piping to aplay
            # 'aplay -' tells it to read from stdin
            process = subprocess.Popen(
                ["aplay", "-q"],
                stdin=subprocess.PIPE
            )
            process.communicate(input=audio_obj.getvalue())
        else:
            # Fallback for physical files
            subprocess.run(["aplay", "-q", str(audio_obj)], check=False)
            
    except Exception as e:
        print(f"Playback error: {e}")
    finally:
        screen.stop_talking()

    # Drain stale mic audio accumulated during playback
    # This prevents Jarvis from "hearing" himself or old noise
    drain_frames = int(800 / config.FRAME_MS) # Increased to 800ms for safety
    for _ in range(drain_frames):
        try:
            mic_proc.stdout.read(config.FRAME_BYTES)
        except Exception:
            break

def speak(text: str, mic_proc):
    """Fallback TTS using espeak if needed."""
    screen.start_talking()
    subprocess.run(["espeak", text], check=False)
    screen.stop_talking()
    
    # Same draining logic
    drain_frames = int(500 / config.FRAME_MS)
    for _ in range(drain_frames):
        mic_proc.stdout.read(config.FRAME_BYTES)