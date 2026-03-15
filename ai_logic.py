# ai_logic.py
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types as genai_types
import config
import wled_controller, music_controller

load_dotenv()
gclient = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
active_chat = None

def start_new_chat():
    """Initializes a fresh chat session with the discovered devices loaded."""
    global active_chat
    available_lights = ", ".join(wled_controller.discovered_wleds.keys())
    
    system_instruction = (
        f"You are a cute desk companion named {config.COMPANION_NAME}. "
        f"You have the ability to control the following WLED smart lights on the network: {available_lights}. "
        f"Reply in 1–2 short sentences. "
        f"Reply with plain text only — no markdown, no asterisks, no formatting of any kind."
    )
    
    active_chat = gclient.chats.create(
        model="gemini-2.5-flash-lite",
        config=genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=[wled_controller.control_wled, music_controller.play_spotify] 
        )
    )

def get_reply(user_text: str) -> str:
    try:
        r = active_chat.send_message(user_text)
        return (r.text or "").strip()
    except Exception as e:
        print(f"[Gemini error: {e}]")
        return "Sorry, something went wrong."