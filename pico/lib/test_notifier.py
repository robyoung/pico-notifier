from unittest import mock

import pytest

import notifier


@pytest.mark.parametrize(
    ('keycmd', 'result'),
    [
        ('s10.0', ('s', 10.0)),
        ('s10', ('s', 10.0)),
        ('wblahblah', ('w', 'blahblah')),
        ('kCOMMAND|P', ('k', ['COMMAND', 'P'])),
    ]
)
def test_parse_keycmd(keycmd, result):
    Keycode = mock.Mock()
    Keycode.COMMAND = 'COMMAND'
    Keycode.P = 'P'
    assert notifier.parse_keycmd(keycmd, Keycode) == result


@pytest.mark.parametrize(
    ('command', 'result'),
    [
        ('SET LED:12/12,12*12*12', ('SET LED', ([12, 12], (12, 12, 12)))),
        ('set led:12,12*12*12', ('SET LED', ([12], (12, 12, 12)))),
        ('SET LED:12/12,12*12*12*12.0', ('SET LED', ([12, 12], (12, 12, 12, 12.0)))),
        ('SET KEY:12,kCOMMAND|P/wblahblah/s1.1', ('SET KEY', ([12], [('k', ['COMMAND', 'P']), ('w', 'blahblah'), ('s', 1.1)]))),
    ]
)
def test_parse_command(command, result):
    # arrange
    Keycode = mock.Mock()
    Keycode.COMMAND = 'COMMAND'
    Keycode.P = 'P'

    # act
    parsed_command = notifier.parse_command(command, Keycode)

    # assert
    assert parsed_command == result
