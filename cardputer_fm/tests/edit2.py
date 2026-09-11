import sys
import os

# =========================================================
# Cardputer terminal text editor
#
# This version keeps the original ANSI-terminal UI and editor
# model, but fixes the CircuitPython compatibility issues and
# uses USB CDC input rather than the physical Cardputer keyboard.
#
# IMPORTANT:
# The editor is a terminal editor. It expects the Cardputer to
# provide keyboard input through USB CDC / the console.
# It does NOT draw on the Cardputer LCD.
# =========================================================

# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

VIEW_BOX = (0, 0, 40, 8)       # x, y, width, height
DEBUG = False

# Cardputer / terminal key translations.
#
# These are the control characters normally received by a
# terminal/USB console. Arrow keys are ANSI escape sequences.
CTRL_KEYS = {
    "\x01": "CTRL_A",
    "\x02": "CTRL_B",
    "\x03": "CTRL_C",
    "\x04": "CTRL_D",
    "\x05": "CTRL_E",
    "\x06": "CTRL_F",
    "\x07": "CTRL_G",
    "\x08": "BACKSPACE",
    "\x09": "TAB",
    "\x0a": "ENTER",
    "\x0b": "CTRL_K",
    "\x0c": "CTRL_L",
    "\x0d": "ENTER",
    "\x0e": "CTRL_N",
    "\x0f": "CTRL_O",
    "\x10": "CTRL_P",
    "\x11": "CTRL_Q",
    "\x12": "CTRL_R",
    "\x13": "CTRL_S",
    "\x14": "CTRL_T",
    "\x15": "CTRL_U",
    "\x16": "CTRL_V",
    "\x17": "CTRL_W",
    "\x18": "CTRL_X",
    "\x19": "CTRL_Y",
    "\x1a": "CTRL_Z",
    "\x7f": "BACKSPACE",
}

ESCAPE_SEQUENCES = {
    "\x1b[A": "UP",
    "\x1b[B": "DOWN",
    "\x1b[C": "RIGHT",
    "\x1b[D": "LEFT",
    "\x1b[3~": "DELETE",
    "\x1b[1;2A": "SHIFT+UP",
    "\x1b[1;2B": "SHIFT+DOWN",
    "\x1b[1;2C": "SHIFT+RIGHT",
    "\x1b[1;2D": "SHIFT+LEFT",
}

# ---------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------

def clear():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


def move_cursor(x, y):
    sys.stdout.write("\x1b[%d;%dH" % (y + 1, x + 1))


def read_one():
    """Read one character from the CircuitPython console."""
    return sys.stdin.read(1)


def get_key():
    """
    Translate terminal/USB-console input into the internal
    editor key names.

    Note: sys.stdin is a console stream. It is not the native
    Cardputer GPIO/I2C keyboard API.
    """
    try:
        ch = read_one()

        if not ch:
            return "NONE"

        if ch in CTRL_KEYS:
            return CTRL_KEYS[ch]

        if ch != "\x1b":
            return ch

        # Read enough of an ANSI escape sequence to identify it.
        seq = ch

        # ANSI sequences used here are short. Read characters
        # until a final byte is encountered.
        for _ in range(7):
            nxt = read_one()
            if not nxt:
                break
            seq += nxt

            if nxt.isalpha() or nxt == "~":
                break

            if seq in ESCAPE_SEQUENCES:
                break

        if seq in ESCAPE_SEQUENCES:
            return ESCAPE_SEQUENCES[seq]

        return "ESC"

    except Exception as exc:
        if DEBUG:
            print("get_key error:", exc)
        return "NONE"


# ---------------------------------------------------------
# Utility
# ---------------------------------------------------------

def fill(text, max_width):
    if len(text) >= max_width:
        return text[:max_width]
    return text + "-" * (max_width - len(text))


# ---------------------------------------------------------
# Document model
# ---------------------------------------------------------

class EditorState:
    def __init__(self):
        self.doc_lines = [""]
        self.view_offset = 0
        self.file_path = None
        self.clipboard = ""
        self.selection_active = False
        self.selection_anchor = None
        self.selection_end = None
        self.selection_in_progress = False


state = EditorState()


# ---------------------------------------------------------
# Clipboard
# ---------------------------------------------------------

def copy_to_clipboard(text):
    state.clipboard = text


def paste_from_clipboard():
    return state.clipboard


# ---------------------------------------------------------
# File I/O
# ---------------------------------------------------------

