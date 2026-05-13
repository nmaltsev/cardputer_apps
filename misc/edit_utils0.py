
import sys
import os

POSIX_MAPPING_ARROWS = {
    "[A": 'UP',
    "[B": 'DOWN',
    "[C": 'RIGHT',
    "[D": 'LEFT',
}
POSIX_MAPPING_SHIFTARROWS = {
    "2A": 'UP',
    "2B": 'DOWN',
    "2C": 'RIGHT',
    "2D": 'LEFT',
}
POSIX_MAPPING_SHIFTARROWS = {
    "2A": 'UP',
    "2B": 'DOWN',
    "2C": 'RIGHT',
    "2D": 'LEFT',
}
POSIX_MAPPING_NAV = {
    '[6': 'PAGE_DOWN',
    '[5': 'PAGE_UP',
    '[1': 'HOME',
    '[4': 'END',
    '[2': 'INSERT',
    '[3': 'DELETE',
}

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
            # char = ''
            # while True:
            #     ch = sys.stdin.read(1)                
            #     if ch is None:
            #         break
            #     char += ch
            # print(f'{char=}')

            # Escape sequences (arrows, etc.)
            if ch == "\x1b":
                seq = sys.stdin.read(2)
                
                if seq in POSIX_MAPPING_ARROWS:
                    return POSIX_MAPPING_ARROWS[seq]

                if seq in POSIX_MAPPING_NAV:
                    seq1 = sys.stdin.read(1)
                    if seq1 == '~':
                        return POSIX_MAPPING_NAV[seq]
                    elif seq1 == ';':
                        seq2 = sys.stdin.read(2)
                        if seq2 in POSIX_MAPPING_SHIFTARROWS:
                            return 'SHIFT_' + POSIX_MAPPING_SHIFTARROWS[seq2]
                        else: 
                            print('SHIFT+', seq, seq1, seq2)
                    else:
                        print(f'{seq1=}')
                
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