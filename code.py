'''Adapted from the Adafruit_CircuitPython_ESP32SPI
library example esp32spi_simpletest.py:
https://github.com/adafruit/Adafruit_CircuitPython_ESP32SPI/
blob/master/examples/esp32spi_simpletest.py '''

import board
import busio
import time
import neopixel
from digitalio import DigitalInOut
import adafruit_requests as requests
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_esp32spi import adafruit_esp32spi

# needed for display
import adafruit_displayio_ssd1306
import displayio
import terminalio
import adafruit_mpr121
from adafruit_display_text import label

# Set up strip & blank it outled_pin = board.D7
num_leds = 20
led_pin = board.D7
strip = neopixel.NeoPixel(led_pin, num_leds, brightness=0.85, auto_write=False)
strip.fill((0,0,0))
strip.write()

# set up displays:
# For display through I2C (STEMMA QT)
displayio.release_displays()
#oled_reset = board.D9
i2c = board.I2C()
display_bus = displayio.I2CDisplay(i2c, device_address=0x3C)
# Create I2C bus <- don't need this and don't need the extra verbose definition. Created board.I2C above.
#i2c = busio.I2C(board.SCL, board.SDA)
WIDTH = 128
HEIGHT = 32  # Change to 64 if needed
BORDER = 0
display = adafruit_displayio_ssd1306.SSD1306(display_bus, width=WIDTH, height=HEIGHT)
# Set text, font, and color
text = " "
font = terminalio.FONT
color = 0xFFFFFF
# Create the text label
text_area = label.Label(font, text=text, color=color)
# Set the location
text_area.x = 0
text_area.y = 3
# Show it
display.show(text_area)
# to update text area after this with new text, just use a statement like this:
# text_area.text = "This is my new statement to display\nAnd this second line is amazing!"

# Needed for temperature sensor
import adafruit_mcp9808
#i2c = busio.I2C(board.SCL, board.SDA) #already used this
mcp = adafruit_mcp9808.MCP9808(i2c)

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

#  ESP32 pins
esp32_cs = DigitalInOut(board.CS1)
esp32_ready = DigitalInOut(board.ESP_BUSY)
esp32_reset = DigitalInOut(board.ESP_RESET)

#  uses the secondary SPI connected through the ESP32
spi = busio.SPI(board.SCK1, board.MOSI1, board.MISO1)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
requests.set_socket(socket, esp)

JSON_GET_URL = "https://worldtimeapi.org/api/timezone/America/New_York" #adding .txt removes JSON formatting
DATE_TIME = [0, 'datetime']

attempts = 3  # Number of attempts to retry each request
failure_count = 0
response = None

if esp.status == adafruit_esp32spi.WL_IDLE_STATUS:
    print("ESP32 found and in idle mode")
print("Firmware vers.", esp.firmware_version)
print("MAC addr:", [hex(i) for i in esp.MAC_address])

print("Connecting to AP...")
while not esp.is_connected:
    try:
        esp.connect_AP(secrets["ssid"], secrets["password"])
    except RuntimeError as e:
        print("could not connect to AP, retrying: ", e)
        continue
print("Connected to", str(esp.ssid, "utf-8"), "\tRSSI:", esp.rssi)
print("My IP address is", esp.pretty_ip(esp.ip_address))

# API Call
JSON_GET_URL = "http://worldtimeapi.org/api/timezone/America/New_York" #adding .txt removes JSON formatting
#DATE_TIME = [0, 'datetime']
UTC_OFFSET = [0, 'utc_offset']

print("Fetching JSON data from %s" % JSON_GET_URL)
while not response:
    try:
        response = requests.get(JSON_GET_URL)
        failure_count = 0
    except AssertionError as error:
        print("Request failed, retrying...\n", error)
        failure_count += 1
        if failure_count >= attempts:
            raise AssertionError(
                "Failed to resolve hostname, \
                                  please check your router's DNS configuration."
            ) from error
        continue
print("-" * 40)

print("JSON Response: ", response.json())
jsonDictionary = response.json()
utcOffsetHoursString = jsonDictionary["utc_offset"].split(":")[0]
utcOffsetMinutesString = jsonDictionary["utc_offset"].split(":")[1]
print("utcOffsetHoursString:", utcOffsetHoursString)
print("utcOffsetMinutesString:", utcOffsetMinutesString)
timeZoneOffset = (int(utcOffsetHoursString) * 60 * 60) + int(utcOffsetMinutesString * 60)  # get the offset amount in hours, splitting out anything after the colon

print("-" * 40)
response.close()
response = None


def formatTime(localTime):
    hour = localTime.tm_hour % 12
    if hour == 0:
        hour = 12

    am_pm = "AM"
    if localTime.tm_hour / 12 >= 1:
        am_pm = "PM"

    time_display = "{:d}:{:02d}:{:02d} {}".format(hour, localTime.tm_min, localTime.tm_sec, am_pm)
    return time_display

validResponse = False

print("Getting current time ..", end = '')
while not validResponse:
    try:
        timeFromESP = esp.get_time()
        validResponse = True
        print(".")
    except:
        print(".", end = '')

timeFromESP = esp.get_time()
print("Here is timeFromESP: ", timeFromESP)
localTime = time.localtime(timeFromESP[0] + (timeZoneOffset))
print("Here is localTime:", localTime)
print("Here is the formatted localTime:", formatTime(localTime))

# Gator Touch & LED Code
# Create MPR121 object (for Gator touch)
mpr121 = adafruit_mpr121.MPR121(i2c)
# Note you can optionally change the address of the device:
# mpr121 = adafruit_mpr121.MPR121(i2c, address=0x91)
# Loop forever testing each input and printing when they're touched.

def flashRed():
    strip.fill((255,0,0))
    strip.write()

flashRed()

while True:
    localTime = time.localtime(esp.get_time()[0] + (timeZoneOffset))
    printString = formatTime(localTime) + ", " + 'Temp: {} °F'.format(int(mcp.temperature * 9/5 + 32))
    touched = False
    for i in range(12): # Loop through the 12 gator pads
        if mpr121[i].value:
            printString = printString + "\n" + "GatorPad {} touched!".format(i)
            touched = True
            flashRed()
    if touched == False:
        strip.fill((0,0,0))
        strip.write()
    text_area.text = printString
    print(printString)
    time.sleep(0.1)


