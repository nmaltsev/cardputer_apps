import sys

def clear():
    sys.stdout.write("\x1b[2J\x1b[H")
    # print("\x1b[2J\x1b[H", end='')

def move_cursor(x, y):
    sys.stdout.write(f"\x1b[{y+1};{x+1}H")

ANSI_KEYS = {
    "A": "UP",
    "B": "DOWN",
    "C": "RIGHT",
    "D": "LEFT",
    "H": "HOME",
    "F": "END",
}

ANSI_TILDE_KEYS = {
    "1": "HOME",
    "2": "INSERT",
    "3": "DELETE",
    "4": "END",
    "5": "PAGE_UP",
    "6": "PAGE_DOWN",
    "7": "HOME",
    "8": "END",
}

CTRL_KEYS = {
    "\x03": "CTRL_C",
    "\x04": "CTRL_D",
    "\x08": "BACKSPACE",
    "\x7f": "BACKSPACE",
    "\r": "ENTER",
    "\n": "ENTER",
    "\t": "TAB",
    "\x1b": "ESC",
}

# ANSI modifier codes
# 2=Shift, 3=Alt, 5=Ctrl, 6=Ctrl+Shift ...
MODIFIERS = {
    2: "SHIFT",
    3: "ALT",
    4: "ALT+SHIFT",
    5: "CTRL",
    6: "CTRL+SHIFT",
    7: "CTRL+ALT",
    8: "CTRL+ALT+SHIFT",
}


# =========================================================
# POSIX KEY READER
# =========================================================

def _read_escape_sequence():
    """
    Read full ANSI escape sequence after ESC.
    """
    seq = ""

    while True:
        ch = sys.stdin.read(1)
        seq += ch

        # ANSI sequences typically end with:
        # letters or '~'
        if ch.isalpha() or ch == "~":
            break

    return seq


def _decode_escape_sequence(seq):
    """
    Decode ANSI escape sequences.
    """

    # -----------------------------------------------------
    # Arrow/Home/End
    # Example:
    #   [A
    #   [1;2D
    #   [1;5C
    # -----------------------------------------------------

    if not seq.startswith("["):
        return "ESC"

    body = seq[1:]

    # Simple arrows: [A
    if body in ANSI_KEYS:
        return ANSI_KEYS[body]

    # Modified keys: [1;2D
    if ";" in body:
        prefix, rest = body.split(";", 1)

        mod_code = ""
        key_code = ""

        for ch in rest:
            if ch.isdigit():
                mod_code += ch
            else:
                key_code += ch

        mod = MODIFIERS.get(int(mod_code), "")
        key = ANSI_KEYS.get(key_code, key_code)

        return f"{mod}+{key}" if mod else key

    # Navigation keys: [3~
    if body.endswith("~"):
        code = body[:-1]
        return ANSI_TILDE_KEYS.get(code, code)

    return seq

def get_key():
    try:
        ch = sys.stdin.read(1)

        # Escape sequence
        if ch == "\x1b":
            seq = _read_escape_sequence()
            return _decode_escape_sequence(seq)

        # Named control keys
        if ch in CTRL_KEYS:
            return CTRL_KEYS[ch]

        # CTRL+A ... CTRL+Z
        code = ord(ch)
        if 1 <= code <= 26:
            return f"CTRL_{chr(code + 64)}"

        return ch
    except Exception as exc:
        print("get_key error: ", exc)


def main():
    prev = None
    while True:
        key = get_key()

        print(f"{key=}")

        # --- EXIT ---
        if key == 'CTRL_C' and prev == 'CTRL_C':
            break

        # --- CLEAR ---
        if key == 'CTRL_W':
            clear()

        if key == 'CTRL_N' :
            move_cursor(2, 10)
            print('??')
            
        prev = key

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Exception ', exc)
        raise exc
