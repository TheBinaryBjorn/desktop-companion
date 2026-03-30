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
    print("[Screen Thread]: Ready!")
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