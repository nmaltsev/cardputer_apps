from .utils import pad_line, get_key, clear
# OLD stable editor


# ---------- KEY PARSER ----------
def read_key():
    k = get_key()

    # Handle escape sequences (arrows)
    if k == '\x1b':  # ESC
        k2 = get_key()
        if k2 == '[':
            k3 = get_key()
            if k3 == 'A':
                return 'UP'
            elif k3 == 'B':
                return 'DOWN'
            elif k3 == 'C':
                return 'RIGHT'
            elif k3 == 'D':
                return 'LEFT'
        return 'ESC'

    # Ctrl keys
    if k == '\x13':
        return 'SAVE'  # Ctrl+S
    if k == '\x11':
        return 'QUIT'  # Ctrl+Q

    if k == '\r':
        return 'ENTER'
    if k == '\x7f':
        return 'BACKSPACE'

    return k


# ---------- EDITOR ----------
def text_editor(path):
    try:
        with open(path, "r") as f:
            lines = [l.rstrip("\n") for l in f.readlines()]
    except:
        lines = [""]

    cx = 0  # cursor x
    cy = 0  # cursor y
    row_offset = 0

    screen_h = 7
    screen_w = 38

    dirty = False

    while True:
        # clear()

        print(pad_line("EDIT: {}".format(path)))

        # ---------- DRAW ----------
        for i in range(screen_h):
            file_row = row_offset + i

            if file_row >= len(lines):
                print("~")
                continue

            line = lines[file_row]

            # clip horizontally
            visible = line[:screen_w]

            # cursor line
            if file_row == cy:
                cursor_line = ""
                for j in range(len(visible)):
                    if j == cx:
                        cursor_line += "_"
                    else:
                        cursor_line += visible[j]

                if cx >= len(visible):
                    cursor_line += "_"

                print(cursor_line)
            else:
                print(visible)

        status = "[{}:{}] {}".format(cy, cx, "*" if dirty else "")
        print(pad_line(status + " q=quit s=save"))

        # ---------- INPUT ----------
        key = read_key()

        # ---------- QUIT ----------
        if key in ('q', 'QUIT'):
            if dirty:
                print("Unsaved! press q again")
                k2 = read_key()
                if k2 in ('q', 'QUIT'):
                    break
            else:
                break

        # ---------- SAVE ----------
        elif key in ('s', 'SAVE'):
            try:
                with open(path, "w") as f:
                    for l in lines:
                        f.write(l + "\n")
                dirty = False
            except Exception as e:
                print("save error:", e)

        # ---------- MOVEMENT ----------
        elif key == 'UP':
            if cy > 0:
                cy -= 1
                if cy < row_offset:
                    row_offset -= 1

        elif key == 'DOWN':
            if cy < len(lines) - 1:
                cy += 1
                if cy >= row_offset + screen_h:
                    row_offset += 1

        elif key == 'LEFT':
            if cx > 0:
                cx -= 1
            elif cy > 0:
                cy -= 1
                cx = len(lines[cy])

        elif key == 'RIGHT':
            if cx < len(lines[cy]):
                cx += 1
            elif cy < len(lines) - 1:
                cy += 1
                cx = 0

        # ---------- ENTER ----------
        elif key == 'ENTER':
            line = lines[cy]
            new_line = line[cx:]
            lines[cy] = line[:cx]
            lines.insert(cy + 1, new_line)
            cy += 1
            cx = 0
            dirty = True

        # ---------- BACKSPACE ----------
        elif key == 'BACKSPACE':
            if cx > 0:
                line = lines[cy]
                lines[cy] = line[:cx - 1] + line[cx:]
                cx -= 1
                dirty = True
            elif cy > 0:
                prev_len = len(lines[cy - 1])
                lines[cy - 1] += lines[cy]
                lines.pop(cy)
                cy -= 1
                cx = prev_len
                dirty = True

        # ---------- INSERT CHAR ----------
        elif isinstance(key, str) and len(key) == 1:
            line = lines[cy]
            lines[cy] = line[:cx] + key + line[cx:]
            cx += 1
            dirty = True

        # ---------- CLAMP ----------
        if cy >= len(lines):
            cy = len(lines) - 1
        if cy < 0:
            cy = 0

        if cx > len(lines[cy]):
            cx = len(lines[cy])