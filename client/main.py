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

    # Define the threads
    t_screen = threading.Thread(target=screen_loop, args=(brain,), daemon=True)
    t_mic = threading.Thread(target=mic_loop, args=(brain, audio_queue, playback_queue), daemon=True)
    t_net = threading.Thread(target=network_loop, args=(brain, audio_queue, playback_queue), daemon=True)
    t_speaker = threading.Thread(target=speaker_loop, args=(brain, playback_queue), daemon=True)

    # Start the threads
    t_screen.start()
    t_mic.start()
    t_net.start()
    t_speaker.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Jarvis...")

if __name__ == "__main__":
    main()
