import threading, queue, time
from state_manager import StateManager
from mic_service import mic_loop
from screen_service import screen_loop
from network_service import network_loop
from speaker_service import speaker_loop


def main():
    # Start in IDLE
    brain = StateManager()

    # Audio Queue for mic thread and network thread to communicate
    audio_queue = queue.Queue()
    playback_queue = queue.Queue()

    # Define event
    shutdown_event = threading.Event()

    # Define the threads
    t_screen = threading.Thread(target=screen_loop, args=(brain, shutdown_event), daemon=True)
    t_mic = threading.Thread(target=mic_loop, args=(brain, shutdown_event, audio_queue, playback_queue), daemon=True)
    t_net = threading.Thread(target=network_loop, args=(brain, shutdown_event, audio_queue, playback_queue), daemon=True)
    t_speaker = threading.Thread(target=speaker_loop, args=(brain, shutdown_event, playback_queue), daemon=True)
    
    threads = [t_screen, t_mic, t_net, t_speaker]
    
    # Start the threads
    for thread in threads:
        thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Jarvis...")
        shutdown_event.set()
        for thread in reversed(threads):
            thread.join(timeout=2.0)

if __name__ == "__main__":
    main()
