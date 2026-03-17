import os, time, config, screen, mic_in, ai_logic
import io

def main():
    print(f"{config.COMPANION_NAME} (Pi Satellite) is active.")
    screen.draw_eyes("idle")

    proc = None
    try:
        proc = mic_in.start_arecord()
        
        while True:
            frame = proc.stdout.read(config.FRAME_BYTES)
            if not frame or not mic_in.detect_wake(frame):
                continue

            mic_in.wake_rec.Reset()
            screen.draw_text("Listening...")

            while True:
                try:
                    local_wav_obj = mic_in.capture_utterance(proc)
                except mic_in.ConvoTimeout:
                    print("Conversation timed out.")
                    screen.draw_eyes("idle")
                    break

                if not local_wav_obj:
                    continue

                screen.draw_text("Thinking...")

                # Streams audio and plays it directly — no return value needed
                user_txt, _, _ = ai_logic.process_voice_remote(local_wav_obj)

                print(f"You: {user_txt}")
                screen.draw_text("Listening...")

    except KeyboardInterrupt:
        print("\nStopping Jarvis...")
    finally:
        if proc:
            proc.terminate()
        screen.clear()

if __name__ == "__main__":
    main()