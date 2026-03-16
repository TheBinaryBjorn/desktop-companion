import os, time, config, screen, audio_out, mic_in, ai_logic, wled_controller
import io # Added for type checking

def main():
    # 1. Hardware Initialization
    print(f"{config.COMPANION_NAME} (Pi Satellite) is active.")
    screen.draw_eyes("idle")

    proc = None
    try:
        proc = mic_in.start_arecord()
        
        while True:
            # 2. Wait for Wake Word
            frame = proc.stdout.read(config.FRAME_BYTES)
            if not frame or not mic_in.detect_wake(frame):
                continue

            # 3. Trigger Active Listening
            mic_in.wake_rec.Reset()
            screen.draw_text("Listening...")
            #ai_logic.start_new_chat()

            while True:
                try:
                    # NOW RETURNS: io.BytesIO object (RAM)
                    local_wav_obj = mic_in.capture_utterance(proc)
                except mic_in.ConvoTimeout:
                    print("Conversation timed out.")
                    screen.draw_eyes("idle")
                    break

                if not local_wav_obj: continue
                
                screen.draw_text("Thinking...")

                # --- TELEPORT TO VIVOBOOK ---
                # We pass the memory object, and it returns a memory object (reply_wav_obj)
                user_txt, ai_txt, reply_wav_obj = ai_logic.process_voice_remote(local_wav_obj)

                print(f"You: {user_txt}")
                print(f"Jarvis: {ai_txt}")

                # 4. Play the Piper response
                # We check if it's a BytesIO object instead of os.path.exists
                if isinstance(reply_wav_obj, io.BytesIO):
                    # You'll need to update audio_out.play_file to handle BytesIO
                    audio_out.play_file(reply_wav_obj)

                screen.draw_text("Listening...")

    except KeyboardInterrupt:
        print("\nStopping Jarvis...")
    finally:
        if proc: proc.terminate()
        screen.clear()

if __name__ == "__main__":
    main()