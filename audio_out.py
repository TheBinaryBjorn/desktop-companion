# audio_out.py
import subprocess
import config
import screen

def speak(text: str, mic_proc):
    """Triggers the screen animation, speaks the text, and flushes the mic buffer."""
    screen.start_talking()
    
    # Run TTS
    subprocess.run(["espeak", text], check=False)
    
    screen.stop_talking()

    # Drain stale mic audio accumulated during TTS
    drain_frames = int(500 / config.FRAME_MS)
    for _ in range(drain_frames):
        mic_proc.stdout.read(config.FRAME_BYTES)