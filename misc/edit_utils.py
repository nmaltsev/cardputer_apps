
import sys
import os

def get_key():
    try:
        # Windows
        import msvcrt
        key = msvcrt.getch()

        # Special keys (arrows, function keys, etc.)
        if key in (b'\x00', b'\xe0'):
            key = msvcrt.getch()
            mapping = {
                b'H': 'UP',
                b'P': 'DOWN',
                b'K': 'LEFT',
                b'M': 'RIGHT',
            }
            return mapping.get(key, '')

        # Control keys
        if key == b'\x03':
            return 'CTRL_C'
        if key == b'\x04':
            return 'CTRL_D'
        if key == b'\x08':
            return 'BACKSPACE'
        if key == b'\r':
            return 'ENTER'
        if key == b'\t':
            return 'TAB'
        if key == b'\x1b':
            return 'ESC'

        # Ctrl + letter (ASCII 1–26)
        if 1 <= ord(key) <= 26:
            return f'CTRL_{chr(ord(key) + 64)}'

        return key.decode(errors="ignore")

    except ImportError:
        # Unix/Linux/macOS
        import sys
        import tty
        import termios

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)

        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)

            # Escape sequences (arrows, etc.)
            if ch == "\x1b":
                seq = sys.stdin.read(2)
                # print(f"{seq=}")
                mapping = {
                    "[A": 'UP',
                    "[B": 'DOWN',
                    "[C": 'RIGHT',
                    "[D": 'LEFT',
                    '[6': 'PAGE_DOWN',
                    '[5': 'PAGE_UP',
                    '[1': 'HOME',
                    '[4': 'END',
                    '[2': 'INSERT',
                    '[3': 'DELETE',
                }
                if seq in mapping:
                    return mapping[seq]
                return 'ESC'

            # Control keys
            if ch == '\x03':
                return 'CTRL_C'
            if ch == '\x04':
                return 'CTRL_D'
            if ch == '\x7f':
                return 'BACKSPACE'
            if ch in ('\r', '\n'):
                return 'ENTER'
            if ch == '\t':
                return 'TAB'

            # Ctrl + letter
            if 1 <= ord(ch) <= 26:
                return f'CTRL_{chr(ord(ch) + 64)}'

            return ch

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
# ---------- TERMINAL ----------
def clear():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()

def move_cursor(x, y):
    sys.stdout.write(f"\x1b[{y+1};{x+1}H")