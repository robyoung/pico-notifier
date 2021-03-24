import board
import busio
import supervisor
import time
import usb_hid

from adafruit_bus_device.i2c_device import I2CDevice
import adafruit_dotstar
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode
from digitalio import DigitalInOut, Direction, Pull

import notifier

# Pull CS pin low to enable level shifter
cs = DigitalInOut(board.GP17)
cs.direction = Direction.OUTPUT
cs.value = 0

# Set up APA102 pixels
num_pixels = 16
pixels = adafruit_dotstar.DotStar(
    board.GP18, board.GP19, num_pixels, brightness=0.1, auto_write=True
)

# Set up I2C for IO expander (addr: 0x20)
i2c = busio.I2C(board.GP5, board.GP4)
device = I2CDevice(i2c, 0x20)

# Set up the keyboard
kbd = Keyboard(usb_hid.devices)
layout = KeyboardLayoutUS(kbd)
keysets = {}

# Read button states from the I2C IO expander on the keypad
def read_button_states(x, y):
    pressed = [0] * 16
    with device:
        # Read from IO expander, 2 bytes (8 bits) correspond to the 16 buttons
        device.write(bytes([0x0]))
        result = bytearray(2)
        device.readinto(result)
        b = result[0] | result[1] << 8

        # Loop through the buttons
        for i in range(x, y):
            if not (1 << i) & b:
                pressed[i] = 1
            else:
                pressed[i] = 0
    return pressed


while True:
    notifier.handle_command(supervisor.runtime, pixels, keysets, Keycode)

    pressed = read_button_states(0, 16)
    for button, keyset in keysets.items():
        if pressed[button] == 1:
            print("LOG: execute keyset for button {}".format(button))
            notifier.execute_keyset(kbd, layout, time, pixels, keyset)

    time.sleep(0.1)
