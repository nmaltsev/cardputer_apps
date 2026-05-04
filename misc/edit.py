import sys
import os

# ---------- KEY INPUT ----------
def get_key():
    try:
        import msvcrt
        key = msvcrt.getch()

        if key == b'\xe0':  # special key
            key = msvcrt.getch()
            mapping = {
                b'H': 'UP',
                b'P': 'DOWN',
                b'K': 'LEFT',
                b'M': 'RIGHT'
            }
            return mapping.get(key, '')

        return key.decode(errors="ignore")

    except ImportError:
        import sys, tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                seq = sys.stdin.read(2)
                mapping = {
                    "[A": 'UP',
                    "[B": 'DOWN',
                    "[C": 'RIGHT',
                    "[D": 'LEFT'
                }
                return mapping.get(seq, '')
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ---------- TERMINAL ----------
def clear():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()

# TODO read the necessery key presses in the loop
