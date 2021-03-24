COMMAND_IDENTIFY = "IDENTIFY"
COMMAND_SET_LED = "SET LED"
COMMAND_SET_KEY = "SET KEY"


def set_led(pixels, buttons, rgb):
    button_max = len(pixels) - 1

    for button in buttons:
        if button < 0 or button > button_max:
            raise ValueError(
                "button number must be positive int less than {}".format(button_max)
            )
        pixels[button] = rgb


def set_key(keysets, buttons, keycmds):
    for button in buttons:
        keysets[button] = keycmds


def parse_keycmd(keycmd, Keycode, buttons):
    if len(keycmd) < 2:
        raise ValueError("key command not long enough: {}".format(keycmd))

    name = keycmd[0]
    value = keycmd[1:]
    # s = sleep, k = keys, w = write
    if name == "s":
        return name, float(value)
    elif name == "k":
        try:
            return name, [getattr(Keycode, part) for part in value.split("|")]
        except AttributeError as e:
            raise ValueError("invalid keycode {}".format(e))
    elif name == "w":
        return name, value
    elif name == "l":
        return name, (buttons, parse_rgb(value))
    else:
        raise ValueError("unknown key command {}".format(keycmd))


def execute_keyset(kbd, layout, time, pixels, keyset):
    for (name, value) in keyset:
        if name == "s":
            time.sleep(value)
        elif name == "k":
            kbd.send(*value)
        elif name == "w":
            layout.write(value)
        elif name == "l":
            for button in value[0]:
                pixels[button] = value[1]


def parse_command(command, Keycode):
    parts = command.split(":", 1)
    command_id = parts[0].upper()

    if len(parts) > 1:
        raw_args = parts[1].split(",")
    else:
        raw_args = []

    try:
        if command_id == COMMAND_IDENTIFY:
            return (command_id, tuple([]))
        elif command_id == COMMAND_SET_LED:
            if len(raw_args) != 2:
                raise ValueError("expected 2 arguments")

            buttons = [int(button) for button in raw_args[0].split("/")]
            rgb = parse_rgb(raw_args[-1])

            return command_id, (buttons, rgb)
        elif command_id == COMMAND_SET_KEY:
            if len(raw_args) != 2:
                raise ValueError("expected 2 arguments")

            buttons = [int(button) for button in raw_args[0].split("/")]
            key_cmds = [
                parse_keycmd(key_cmd, Keycode, buttons)
                for key_cmd in raw_args[1].split("/")
            ]

            return command_id, (buttons, key_cmds)
        else:
            raise ValueError("unknown command")
    except ValueError as e:
        raise ValueError("Failed to parse command ({}) {}".format(e, command))


def parse_rgb(value):
    parts = value.split("*")
    try:
        if len(parts) in (3, 4):
            rgb = tuple([int(part) for part in parts[:3]])
            if len(parts) == 3:
                return rgb
            else:
                return rgb + (float(parts[3]),)
        raise ValueError
    except ValueError as e:
        raise ValueError("Invalid RGB value {} ({})".format(value, e))


def handle_command(runtime, pixels, keysets, Keycode):
    if runtime.serial_bytes_available:
        value = input().strip()

        try:
            command, args = parse_command(value, Keycode)
            if command == COMMAND_IDENTIFY:
                print("Notifier/0.1")
                return
            elif command == COMMAND_SET_LED:
                set_led(pixels, *args)
            elif command == COMMAND_SET_KEY:
                set_key(keysets, *args)
            else:
                raise ValueError("cannot be here")
            print("OK")
        except ValueError as e:
            print("ERROR: {}".format(e))