def load_file(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            data = f.read()

        # Keep a final empty line if the file ends with '\n'.
        state.doc_lines = data.split("\n")

        if not state.doc_lines:
            state.doc_lines = [""]
    else:
        state.doc_lines = [""]


def save_file(path):
    with open(path, "w") as f:
        f.write("\n".join(state.doc_lines))


# ---------------------------------------------------------
# Selection
# ---------------------------------------------------------

def normalize_selection():
    if (
        state.selection_anchor is None
        or state.selection_end is None
    ):
        return None

    a = state.selection_anchor
    b = state.selection_end

    if a <= b:
        return a, b

    return b, a


def has_selection():
    r = normalize_selection()

    if r is None:
        return False

    a, b = r
    return a != b


def clear_selection():
    state.selection_active = False
    state.selection_anchor = None
    state.selection_end = None
    state.selection_in_progress = False


def begin_selection(row, col):
    if not state.selection_active:
        state.selection_active = True
        state.selection_anchor = (row, col)

    state.selection_end = (row, col)
    state.selection_in_progress = True


def update_selection(row, col):
    state.selection_end = (row, col)


def finalize_selection():
    state.selection_in_progress = False


def get_selected_text():
    r = normalize_selection()

    if r is None:
        return ""

    (r1, c1), (r2, c2) = r

    if r1 == r2:
        return state.doc_lines[r1][c1:c2]

    out = []
    out.append(state.doc_lines[r1][c1:])

    for y in range(r1 + 1, r2):
        out.append(state.doc_lines[y])

    out.append(state.doc_lines[r2][:c2])

    return "\n".join(out)


def delete_selection():
    r = normalize_selection()

    if r is None:
        return None

    (r1, c1), (r2, c2) = r

    if r1 == r2:
        line = state.doc_lines[r1]
        state.doc_lines[r1] = line[:c1] + line[c2:]
    else:
        first = state.doc_lines[r1][:c1]
        last = state.doc_lines[r2][c2:]

        state.doc_lines[r1] = first + last
        del state.doc_lines[r1 + 1:r2 + 1]

    if not state.doc_lines:
        state.doc_lines = [""]

    clear_selection()
    return r1, c1


# ---------------------------------------------------------
# Text insertion
# ---------------------------------------------------------

def insert_text(row, col, text):
    parts = text.split("\n")

    line = state.doc_lines[row]
    before = line[:col]
    after = line[col:]

    if len(parts) == 1:
        state.doc_lines[row] = before + text + after
        return row, col + len(text)

    state.doc_lines[row] = before + parts[0]

    insert_pos = row + 1

    for p in parts[1:-1]:
        state.doc_lines.insert(insert_pos, p)
        insert_pos += 1

    state.doc_lines.insert(insert_pos, parts[-1] + after)

    return insert_pos, len(parts[-1])


def replace_selection(text):
    pos = delete_selection()

    if pos is None:
        return None

    row, col = pos
    return insert_text(row, col, text)


# ---------------------------------------------------------
# Visual wrapping
# ---------------------------------------------------------

def build_visual_lines():
    visual = []
    width = VIEW_BOX[2]

    for doc_y, line in enumerate(state.doc_lines):
        if line == "":
            visual.append((doc_y, 0, ""))
            continue

        start = 0

        while True:
            segment = line[start:start + width]
            visual.append((doc_y, start, segment))

            if start + width >= len(line):
                break

            start += width

    if not visual:
        visual.append((0, 0, ""))

    return visual


# ---------------------------------------------------------
# Render
# ---------------------------------------------------------

def fill_view_box(view_box, visual_lines, cursor=None):
    for i in range(view_box[3]):
        move_cursor(view_box[0], view_box[1] + i)

        idx = state.view_offset + i

        if idx < len(visual_lines):
            _, _, text = visual_lines[idx]
        else:
            text = ""

        if cursor is not None and i == cursor[1]:
            cx = cursor[0]

            if cx >= len(text):
                text = text + "_"
            else:
                text = text[:cx] + "_" + text[cx:]

        print(fill(text, view_box[2]), end="")

    sys.stdout.flush()


# ---------------------------------------------------------
# Status bar
# ---------------------------------------------------------

def draw_status(doc_y, real_x, ch, path):
    y = VIEW_BOX[1] + VIEW_BOX[3]
    move_cursor(VIEW_BOX[0], y)

    if has_selection():
        (r1, c1), (r2, c2) = normalize_selection()

        status = (
            "(%d,%d,%d,%d) %s"
            % (r1 + 1, c1 + 1, r2 + 1, c2 + 1, path)
        )
    else:
        status = (
            "(%d:%d) %r %s"
            % (doc_y + 1, real_x + 1, ch, path)
        )

    print(fill(status, VIEW_BOX[2]), end="")
    sys.stdout.flush()


# ---------------------------------------------------------
# Position helpers
# ---------------------------------------------------------

def document_to_visual(doc_y, real_x, visual):
    """
    Convert a document position to a visual-line position.

    A cursor at the end of a wrapped segment belongs to the next
    segment when one exists.
    """
    last_match = 0

    for i, (dy, start, seg) in enumerate(visual):
        if dy != doc_y:
            continue

        end = start + len(seg)
        last_match = i

        if start <= real_x < end:
            return i

        if real_x == end:
            if end < len(state.doc_lines[doc_y]):
                continue
            return i

    return last_match


def clamp_position(doc_y, real_x):
    if not state.doc_lines:
        state.doc_lines = [""]

    if doc_y < 0:
        doc_y = 0
    elif doc_y >= len(state.doc_lines):
        doc_y = len(state.doc_lines) - 1

    line_length = len(state.doc_lines[doc_y])

    if real_x < 0:
        real_x = 0
    elif real_x > line_length:
        real_x = line_length

    return doc_y, real_x


# ---------------------------------------------------------
# Main editor
# ---------------------------------------------------------

def main(path):
    clear()

    if path is not None:
        state.file_path = path
        load_file(state.file_path)
    else:
        state.file_path = "untitled.txt"

    prev = None
    edit_mode = False

    # Document cursor is kept explicitly instead of deriving it
    # from the visual cursor after every operation.
    doc_y = 0
    real_x = 0

    while True:
        key = get_key()

        if key == "NONE":
            continue

        if not edit_mode and DEBUG:
            print("key=", repr(key))

        # -------------------------------------------------
        # Exit
        # -------------------------------------------------

        if key == "CTRL_Q" and prev == "CTRL_Q":
            clear()
            break

        # -------------------------------------------------
        # Clear
        # -------------------------------------------------

        if key == "CTRL_W":
            clear()
            prev = key
            continue

        # -------------------------------------------------
        # Save
        # -------------------------------------------------

        if key == "CTRL_S":
            save_file(state.file_path)
            prev = key
            continue

        # -------------------------------------------------
        # Enter edit mode
        # -------------------------------------------------

        if key == "CTRL_P":
            edit_mode = True
            state.view_offset = 0
            doc_y = 0
            real_x = 0
            clear()

            prev = key
            continue

        if not edit_mode:
            prev = key
            continue

        # -------------------------------------------------
        # Selection state
        # -------------------------------------------------

        shift_move = key in (
            "SHIFT+LEFT",
            "SHIFT+RIGHT",
            "SHIFT+UP",
            "SHIFT+DOWN",
        )

        if shift_move:
            if not state.selection_in_progress:
                begin_selection(doc_y, real_x)
        elif state.selection_in_progress:
            finalize_selection()

        # -------------------------------------------------
        # Selection operations
        # -------------------------------------------------

        handled = False

        if has_selection():
            if key == "CTRL_C":
                copy_to_clipboard(get_selected_text())
                prev = key
                continue

            elif key == "CTRL_X":
                copy_to_clipboard(get_selected_text())
                pos = delete_selection()

                if pos is not None:
                    doc_y, real_x = pos

                handled = True

            elif key in ("DELETE", "BACKSPACE"):
                pos = delete_selection()

                if pos is not None:
                    doc_y, real_x = pos

                handled = True

            elif key == "CTRL_V":
                text = paste_from_clipboard()
                pos = replace_selection(text)

                if pos is not None:
                    doc_y, real_x = pos

                handled = True

            elif key == "TAB":
                r = normalize_selection()

                if r is not None:
                    (r1, c1), (r2, c2) = r

                    for y in range(r1, r2 + 1):
                        state.doc_lines[y] = "  " + state.doc_lines[y]

                    state.selection_anchor = (
                        state.selection_anchor[0],
                        state.selection_anchor[1] + 2,
                    )

                    state.selection_end = (
                        state.selection_end[0],
                        state.selection_end[1] + 2,
                    )

                    real_x += 2

                handled = True

            elif key == "SHIFT+TAB":
                r = normalize_selection()

                if r is not None:
                    (r1, c1), (r2, c2) = r

                    for y in range(r1, r2 + 1):
                        line = state.doc_lines[y]

                        if line.startswith("  "):
                            state.doc_lines[y] = line[2:]
                        elif line.startswith(" "):
                            state.doc_lines[y] = line[1:]

                    state.selection_anchor = (
                        state.selection_anchor[0],
                        max(0, state.selection_anchor[1] - 2),
                    )

                    state.selection_end = (
                        state.selection_end[0],
                        max(0, state.selection_end[1] - 2),
                    )

                    real_x = max(0, real_x - 2)

                handled = True

            elif len(key) == 1:
                pos = replace_selection(key)

                if pos is not None:
                    doc_y, real_x = pos

                handled = True

            elif not shift_move:
                clear_selection()

        # -------------------------------------------------
        # Input operations
        # -------------------------------------------------

        if not handled:
            if key == "CTRL_V":
                text = paste_from_clipboard()

                if has_selection():
                    pos = replace_selection(text)

                    if pos is not None:
                        doc_y, real_x = pos
                else:
                    doc_y, real_x = insert_text(
                        doc_y, real_x, text
                    )

            elif key == "CTRL_A":
                if state.doc_lines:
                    state.selection_active = True
                    state.selection_anchor = (0, 0)

                    last_y = len(state.doc_lines) - 1
                    state.selection_end = (
                        last_y,
                        len(state.doc_lines[last_y]),
                    )

                    state.selection_in_progress = False

            elif key == "TAB":
                doc_y, real_x = insert_text(
                    doc_y, real_x, "  "
                )

            elif len(key) == 1:
                line = state.doc_lines[doc_y]
                state.doc_lines[doc_y] = (
                    line[:real_x] + key + line[real_x:]
                )
                real_x += 1

            elif key == "ENTER":
                line = state.doc_lines[doc_y]
                new_line = line[real_x:]

                state.doc_lines[doc_y] = line[:real_x]
                state.doc_lines.insert(doc_y + 1, new_line)

                doc_y += 1
                real_x = 0

            elif key == "BACKSPACE":
                line = state.doc_lines[doc_y]

                if real_x > 0:
                    state.doc_lines[doc_y] = (
                        line[:real_x - 1] + line[real_x:]
                    )
                    real_x -= 1

                elif doc_y > 0:
                    prev_line = state.doc_lines[doc_y - 1]
                    real_x = len(prev_line)

                    state.doc_lines[doc_y - 1] = (
                        prev_line + line
                    )
                    state.doc_lines.pop(doc_y)
                    doc_y -= 1

            elif key == "DELETE":
                line = state.doc_lines[doc_y]

                if real_x < len(line):
                    state.doc_lines[doc_y] = (
                        line[:real_x] + line[real_x + 1:]
                    )

                elif doc_y < len(state.doc_lines) - 1:
                    state.doc_lines[doc_y] += (
                        state.doc_lines[doc_y + 1]
                    )
                    state.doc_lines.pop(doc_y + 1)

        # -------------------------------------------------
        # Navigation
        # -------------------------------------------------

        # Refresh the current line after any editing operation.
        line = state.doc_lines[doc_y]

        if key in ("LEFT", "SHIFT+LEFT"):
            if real_x > 0:
                real_x -= 1
            elif doc_y > 0:
                doc_y -= 1
                real_x = len(state.doc_lines[doc_y])

        elif key in ("RIGHT", "SHIFT+RIGHT"):
            line = state.doc_lines[doc_y]

            if real_x < len(line):
                real_x += 1
            elif doc_y < len(state.doc_lines) - 1:
                doc_y += 1
                real_x = 0

        elif key in ("UP", "SHIFT+UP"):
            if doc_y > 0:
                doc_y -= 1
                real_x = min(
                    real_x,
                    len(state.doc_lines[doc_y]),
                )

        elif key in ("DOWN", "SHIFT+DOWN"):
            if doc_y < len(state.doc_lines) - 1:
                doc_y += 1
                real_x = min(
                    real_x,
                    len(state.doc_lines[doc_y]),
                )

        doc_y, real_x = clamp_position(doc_y, real_x)

        if shift_move:
            update_selection(doc_y, real_x)

        # -------------------------------------------------
        # Map document position to visual position
        # -------------------------------------------------

        visual = build_visual_lines()

        new_vis_idx = document_to_visual(
            doc_y, real_x, visual
        )

        _, start, seg = visual[new_vis_idx]

        cx = real_x - start

        if cx < 0:
            cx = 0

        if cx > len(seg):
            cx = len(seg)

        cy = new_vis_idx - state.view_offset

        # -------------------------------------------------
        # Scrolling
        # -------------------------------------------------

        if cy < 0:
            state.view_offset = new_vis_idx
            cy = 0

        elif cy >= VIEW_BOX[3]:
            state.view_offset = (
                new_vis_idx - VIEW_BOX[3] + 1
            )
            cy = VIEW_BOX[3] - 1

        max_offset = max(0, len(visual) - VIEW_BOX[3])

        if state.view_offset > max_offset:
            state.view_offset = max_offset

        # -------------------------------------------------
        # Render
        # -------------------------------------------------

        fill_view_box(
            VIEW_BOX,
            visual,
            cursor=(cx, cy),
        )

        ch = ""

        if doc_y < len(state.doc_lines):
            if real_x < len(state.doc_lines[doc_y]):
                ch = state.doc_lines[doc_y][real_x]

        draw_status(
            doc_y,
            real_x,
            ch,
            state.file_path,
        )

        prev = key


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        path = None

    main(path)
