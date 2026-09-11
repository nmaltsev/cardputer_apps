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


def read_escape_sequence():
    seq = ""

    while True:
        ch = sys.stdin.read(1)
        seq += ch

        # ANSI sequences typically end with letters or '~'
        if not ch or ch.isalpha() or ch == "~":
            break

    return seq


def get_key():
    try:
        ch = sys.stdin.read(1)

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


def get_key2():
    # Alt + q = \x1,bq
    # Alt + 3 = \x1,b3
    # Opt + q = \x1,0q
    try:
        ch = sys.stdin.read(6)

        return ch
    except Exception as exc:
        print("get_key error: ", exc)


# WORKS
def main1():
    prev = None
    try:
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
                move_cursor(10, 5)
                print('??')
                
            prev = key
    except Exception as exc:
        print('Exception ', exc)
        raise exc


def main2():
    try:
        prev = None
        while True:
            seq = read_escape_sequence()
            print(f"{seq=}")

            prev = seq
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print('Exception ', exc)
        raise exc

def main3():
    try:
        prev = None
        while True:
            seq = get_key2()
            arr = [ord(ch) for ch in seq]
            print(f"{seq=} {arr=}")

            prev = seq
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print('Exception ', exc)
        raise exc


if __name__ == '__main__':
    main()
