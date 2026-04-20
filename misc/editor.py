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

def move_cursor(x, y):
    sys.stdout.write(f"\x1b[{y+1};{x+1}H")

def get_window_size():
    try:
        import shutil
        size = shutil.get_terminal_size()
        return size.columns, size.lines
    except:
        return 80, 24


# ---------- FILE ----------
def load_file(path):
    if not os.path.exists(path):
        return [""]
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().split("\n")

def save_file(path, buffer):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(buffer))


# ---------- EDITOR ----------
def editor(filename):
    buffer = load_file(filename)

    cx, cy = 0, 0        # cursor position in file
    row_offset = 0       # vertical scroll
    col_offset = 0       # horizontal scroll

    while True:
        width, height = get_window_size()
        text_height = height - 1  # last line = status bar

        clear()
        sys.stdout.write("\x1b[?25h")  # force show cursor
        sys.stdout.flush()

        # ---------- DRAW TEXT ----------
        for i in range(text_height):
            file_row = i + row_offset
            if file_row < len(buffer):
                line = buffer[file_row][col_offset:col_offset+width]
                print(line.ljust(width))
            else:
                print("~".ljust(width))

            # manually add newline EXCEPT last line
            if i < text_height - 1:
                sys.stdout.write("\n")

        # ---------- STATUS BAR ----------
        status = f"{filename}  |  Ln {cy+1}, Col {cx+1}"
        status = status[:width].ljust(width)
        move_cursor(0, text_height)
        sys.stdout.write("\x1b[7m" + status + "\x1b[0m")  # inverted colors

        # ---------- CURSOR DRAW ----------
        screen_x = cx - col_offset
        screen_y = cy - row_offset

        if 0 <= screen_y < text_height:
            move_cursor(screen_x, screen_y)

            line = buffer[cy]
            if screen_x < len(line):
                ch = line[screen_x]
            else:
                ch = " "

            sys.stdout.write("\x1b[7m" + ch + "\x1b[0m")

            move_cursor(screen_x, screen_y)

        sys.stdout.flush()

        key = get_key()

        # -------- QUIT --------
        if key == "\x11":  # Ctrl+Q
            break

        # -------- SAVE --------
        elif key == "\x13":  # Ctrl+S
            save_file(filename, buffer)

        # -------- BACKSPACE --------
        elif key in ("\x08", "\x7f"):
            if cx > 0:
                line = buffer[cy]
                buffer[cy] = line[:cx-1] + line[cx:]
                cx -= 1
            elif cy > 0:
                prev_len = len(buffer[cy-1])
                buffer[cy-1] += buffer[cy]
                buffer.pop(cy)
                cy -= 1
                cx = prev_len

        # -------- ENTER --------
        elif key == "\r":
            line = buffer[cy]
            buffer[cy] = line[:cx]
            buffer.insert(cy+1, line[cx:])
            cy += 1
            cx = 0

        # -------- ARROWS --------
        elif key == 'UP':
            cy = max(0, cy - 1)
        elif key == 'DOWN':
            cy = min(len(buffer) - 1, cy + 1)
        elif key == 'LEFT':
            cx = max(0, cx - 1)
        elif key == 'RIGHT':
            cx = min(len(buffer[cy]), cx + 1)

        # -------- TEXT INPUT --------
        elif len(key) == 1 and key.isprintable():
            line = buffer[cy]
            buffer[cy] = line[:cx] + key + line[cx:]
            cx += 1

        # ---------- CLAMP ----------
        cx = min(cx, len(buffer[cy]))

        # ---------- SCROLL ----------
        if cy < row_offset:
            row_offset = cy
        elif cy >= row_offset + text_height:
            row_offset = cy - text_height + 1

        if cx < col_offset:
            col_offset = cx
        elif cx >= col_offset + width:
            col_offset = cx - width + 1


# ---------- RUN ----------
if __name__ == "__main__":
    filename = sys.argv[1] if len(sys.argv) > 1 else "test.txt"
    editor(filename)