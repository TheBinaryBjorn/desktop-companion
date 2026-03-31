import pyaudio, time, queue
from state_manager import JarvisState

def thread_shutdown(audio, stream):
    stream.stop_stream()
    stream.close()
    audio.terminate()

def speaker_loop(brain, shutdown_event, playback_queue):
    audio = pyaudio.PyAudio()

    stream = audio.open(format=pyaudio.paInt16,
                        channels=1,
                        rate=22050,
                        output=True)
    print("[Speaker Thread]: Ready!")
    while not shutdown_event.is_set():
        try:
            audio_data = playback_queue.get(timeout=1.0)

            if audio_data == b'EOF':
                stream.stop_stream()
                stream.start_stream()
                time.sleep(0.3)
                brain.set_state(JarvisState.LISTENING)
            else:
                stream.write(audio_data)
        except queue.Empty:
            continue
    thread_shutdown(audio, stream)