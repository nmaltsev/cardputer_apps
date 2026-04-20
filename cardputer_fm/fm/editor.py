from .utils import pad_line, get_key, clear

# ---------- KEY PARSER ----------
def read_key():
    k = get_key()
    # Handle escape sequences (arrows + DELETE)
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
            elif k3 == '3':
                k4 = get_key()
                if k4 == '~':
                    return 'DELETE'
                # Unknown sequence after [3 → ignore and treat as ESC
                return 'ESC'
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


# ---------- SCROLL HELPER ----------
def _update_scroll(cx, cy, row_offset, col_offset, lines, screen_h, screen_w):
    # Vertical scroll: keep cursor visible
    if row_offset > cy:
        row_offset = cy
    elif row_offset + screen_h <= cy:
        row_offset = cy - screen_h + 1
    if row_offset < 0:
        row_offset = 0

    # Horizontal scroll: keep cursor visible on current line
    line_len = len(lines[cy]) if cy < len(lines) else 0
    if col_offset > cx:
        col_offset = cx
    elif col_offset + screen_w <= cx:
        col_offset = cx - screen_w + 1
    if col_offset < 0:
        col_offset = 0

    return row_offset, col_offset


# ---------- EDITOR ----------
def text_editor(path):
    try:
        with open(path, "r") as f:
            lines = [l.rstrip("\n") for l in f.readlines()]
    except:
        lines = [""]

    cx = 0  # cursor x (column in current line)
    cy = 0  # cursor y (line index)
    row_offset = 0  # vertical scroll
    col_offset = 0  # horizontal scroll (NEW)
    screen_h = 7
    screen_w = 38
    dirty = False

    while True:
        # ---------- DRAW ----------
        print(pad_line("EDIT: {}".format(path)))

        for i in range(screen_h):
            file_row = row_offset + i
            if file_row >= len(lines):
                print("~")
                continue
            line = lines[file_row]
            # Horizontal clipping with scroll (NEW)
            visible = line[col_offset : col_offset + screen_w]

            # Cursor line (shows _ instead of char or at end)
            if file_row == cy:
                rel_cx = cx - col_offset
                cursor_line = ""
                vlen = len(visible)
                for j in range(vlen):
                    if j == rel_cx:
                        cursor_line += "_"
                    else:
                        cursor_line += visible[j]
                if rel_cx >= vlen:
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

        # ---------- BACKSPACE (delete left) ----------
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

        # ---------- DELETE (forward delete) - NEW ----------
        elif key == 'DELETE':
            if cx < len(lines[cy]):
                # Delete character under cursor
                line = lines[cy]
                lines[cy] = line[:cx] + line[cx + 1:]
                dirty = True
                # cx stays in place
            elif cy < len(lines) - 1:
                # At end of line → join with next line
                lines[cy] += lines[cy + 1]
                lines.pop(cy + 1)
                dirty = True
                # cx stays (now at the join point)

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
        if cx > len(lines[cy]) if cy < len(lines) else 0:
            cx = len(lines[cy]) if cy < len(lines) else 0

        # ---------- APPLY SCROLL (horizontal + vertical) - IMPROVED ----------
        row_offset, col_offset = _update_scroll(
            cx, cy, row_offset, col_offset, lines, screen_h, screen_w
        )
