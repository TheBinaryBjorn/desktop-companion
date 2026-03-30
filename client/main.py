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
    t_mic = threading.Thread(target=mic_loop, args=(brain, audio_queue), daemon=True)
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

"""
import os, time, config, client.screen_service as screen_service, client.mic_service as mic_service, client.network_service as network_service
import io

def main():
    print(f"{config.COMPANION_NAME} (Pi Satellite) is active.")
    screen_service.draw_eyes("idle")

    proc = None
    try:
        proc = mic_service.start_arecord()
        
        while True:
            frame = proc.stdout.read(config.FRAME_BYTES)
            if not frame or not mic_service.detect_wake(frame):
                continue

            mic_service.wake_rec.Reset()
            screen_service.draw_text("Listening...")

            while True:
                try:
                    local_wav_obj = mic_service.capture_utterance(proc)
                except mic_service.ConvoTimeout:
                    print("Conversation timed out.")
                    screen_service.draw_eyes("idle")
                    break

                if not local_wav_obj:
                    continue

                screen_service.draw_text("Thinking...")

                # Streams audio and plays it directly — no return value needed
                user_txt, _, _ = network_service.process_voice_remote(local_wav_obj)

                print(f"You: {user_txt}")
                screen_service.draw_text("Listening...")

    except KeyboardInterrupt:
        print("\nStopping Jarvis...")
    finally:
        if proc:
            proc.terminate()
        screen_service.clear()

if __name__ == "__main__":
    main()
"""