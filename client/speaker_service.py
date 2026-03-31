import pyaudio, time
from state_manager import JarvisState

def speaker_loop(brain, playback_queue):
    audio = pyaudio.PyAudio()

    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=22050,
                        output=True)
    print("[Speaker Thread]: Ready!")
    while True:
        audio_data = playback_queue.get()

        if audio_data == b'EOF':
            stream.stop_stream()
            stream.start_stream()
            time.sleep(0.3)
            brain.set_state(JarvisState.LISTENING)
        else:
            stream.write(audio_data)
