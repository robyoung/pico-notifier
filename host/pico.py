import asyncio
from contextlib import contextmanager
import time
from typing import Tuple, Optional, List, Union
from binascii import hexlify

import serial

from . import shell


Colour = Tuple[int, int, int]
Buttons = Union[int, Tuple[int, ...]]

OFF = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

YELLOW = (255, 255, 0)
ORANGE = (255, 100, 0)
MAGENTA = (255, 0, 255)
CYAN = (0, 255, 255)


class Key:
    @staticmethod
    def key(*keys: str) -> str:
        return 'k{}'.format('|'.join(keys))

    @staticmethod
    def sleep(t: float) -> str:
        return f's{t}'

    @staticmethod
    def write(s: str) -> str:
        hexdata = hexlify(s.encode('utf8')).decode('utf8')
        return f'w{hexdata}'

    @staticmethod
    def leds(colour: Colour, brightness: Optional[float] = None) -> str:
        return f'l{_encode_colour(colour, brightness)}'


@contextmanager
def client():
    with serial.Serial('/dev/ttyACM0', baudrate=115200, timeout=0.05) as ser:
        yield Client(ser)


class Client:
    def __init__(self, ser: serial.Serial):
        self.ser = ser

    def read_line(self) -> str:
        return self.ser.readline().decode('utf8').strip()

    def read_until_not_log(self):
        while True:
            line = self.read_line()
            if line.startswith('LOG'):
                print(f'{shell.LOG}{line}{shell.ENDC}')
            else:
                return line

    def read_until(self, prefix: str):
        while True:
            line = self.read_until_not_log()
            if line == "":
                continue
            elif line.startswith(prefix):
                return line
            else:
                print(f'{shell.SKIP}{line}{shell.ENDC}')

    async def async_send_command(self, command: str):
        return await asyncio.to_thread(self.send_command, command)

    def send_command(self, command: str):
        if (line := self.read_until_not_log()) != "":
            print(f'{shell.PRE}PRE: {line}{shell.ENDC}')

        self.ser.write(f'{command}\r'.encode('utf8'))
        self.ser.flush()
        time.sleep(0.05)

        self.read_until(command)
        result = self.read_until_not_log()

        # print(f'out_command={out_command}')
        # print(f'result={result}')

        if result.startswith('ERROR'):
            raise Exception(result.replace('ERROR:', '').strip())

        return result

    async def identify(self):
        return await self.async_send_command('IDENTIFY')

    async def set_led(self, buttons: Buttons, colour: Colour, brightness: Optional[float] = None):
        _buttons = _encode_buttons(buttons)
        _colour = _encode_colour(colour, brightness)

        command = f'SET LED:{_buttons},{_colour}'

        await self.async_send_command(command)


    async def set_key(self, buttons: Buttons, key_commands: List[str]):
        _buttons = _encode_buttons(buttons)
        _key_cmds = '/'.join(key_commands)

        command = f'SET KEY:{_buttons},{_key_cmds}'

        await self.async_send_command(command)


def _encode_buttons(buttons: Buttons) -> str:
    if isinstance(buttons, int):
        buttons = (buttons,)
    return '/'.join(map(str, buttons))

def _encode_colour(colour: Colour, brightness: Optional[float]) -> str:
    if brightness is None:
        parts = colour
    else:
        parts = colour + (brightness,)

    return '*'.join(map(str, parts))
