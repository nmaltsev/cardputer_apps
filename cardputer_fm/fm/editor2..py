from .utils import pad_line, get_key, clear
# ---------- KEY PARSER ----------
def read_key():
    k = get_key()
    # Handle escape sequences (arrows)
    if k == '\x1b': # ESC
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
        return 'SAVE' # Ctrl+S
    if k == '\x11':
        return 'QUIT' # Ctrl+Q
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
    cx = 0 # cursor x
    cy = 0 # cursor y
    row_offset = 0
    col_offset = 0
    screen_h = 7
    screen_w = 38
    dirty = False
    # previous display state for efficient redraw (only changed parts)
    prev_header = None
    prev_content = [None] * screen_h
    prev_status = None
    while True:
        # ---------- DRAW (compute what should be on screen) ----------
        header = pad_line("EDIT: {}".format(path))
        content = []
        for i in range(screen_h):
            file_row = row_offset + i
            if file_row >= len(lines):
                c_line = pad_line("~")
            else:
                line = lines[file_row]
                visible = line[col_offset : col_offset + screen_w]
                if file_row == cy:
                    rel_cx = cx - col_offset
                    # build exactly screen_w chars, placing _ at cursor (replaces char or first padding space)
                    disp_list = list(visible.ljust(screen_w))
                    disp_list[rel_cx] = "_"
                    c_line = "".join(disp_list)
                else:
                    c_line = pad_line(visible)
            content.append(c_line)
        inner_status = "[{}:{}] {}".format(cy, cx, "*" if dirty else "")
        status = pad_line(inner_status + " q=quit s=save")
        # ---------- PARTIAL REDRAW ONLY CHANGED PARTS (ANSI cursor positioning) ----------
        # screen layout (1-based ANSI rows):
        # row 1: header
        # rows 2..(1+screen_h): content
        # row (2+screen_h): status
        if prev_header is None or header != prev_header:
            print("\x1b[1;1H", end="")
            print(header, end="")
            prev_header = header
        for i in range(screen_h):
            if prev_content[i] is None or content[i] != prev_content[i]:
                print(f"\x1b[{2 + i};1H", end="")
                print(content[i], end="")
                prev_content[i] = content[i]
        if prev_status is None or status != prev_status:
            print(f"\x1b[{2 + screen_h};1H", end="")
            print(status, end="")
            prev_status = status
        # ---------- INPUT ----------
        key = read_key()
        # ---------- QUIT ----------
        if key in ('q', 'QUIT'):
            if dirty:
                # positioned temporary message (line after status)
                msg_row = 2 + screen_h + 1
                print(f"\x1b[{msg_row};1H", end="")
                print(pad_line("Unsaved! press q again"), end="")
                k2 = read_key()
                if k2 in ('q', 'QUIT'):
                    break
                else:
                    # clear the message line
                    print(f"\x1b[{msg_row};1H", end="")
                    print(" " * screen_w, end="")
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
                # positioned error message (line after status)
                msg_row = 2 + screen_h + 1
                print(f"\x1b[{msg_row};1H", end="")
                print(pad_line(f"save error: {e}"), end="")
        # ---------- MOVEMENT ----------
        elif key == 'UP':
            if cy > 0:
                cy -= 1
        elif key == 'DOWN':
            if cy < len(lines) - 1:
                cy += 1
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
        # ---------- CLAMP CURSOR ----------
        if cy >= len(lines):
            cy = len(lines) - 1
        if cy < 0:
            cy = 0
        if cx > len(lines[cy]):
            cx = len(lines[cy])
        # ---------- ENSURE CURSOR VISIBLE (horizontal + vertical scroll) ----------
        # vertical scroll (keeps cursor in viewport, same logic as original but generalized)
        if cy < row_offset:
            row_offset = cy
        elif cy >= row_offset + screen_h:
            row_offset = cy - screen_h + 1
        # horizontal scroll
        if cx < col_offset:
            col_offset = cx
        elif cx >= col_offset + screen_w:
            col_offset = cx - screen_w + 1
        # safety clamps
        row_offset = max(0, row_offset)
        col_offset = max(0, col_offset)
