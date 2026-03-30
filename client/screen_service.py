# screen.py
import time
import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw
from datetime import datetime
import config
from state_manager import JarvisState

def create_display():
    i2c = busio.I2C(board.SCL, board.SDA)
    return adafruit_ssd1306.SSD1306_I2C(config.W, config.H, i2c)

def create_canvas():
    image = Image.new('1', (config.W, config.H))
    return image, ImageDraw.Draw(image)

def clear_buffer(draw):
    draw.rectangle((0, 0, config.W, config.H), fill=0)

def display_clock(display, image, draw):
    clear_buffer(draw)
    current_time = datetime.now().strftime("%H:%M")
    draw.text((32, 20), current_time, fill=255)
    push_frame(display, image)

def push_frame(display, image):
    display.image(image)
    display.show()

def display_text(display, image, draw, text):
    clear_buffer(draw)
    draw.text((config.W // 2, config.H // 2), text, anchor="mm", fill=255)
    push_frame(display, image)

def display_listening(display, image, draw):
    display_text(display, image, draw, "[Listening]")

def display_thinking(display, image, draw):
    display_text(display, image, draw, "[Thinking]")

def display_speaking(display, image, draw):
    display_text(display, image, draw, "[Speaking]")

def display_error(display, image, draw):
    display_text(display, image, draw, "[Error]")
    
def screen_loop(brain):
    display = create_display()
    image, draw = create_canvas()
    while True:
        current_state = brain.state
        if current_state == JarvisState.IDLE:
            display_clock(display, image, draw)
            time.sleep(0.05) 
        elif current_state == JarvisState.LISTENING:
            display_listening(display, image, draw)
            time.sleep(0.05)
        elif current_state == JarvisState.THINKING:
            display_thinking(display, image, draw)
            time.sleep(0.05) 
        elif current_state == JarvisState.SPEAKING:
            display_speaking(display, image, draw)
            time.sleep(0.05)
        else:
            display_error(display, image, draw)
            time.sleep(1)

"""
_speaking = False
_anim_thread = None



def _draw_frame(img):
    display.image(img)
    display.show()

def _make_eyes(d, state="idle"):
    if state == "idle":
        d.ellipse((20, 20, 50, 50), fill=255)
        d.ellipse((78, 20, 108, 50), fill=255)
    elif state == "listening":
        d.ellipse((15, 15, 55, 55), fill=255)
        d.ellipse((73, 15, 113, 55), fill=255)
    elif state == "thinking":
        d.ellipse((20, 25, 50, 45), fill=255)
        d.ellipse((78, 25, 108, 45), fill=255)
    elif state == "blink":
        d.rectangle((20, 30, 50, 34), fill=255)
        d.rectangle((78, 30, 108, 34), fill=255)

def _rounded_rect(d, x0, y0, x1, y1, radius, fill=255):
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    d.rectangle((x0 + r, y0, x1 - r, y1), fill=fill)
    d.rectangle((x0, y0 + r, x1, y1 - r), fill=fill)
    d.ellipse((x0, y0, x0 + 2*r, y0 + 2*r), fill=fill)
    d.ellipse((x1 - 2*r, y0, x1, y0 + 2*r), fill=fill)
    d.ellipse((x0, y1 - 2*r, x0 + 2*r, y1), fill=fill)
    d.ellipse((x1 - 2*r, y1 - 2*r, x1, y1), fill=fill)

def _draw_mouth(d, amount):
    mx, my, half_w = 64, 57, 20
    min_h, max_h, radius = 2, 9, 3

    h = int(min_h + amount * (max_h - min_h))
    x0, y0 = mx - half_w, my - h
    x1, y1 = mx + half_w, my + h

    if h <= min_h:
        d.rectangle((x0, my - 1, x1, my + 1), fill=255)
    else:
        _rounded_rect(d, x0, y0, x1, y1, radius)

def draw_eyes(state="idle"):
    img = Image.new("1", (config.W, config.H))
    d = ImageDraw.Draw(img)
    _make_eyes(d, state)
    _draw_frame(img)

def _animate_mouth():
    pattern = [0.0, 1.0, 0.0, 1.0, 0.0, 0.8, 0.0, 1.0, 0.0, 0.6, 0.0, 1.0]
    i = 0
    while _speaking:
        img = Image.new("1", (config.W, config.H))
        d = ImageDraw.Draw(img)
        _make_eyes(d, "idle")
        _draw_mouth(d, pattern[i % len(pattern)])
        _draw_frame(img)
        i += 1
        time.sleep(config.MOUTH_BEAT_SEC)
    draw_eyes("idle")

def draw_text(text, size=12, x=0, y=0, clear_first=True):
    img = Image.new("1",(config.W, config.H))
    d = ImageDraw.Draw(img)
    # Optional, add font later
    d.text((x, y), text, fill=255)
    _draw_frame(img)

def start_talking():
    """
"""
    global _speaking, _anim_thread
    _speaking = True
    _anim_thread = threading.Thread(target=_animate_mouth, daemon=True)
    _anim_thread.start()
    """
"""
    draw_text("Talking...")

def stop_talking():
    global _speaking, _anim_thread
    _speaking = False
    if _anim_thread:
        _anim_thread.join(timeout=0.5)

# Clear the screen on import just to be safe
clear()
"""