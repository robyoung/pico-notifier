from typing import Tuple, Optional, List
import time

import serial

Colour = Tuple[int, int, int]

OFF = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

YELLOW = (255, 255, 0)
MAGENTA = (255, 0, 255)
CYAN = (0, 255, 255)


class shell:
    SKIP = '\033[94m'
    LOG = '\033[92m'
    PRE = '\033[93m'
    ENDC = '\033[0m'


class Key:
    @staticmethod
    def key(*keys: str) -> str:
        return 'k{}'.format('|'.join(keys))

    @staticmethod
    def sleep(t: float) -> str:
        return f's{t}'

    @staticmethod
    def write(s: str) -> str:
        return f'w{s}'


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

    def identify(self):
        return self.send_command('IDENTIFY')

    def set_led(self, button: int, colour: Colour, brightness: Optional[float] = None):
        command = f'SET LED:{button},{self._encode_colour(colour)}'
        if brightness is not None:
            command = f'{command},{brightness}'

        self.send_command(command)

    @staticmethod
    def _encode_colour(colour: Colour) -> str:
        return ','.join([str(channel) for channel in colour])

    def set_key(self, button: int, key_commands: List[str]):
        command = 'SET KEY:{},{}'.format(button, ','.join(key_commands))
        self.send_command(command)


def main():
    with serial.Serial('/dev/ttyACM0', baudrate=115200, timeout=0.05) as ser:
        client = Client(ser)
        print('Identifying as: {}'.format(client.identify()))

        client.set_key(0, [
            Key.key('COMMAND'),
            Key.sleep(0.2),
            Key.write('slack'),
            Key.key('ENTER'),
        ])
        time.sleep(1)
        for i in range(16):
            client.set_led(i, CYAN, 0.5)
            time.sleep(0.5)

        while True:
            client.read_until_not_log()
            time.sleep(0.5)


if __name__ == '__main__':
    main()
