# Notifier

Using the Pimoroni RGB Keypad as a notifications interface.

Allow the buttons LEDs and key sequences to be controlled over serial from the host.


## Protocol

### Hierarchy of separators

- `,`
- `|`
- `/`

### `IDENTIFY`

No arguments. Respond with user agent string.

### `SET LED`

Set the colour state of a single LED.

- Pixel numbers
- RGB channels (`*` separated channels, so `{red}*{green}*{blue}` or `{red}*{green}*{blue}*{brightness}`)

### `SET KEY`

Set what happens when a button is pressed. Assigns a set of 'key commands' to a given button number.

- Button number
- At least one 'key command'

A key command can be:
- Write a string of character `w{characters}` eg. `whello bob`
- Send a key combination separated by `k{keys separated by |}` eg. `kCOMMAND|P`
- Wait for a time `s{float seconds}` eg. `s0.1`
- Update the LED state of these buttons `l{rgb}`
