from .utils import pad_line, get_key

# ---------- KEY PARSER ----------
def read_key():
    k = get_key()
    if k == '\x1b':  # ESC
        k2 = get_key()
        if k2 == '[':
            k3 = get_key()
            if k3 == 'A': return 'UP'
            elif k3 == 'B': return 'DOWN'
            elif k3 == 'C': return 'RIGHT'
            elif k3 == 'D': return 'LEFT'
        return 'ESC'

    if k == '\x13': return 'SAVE'   # Ctrl+S
    if k == '\x11': return 'QUIT'   # Ctrl+Q

    # Fallback
    if k.lower() == 's': return 'SAVE'
    if k.lower() == 'q': return 'QUIT'

    if k == '\r': return 'ENTER'
    if k == '\x7f': return 'BACKSPACE'

    return k


# ---------- EDITOR ----------
def text_editor(path):
    try:
        with open(path, "r") as f:
            lines = [l.rstrip("\n") for l in f.readlines()]
    except:
        lines = [""]

    if not lines:
        lines = [""]

    cx = 0          # cursor x (file coords)
    cy = 0          # cursor y
    row_offset = 0  # vertical scroll
    col_offset = 0  # horizontal scroll

    screen_h = 7
    screen_w = 38   # visible width on Cardputer

    dirty = False

    # For efficient redraw
    prev_header = None
    prev_content = [None] * screen_h
    prev_status = None

    full_redraw = True   # force full redraw after structural changes

    while True:
        # ---------- DRAW ----------
        header = pad_line(f"EDIT: {path}")

        content = []
        for i in range(screen_h):
            file_row = row_offset + i
            if file_row >= len(lines):
                c_line = pad_line("~", width=screen_w)
            else:
                line = lines[file_row]
                visible = line[col_offset : col_offset + screen_w]

                if file_row == cy:
                    rel_cx = cx - col_offset
                    disp_list = list(pad_line(visible, width=screen_w))
                    if 0 <= rel_cx < screen_w:
                        disp_list[rel_cx] = "_"
                    c_line = "".join(disp_list)
                else:
                    c_line = pad_line(visible, width=screen_w)

            content.append(c_line)

        inner_status = f"[{cy}:{cx}] {'*' if dirty else ''}"
        status = pad_line(inner_status + "  Ctrl+Q=quit  Ctrl+S=save", width=screen_w)

        # ---------- REDRAW ----------
        if full_redraw or prev_header is None or header != prev_header:
            print("\x1b[1;1H", end="")
            print(header, end="")
            prev_header = header

        for i in range(screen_h):
            if full_redraw or prev_content[i] is None or content[i] != prev_content[i]:
                print(f"\x1b[{2 + i};1H", end="")
                print(content[i], end="")
                prev_content[i] = content[i]

        if full_redraw or prev_status is None or status != prev_status:
            print(f"\x1b[{2 + screen_h};1H", end="")
            print(status, end="")
            prev_status = status

        full_redraw = False

        # ---------- INPUT ----------
        key = read_key()

        # ---------- QUIT ----------
        if key in ('q', 'QUIT'):
            if dirty:
                msg_row = 2 + screen_h + 1
                print(f"\x1b[{msg_row};1H", end="")
                print(pad_line("Unsaved! press q again", width=screen_w), end="")
                if read_key() in ('q', 'QUIT'):
                    break
                # clear message
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
                msg_row = 2 + screen_h + 1
                print(f"\x1b[{msg_row};1H", end="")
                print(pad_line(f"Save error: {e}", width=screen_w), end="")

        # ---------- MOVEMENT ----------
        elif key == 'UP':
            if cy > 0:
                cy -= 1
                cx = min(cx, len(lines[cy]))
        elif key == 'DOWN':
            if cy < len(lines) - 1:
                cy += 1
                cx = min(cx, len(lines[cy]))
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
            full_redraw = True   # important fix

        # ---------- BACKSPACE ----------
        elif key == 'BACKSPACE':
            if cx > 0:
                line = lines[cy]
                lines[cy] = line[:cx-1] + line[cx:]
                cx -= 1
                dirty = True
            elif cy > 0:
                # Merge with previous line
                prev_len = len(lines[cy - 1])
                lines[cy - 1] += lines[cy]
                lines.pop(cy)
                cy -= 1
                cx = prev_len          # fixed: cursor at end of joined text
                dirty = True
                full_redraw = True

        # ---------- INSERT CHARACTER ----------
        elif isinstance(key, str) and len(key) == 1 and key not in '\x1b\x7f\r':
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

        # ---------- SCROLLING (ensure cursor visible) ----------
        # Vertical
        if cy < row_offset:
            row_offset = cy
        elif cy >= row_offset + screen_h:
            row_offset = cy - screen_h + 1

        # Horizontal - now works for very long lines
        if cx < col_offset:
            col_offset = cx
        elif cx >= col_offset + screen_w:
            col_offset = cx - screen_w + 1

        row_offset = max(0, row_offset)
        col_offset = max(0, col_offset)