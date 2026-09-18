import sys
import os

# Cardputer / terminal key translations.
#
# These are the control characters normally received by a
# terminal/USB console. Arrow keys are ANSI escape sequences.
CTRL_KEYS = {
    # "\x01": "CTRL_A",
    # "\x02": "CTRL_B",
    # "\x03": "CTRL_C",
    # "\x04": "CTRL_D",
    # "\x05": "CTRL_E",
    # "\x06": "CTRL_F",
    # "\x07": "CTRL_G",
    "\x08": "BACKSPACE",
    "\x09": "TAB",
    "\x0a": "ENTER",
    # "\x0b": "CTRL_K",
    # "\x0c": "CTRL_L",
    "\x0d": "ENTER",
    # "\x0e": "CTRL_N",
    # "\x0f": "CTRL_O",
    # "\x10": "CTRL_P",
    # "\x11": "CTRL_Q",
    # "\x12": "CTRL_R",
    # "\x13": "CTRL_S",
    # "\x14": "CTRL_T",
    # "\x15": "CTRL_U",
    # "\x16": "CTRL_V",
    # "\x17": "CTRL_W",
    # "\x18": "CTRL_X",
    # "\x19": "CTRL_Y",
    # "\x1a": "CTRL_Z",
    "\x7f": "BACKSPACE",
}

ESCAPE_SEQUENCES = {
    "\x1b[A": "UP",
    "\x1b[B": "DOWN",
    "\x1b[C": "RIGHT",
    "\x1b[D": "LEFT",
    "\x1b[3~": "DELETE",
    "\x1b[1;2A": "SHIFT+UP",
    "\x1b[1;2B": "SHIFT+DOWN",
    "\x1b[1;2C": "SHIFT+RIGHT",
    "\x1b[1;2D": "SHIFT+LEFT",
}

# ---------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------

def clear():
    sys.stdout.write("\x1b[2J\x1b[H")


def move_cursor(x, y):
    sys.stdout.write("\x1b[%d;%dH" % (y + 1, x + 1))


def read_one():
    """Read one character from the CircuitPython console."""
    return sys.stdin.read(1)


def get_key():
    """
    Translate terminal/USB-console input into the internal
    editor key names.

    Note: sys.stdin is a console stream. It is not the native
    Cardputer GPIO/I2C keyboard API.
    """
    try:
        ch = read_one()

        if not ch:
            return "NONE"

        if ch in CTRL_KEYS:
            return CTRL_KEYS[ch]

        # CTRL+A ... CTRL+Z
        code = ord(ch)
        if 1 <= code <= 26:
            return f"CTRL_{chr(code + 64)}"

        if ch != "\x1b":
            return ch

        # Read enough of an ANSI escape sequence to identify it.
        seq = ch

        # ANSI sequences used here are short. Read characters
        # until a final byte is encountered.
        for _ in range(7):
            nxt = read_one()
            if not nxt:
                break
            seq += nxt

            if nxt.isalpha() or nxt == "~":
                break

            if seq in ESCAPE_SEQUENCES:
                break

        if seq in ESCAPE_SEQUENCES:
            return ESCAPE_SEQUENCES[seq]

        return "ESC"

    except Exception as exc:
        if DEBUG:
            print("get_key error:", exc)
        return "NONE"