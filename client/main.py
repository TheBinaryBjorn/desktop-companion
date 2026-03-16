import os, time, config, screen, audio_out, mic_in, ai_logic, wled_controller

def main():
    # 1. Hardware Initialization
    wled_controller.scan_for_devices()
    print(f"{config.COMPANION_NAME} (Pi Satellite) is active.")
    screen.draw_eyes("idle")

    proc = None
    try:
        # Start the background mic listener
        proc = mic_in.start_arecord()
        
        while True:
            # 2. Wait for Wake Word
            frame = proc.stdout.read(config.FRAME_BYTES)
            if not frame or not mic_in.detect_wake(frame):
                continue

            # 3. Trigger Active Listening
            mic_in.wake_rec.Reset()
            screen.draw_text("Listening...")
            ai_logic.start_new_chat()

            # Continuous Conversation Loop
            while True:
                try:
                    # Records until silence and returns a local .wav path
                    local_wav = mic_in.capture_utterance(proc)
                except mic_in.ConvoTimeout:
                    print("Conversation timed out.")
                    screen.draw_eyes("idle")
                    break

                if not local_wav: continue
                
                screen.draw_text("Thinking...")

                # --- TELEPORT TO VIVOBOOK ---
                user_txt, ai_txt, reply_wav = ai_logic.process_voice_remote(local_wav)

                print(f"You: {user_txt}")
                print(f"Jarvis: {ai_txt}")

                # 4. Play the Piper response on Pi speakers
                if reply_wav and os.path.exists(reply_wav):
                    audio_out.play_file(reply_wav)

                screen.draw_text("Listening...")

    except KeyboardInterrupt:
        print("\nStopping Jarvis...")
    finally:
        if proc: proc.terminate()
        screen.clear()

if __name__ == "__main__":
    main()