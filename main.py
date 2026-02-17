import time
import board
import busio
from PIL import Image, ImageDraw
import adafruit_ssd1306

DISPLAY_WIDTH = 128
DISPLAY_HEIGHT = 64

i2c = busio.I2C(board.SCL, board.SDA)
display = adafruit_ssd1306.SSD1306_I2C(DISPLAY_WIDTH, DISPLAY_HEIGHT, i2c)

def draw_eyes(blink=False):
	image = Image.new("1", (DISPLAY_WIDTH, DISPLAY_HEIGHT))
	draw = ImageDraw.Draw(image)
	if blink:
		draw.rectangle((20, 30, 50, 34), fill=255)
		draw.rectangle((78, 30, 108, 34), fill=255)
	else:
		draw.ellipse((20, 20, 50, 50), fill=255)
		draw.ellipse((78, 20, 108, 50), fill=255)

	display.image(image)
	display.show()

while True:
	draw_eyes(False)
	time.sleep(3)
	draw_eyes(True)
	time.sleep(0.2)
