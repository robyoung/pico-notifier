def set_led(args, pixels):
    if len(args) < 4:
        raise ValueError('not enoug args: {}'.format(args))

    try:
        button = int(args[0])
    except ValueError as e:
        raise ValueError('invalid button number: {}'.format(e))

    try:
        pixel_args = tuple([int(colour) for colour in args[1:4]])
    except ValueError as e:
        raise ValueError('invalid colour: {}'.format(e))

    if len(args) > 4:
        try:
            pixel_args = pixel_args + (float(args[4]),)
        except ValueError as e:
            raise ValueError('invalid brightness: {}'.format(e))

    if button < 0 or button > len(pixels) - 1:
        raise ValueError('button number out of range: {}'.format(button))

    pixels[button] = pixel_args


def set_key(args, keysets, Keycode):
    if len(args) < 2:
        raise ValueError('not enough args: {}'.format(args))

    try:
        button = int(args[0])
    except ValueError as e:
        raise ValueError('invalid button number: {}'.format(e))

    keyset = [parse_keycmd(arg, Keycode) for arg in args[1:]]

    keysets[button] = tuple(keyset)


def parse_keycmd(keycmd, Keycode):
    if len(keycmd) < 2:
        raise ValueError('key command not long enough: {}'.format(keycmd))

    name = keycmd[0]
    value = keycmd[1:]
    # s = sleep, k = keys, w = write
    if name == 's':
        return name, float(value)
    elif name == 'k':
        try:
            return name, [getattr(Keycode, part) for part in value.split('|')]
        except AttributeError as e:
            raise ValueError('invalid keycode {}'.format(e))
    elif name == 'w':
        return name, value
    else:
        raise ValueError('unknown key command {}'.format(keycmd))


def execute_keyset(keyset, kbd, layout, time):
    for (name, value) in keyset:
        if name == 's':
            time.sleep(value)
        elif name == 'k':
            kbd.send(*value)
        elif name == 'w':
            layout.write(value)

def handle_command(runtime, pixels, keysets, Keycode):
    if runtime.serial_bytes_available:
        value = input().strip()
        parts = value.split(':', 1)

        command = parts[0].upper()
        if len(parts) > 1:
            args = [arg.strip() for arg in parts[1].split(',')]
        else:
            args = []

        try:
            if command == 'IDENTIFY':
                print('Notifier/0.1')
                return
            elif command == 'SET LED':
                set_led(args, pixels)
            elif command == 'SET KEY':
                set_key(args, keysets, Keycode)
            else:
                raise ValueError('unkown command {}'.format(command))
            print('OK')
        except ValueError as e:
            print('ERROR: {}'.format(e))
