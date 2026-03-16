# main.py
import time
import config
import screen
import audio_out
import mic_in
import ai_logic
import wled_controller

def main():
    # 1. Boot sequence
    wled_controller.scan_for_devices()
    print(f"{config.COMPANION_NAME} running: wake word + continuous conversation (Ctrl+C to stop)")
    screen.draw_eyes("idle")

    proc = None
    try:
        proc = mic_in.start_arecord()

        while True:
            # 2. Listen for Wake Word
            frame = proc.stdout.read(config.FRAME_BYTES)
            if not frame or len(frame) < config.FRAME_BYTES:
                time.sleep(0.01)
                continue

            if not mic_in.detect_wake(frame):
                continue

            # 3. Wake Word Detected!
            mic_in.wake_rec.Reset()

            #screen.draw_eyes("listening")
            screen.draw_text("Listening...")

            ai_logic.start_new_chat()

            print(f"[Conversation started — will end after {config.CONVO_TIMEOUT_MS//1000}s of silence]")

            # 4. Continuous Conversation Loop
            while True:
                try:
                    text = mic_in.capture_utterance(proc)
                except mic_in.ConvoTimeout:
                    print("[Conversation ended — no follow-up detected]")
                    screen.draw_eyes("idle")
                    mic_in.wake_rec.Reset()
                    break

                if not text:
                    #screen.draw_eyes("listening")
                    screen.draw_text("Listening...")
                    continue

                print("You:", text)
                #screen.draw_eyes("thinking")
                screen.draw_text("Thinking...")

                # Talk to Gemini & Handle Tools
                reply = ai_logic.get_reply(text)
                print(f"{config.COMPANION_NAME}:", reply)

                # Output Audio
                if reply:
                    audio_out.speak(reply, proc)

                #screen.draw_eyes("listening")
                screen.draw_text("Listening...")
                
    except KeyboardInterrupt:
        pass
    finally:
        if proc:
            try:
                proc.terminate()
            except Exception:
                pass
        screen.clear()
        print("\nStopped.")

if __name__ == "__main__":
    main()