Here is a minimul text editor for M5Stack Cardputer written in CircuitPython
```
from .utils import pad_line, get_key, clear

# New featured (W v2)
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

    # Ctrl keys - these are the actual control characters
    if k == '\x13':      # Ctrl+S
        return 'SAVE'
    if k == '\x11':      # Ctrl+Q
        return 'QUIT'

    # Fallback for lowercase (useful when testing or if Ctrl doesn't work)
    if k == 's':
        return 'SAVE'
    if k == 'q':
        return 'QUIT'

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

    if not lines:
        lines = [""]

    cx = 0          # cursor x (in file coordinates)
    cy = 0          # cursor y
    row_offset = 0  # vertical scroll
    col_offset = 0  # horizontal scroll
    screen_h = 7
    screen_w = 38
    dirty = False

    # previous display state for efficient redraw
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
                    # Build exactly screen_w chars with cursor
                    disp_list = list(pad_line(visible, width=screen_w))
                    if 0 <= rel_cx < screen_w:
                        disp_list[rel_cx] = "_"
                    c_line = "".join(disp_list)
                else:
                    c_line = pad_line(visible, width=screen_w)
            content.append(c_line)

        inner_status = "[{}:{}] {}".format(cy, cx, "*" if dirty else "")
        status = pad_line(inner_status + " Ctrl+Q=quit Ctrl+S=save")

        # ---------- PARTIAL REDRAW ONLY CHANGED PARTS ----------
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
                msg_row = 2 + screen_h + 1
                print(f"\x1b[{msg_row};1H", end="")
                print(pad_line("Unsaved! press q again"), end="")
                k2 = read_key()
                if k2 in ('q', 'QUIT'):
                    break
                else:
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
            new_line = line[cx:]          # rest of the line moves down
            lines[cy] = line[:cx]         # current line is truncated
            lines.insert(cy + 1, new_line)
            cy += 1
            cx = 0
            dirty = True

        # ---------- BACKSPACE ----------
        elif key == 'BACKSPACE':
            if cx > 0:
                # delete character inside line
                line = lines[cy]
                lines[cy] = line[:cx - 1] + line[cx:]
                cx -= 1
                dirty = True
            elif cy > 0:
                # merge with previous line
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

        # ---------- ENSURE CURSOR VISIBLE (scrolling) ----------
        # vertical
        if cy < row_offset:
            row_offset = cy
        elif cy >= row_offset + screen_h:
            row_offset = cy - screen_h + 1

        # horizontal - fixed for long lines
        if cx < col_offset:
            col_offset = cx
        elif cx >= col_offset + screen_w:
            col_offset = cx - screen_w + 1

        # safety clamps
        row_offset = max(0, row_offset)
        col_offset = max(0, col_offset)
```

utils.py:
```
import sys
import os
import json

# ---------- KEY INPUT ----------
def get_key():
    try:
        import supervisor
        while not supervisor.runtime.serial_bytes_available:
            pass
        return sys.stdin.read(1)
    except:
        return input()[0]


# ---------- FORMAT LINE ----------
def pad_line(text, width=38):
    if len(text) >= width:
        return text[:width]
    return text + "_" * (width - len(text))


# ---------- TEXT WRAP ----------
def wrap_line(line, width=37):
    lines = []
    while len(line) > width:
        lines.append(line[:width])
        line = line[width:]
    lines.append(line)
    return lines

def clear():
	# sys.stderr.write("\x1b[2J\x1b[H")
    # print(chr(27)+"[2J")
    print("\x1b[2J\x1b[H", end='')

# ---------- BINARY DETECTION ----------
def is_text_file(path):
    # Whitelisted text extensions (lowercase, no allocation-heavy ops)
    TEXT_EXTS = (
        ".py", ".yaml", ".yml", '.bat',
        ".txt", ".log", ".htm", ".html", ".xml",
        ".toml", ".json", ".md", ".js", ".css"
    )

    # Extract filename (avoid os.path to keep it lightweight)
    name = path.rsplit("/", 1)[-1]

    # Find extension
    dot = name.rfind(".")
    if dot == -1:
        return False

    ext = name[dot:].lower()

    # Check against whitelist
    for e in TEXT_EXTS:
        if ext == e:
            return True

    return False

def open_settings():
    try:
        # Detect current script directory
        try:
            base_dir = os.path.dirname(__file__)
            if not base_dir:
                base_dir = "/"
        except:
            base_dir = "/"

        settings_path = base_dir + "/settings.json"

        # Create default settings if missing
        if "settings.json" not in os.listdir(base_dir):
            default_settings = {
                "wifi": {
                    "known": [
                        {"ssid": "", "password": ""}
                    ],
                    "default": "ssid"
                },
                "brightness": 0.3
            }

            try:
                with open(settings_path, "w") as f:
                    json.dump(default_settings, f)
                print("Created settings.json")
            except Exception as e:
                print("Error creating settings.json:", e)
                return

        # Open editor
        try:
            from .editor import text_editor
            text_editor(settings_path)
        except Exception as e:
            print("Error opening editor:", e)

    except Exception as e:
        print("Settings error:", e)
```

Fix the following issues:
1. ENTER does not properly split visually. The line continue showing characters that has been moved to the next line
2. BACKSPACE does not merge lines correctly. the cursor continues to be at 0 of the current line
3. Horizontal editing does not work beyond 38 chars.