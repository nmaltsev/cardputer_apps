import sys
import os
__version__ = '2.2026.09.21'
# ============================================================
# Configuration
# ============================================================
view_box1 = (0, 0, 40, 8)  # x,y,w,h (immutable!)
SCREEN_WIDTH = view_box1[2]
SCREEN_HEIGHT = view_box1[3]
HEADER_Y = 0
CONTENT_Y = 1
CONTENT_HEIGHT = SCREEN_HEIGHT - 2
FOOTER_Y = SCREEN_HEIGHT - 1
CHUNK_SIZE = 40 * 8

# ============================================================
# Terminal
# ============================================================
def clear():
    sys.stdout.write("\x1b[2J\x1b[H")

def move_cursor(x, y):
    sys.stdout.write(f"\x1b[{y+1};{x+1}H")

def hide_cursor():
    sys.stdout.write("\x1b[?25l")

def show_cursor():
    sys.stdout.write("\x1b[?25h")

CTRL_KEYS = {
    "\x08": "BACKSPACE",
    "\x7f": "BACKSPACE",
    "\r": "ENTER",
    "\n": "ENTER",
    "\t": "TAB",
}

def get_key():
    try:
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            return read_escape_sequence()
        if ch in CTRL_KEYS:
            return CTRL_KEYS[ch]
        code = ord(ch)
        if 1 <= code <= 26:
            return f"CTRL_{chr(code + 64)}"
        return ch
    except Exception as exc:
        return None

def read_escape_sequence():
    """
    Parse ANSI escape sequences.
    UP       ESC [ A
    DOWN     ESC [ B
    RIGHT    ESC [ C
    LEFT     ESC [ D
    DELETE   ESC [ 3 ~
    """
    ch = sys.stdin.read(1)
    if ch != "[":
        return "ESC"
    ch = sys.stdin.read(1)
    if ch == "A":
        return "UP"
    if ch == "B":
        return "DOWN"
    if ch == "C":
        return "RIGHT"
    if ch == "D":
        return "LEFT"
    if ch == "3":
        ch = sys.stdin.read(1)
        if ch == "~":
            return "DELETE"
    return "ESC"

# ============================================================
# File operations
# ============================================================
def load_file(path, offset, length):
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            data = f.read(length)
            return data.decode("utf-8")
    except OSError:
        return None
    except UnicodeDecodeError:
        try:
            return data.decode("utf-8", "replace")
        except Exception:
            return None

def load_file_bytes(path, offset, length):
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            return f.read(length)
    except OSError:
        return None

def write_file_chunk(path, offset, data):
    try:
        try:
            f = open(path, "r+b")
        except OSError:
            f = open(path, "w+b")
        with f:
            f.seek(offset)
            f.write(data)
        return True
    except OSError:
        return False

def get_file_size(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            return f.tell()
    except OSError:
        return 0

# ============================================================
# Helpers
# ============================================================
def pad_right(text, width):
    if len(text) >= width:
        return text[:width]
    return text + (" " * (width - len(text)))

def safe_char(ch):
    if ch in ("\t", "\r"):
        return " "
    if ord(ch) < 32:
        return " "
    return ch

# ============================================================
# Text editor
# ============================================================
class TextEditor:
    def __init__(self, filename):
        self.filename = filename
        # File offset in bytes.
        self.offset = 0
        # Offset of the next chunk.
        self.next_offset = 0
        # Original bytes.
        self.original_bytes = b""
        # Editable text.
        self.text = ""
        # Cursor is a character index in self.text.
        self.cursor = 0
        # Preferred column for vertical movement.
        self.preferred_col = 0
        # Changed flag.
        self.changed = False
        # Status message.
        self.status = ""
        # Load first chunk.
        self.load_chunk(0)

    # ========================================================
    # Chunk handling
    # ========================================================
    def load_chunk(self, offset):
        data = load_file_bytes(
            self.filename,
            offset,
            CHUNK_SIZE
        )
        if data is None:
            self.original_bytes = b""
            self.text = ""
            self.offset = offset
            self.next_offset = offset
            self.cursor = 0
            self.changed = False
            self.status = "READ ERROR"
            return False
        self.original_bytes = data
        try:
            self.text = data.decode("utf-8")
        except UnicodeDecodeError:
            self.text = data.decode("utf-8", "replace")
        self.offset = offset
        self.next_offset = offset + len(data)
        self.cursor = 0
        self.preferred_col = 0
        self.changed = False
        self.status = ""
        return True

    def reload_chunk(self):
        return self.load_chunk(self.offset)

    def save_chunk(self):
        data = self.text.encode("utf-8")
        success = write_file_chunk(
            self.filename,
            self.offset,
            data
        )
        if success:
            self.original_bytes = data
            self.changed = False
            self.next_offset = self.offset + len(data)
            self.status = "SAVED"
        else:
            self.status = "WRITE ERROR"
        return success

    def save_and_reload(self):
        if not self.save_chunk():
            return False
        return self.load_chunk(self.offset)

    def next_chunk(self):
        if self.changed:
            if not self.save_chunk():
                return False
        new_offset = self.next_offset
        file_size = get_file_size(self.filename)
        if new_offset >= file_size:
            self.status = "EOF"
            return False
        return self.load_chunk(new_offset)

    def previous_chunk(self):
        if self.changed:
            if not self.save_chunk():
                return False
        if self.offset <= 0:
            self.status = "BOF"
            return False
        new_offset = self.offset - CHUNK_SIZE
        if new_offset < 0:
            new_offset = 0
        return self.load_chunk(new_offset)

    # ========================================================
    # Visual line layout
    # ========================================================
    def build_visual_lines(self):
        """
        Build visual lines according to SCREEN_WIDTH.
        Each visual line contains:
            text   : display text
            start  : starting character index
            end    : ending character index
        Cursor positions are mapped to these lines.
        """
        lines = []
        start = 0
        col = 0
        i = 0
        text_len = len(self.text)
        while i < text_len:
            ch = self.text[i]
            # Explicit newline.
            if ch == "\n":
                lines.append({
                    "text": self.text[start:i],
                    "start": start,
                    "end": i,
                    "newline": True
                })
                i += 1
                start = i
                col = 0
                continue
            # Wrap at screen width.
            if col >= SCREEN_WIDTH:
                lines.append({
                    "text": self.text[start:i],
                    "start": start,
                    "end": i,
                    "newline": False
                })
                start = i
                col = 0
            col += 1
            i += 1
        # Add remaining text.
        lines.append({
            "text": self.text[start:text_len],
            "start": start,
            "end": text_len,
            "newline": False
        })
        # Always keep at least one line.
        if len(lines) == 0:
            lines.append({
                "text": "",
                "start": 0,
                "end": 0,
                "newline": False
            })
        return lines

    def get_cursor_visual_position(self):
        """
        Returns:
            visual_line
            visual_column
        The cursor is positioned BEFORE the character
        at self.cursor.
        """
        lines = self.build_visual_lines()
        cursor = self.cursor
        for line_no, line in enumerate(lines):
            start = line["start"]
            end = line["end"]
            # Cursor is within this line.
            if start <= cursor <= end:
                col = cursor - start
                # Cursor at the end of a full wrapped line:
                # place it at the last column.
                if col > SCREEN_WIDTH:
                    col = SCREEN_WIDTH
                return line_no, col
        # Fallback to last line.
        last = lines[-1]
        return len(lines) - 1, self.cursor - last["start"]

    def get_cursor_char(self):
        """
        Character under cursor.
        If cursor is at the end of the text,
        return a space.
        """
        if self.cursor >= len(self.text):
            return " "
        ch = self.text[self.cursor]
        if ch in ("\n", "\r", "\t"):
            return " "
        return ch

    # ========================================================
    # Cursor movement
    # ========================================================
    def move_left(self):
        if self.cursor > 0:
            self.cursor -= 1
            self.preferred_col = (
                self.get_cursor_visual_position()[1]
            )

    def move_right(self):
        if self.cursor < len(self.text):
            self.cursor += 1
            self.preferred_col = (
                self.get_cursor_visual_position()[1]
            )

    def move_up(self):
        lines = self.build_visual_lines()
        current_line, current_col = (
            self.get_cursor_visual_position()
        )
        if current_line <= 0:
            return
        target_line = current_line - 1
        target = lines[target_line]
        target_col = self.preferred_col
        line_length = target["end"] - target["start"]
        if target_col > line_length:
            target_col = line_length
        self.cursor = target["start"] + target_col

    def move_down(self):
        lines = self.build_visual_lines()
        current_line, current_col = (
            self.get_cursor_visual_position()
        )
        # No next line.
        if current_line >= len(lines) - 1:
            return
        target_line = current_line + 1
        target = lines[target_line]
        target_col = self.preferred_col
        line_length = target["end"] - target["start"]
        if target_col > line_length:
            target_col = line_length
        self.cursor = target["start"] + target_col

    # ========================================================
    # Editing
    # ========================================================
    def insert_text(self, value):
        self.text = (
            self.text[:self.cursor]
            + value
            + self.text[self.cursor:]
        )
        self.cursor += len(value)
        self.changed = True
        self.preferred_col = (
            self.get_cursor_visual_position()[1]
        )

    def backspace(self):
        if self.cursor <= 0:
            return
        self.text = (
            self.text[:self.cursor - 1]
            + self.text[self.cursor:]
        )
        self.cursor -= 1
        self.changed = True

    def delete(self):
        if self.cursor >= len(self.text):
            return
        self.text = (
            self.text[:self.cursor]
            + self.text[self.cursor + 1:]
        )
        self.changed = True

    def enter(self):
        self.insert_text("\n")

    def tab(self):
        self.insert_text("    ")

    # ========================================================
    # Display
    # ========================================================
    def get_header(self):
        prefix = "~" if self.changed else " "
        return pad_right(
            prefix + self.filename,
            SCREEN_WIDTH
        )

    def get_footer(self):
        line, col = self.get_cursor_visual_position()
        # Display 1-based line and column.
        line += 1
        col += 1
        length = len(self.text)
        current_char = self.get_cursor_char()
        footer = (
            "Ln:" + str(line)
            + " Col:" + str(col)
            + " Len:" + str(length)
            + " Off:" + str(self.offset)
            + " Ch:" + current_char
        )
        return pad_right(footer, SCREEN_WIDTH)

    def render(self):
        lines = self.build_visual_lines()
        cursor_line, cursor_col = (
            self.get_cursor_visual_position()
        )
        # Header.
        move_cursor(0, HEADER_Y)
        sys.stdout.write(
            self.get_header()
        )
        # Content.
        for i in range(CONTENT_HEIGHT):
            move_cursor(0, CONTENT_Y + i)
            if i < len(lines):
                line = lines[i]
                display = ""
                for ch in line["text"]:
                    display += safe_char(ch)
                display = pad_right(
                    display,
                    SCREEN_WIDTH
                )
                # Cursor replaces the character.
                if i == cursor_line:
                    if cursor_col < SCREEN_WIDTH:
                        display = (
                            display[:cursor_col]
                            + "_"
                            + display[cursor_col + 1:]
                        )
                sys.stdout.write(
                    display[:SCREEN_WIDTH]
                )
            else:
                sys.stdout.write(
                    " " * SCREEN_WIDTH
                )
        # Footer.
        move_cursor(0, FOOTER_Y)
        sys.stdout.write(
            self.get_footer()
        )

    # ========================================================
    # Key handling
    # ========================================================
    def handle_key(self, key):
        if key is None:
            return True
        # Exit without saving.
        if key == "CTRL_Q":
            return False

        # Save and previous chunk.
        if key == "CTRL_B":
            self.previous_chunk()
            return True

        # Save and next chunk.
        if key == "CTRL_F":
            self.next_chunk()
            return True

        # Reload current chunk.
        if key == "CTRL_L":
            self.reload_chunk()
            return True

        # Save and reload.
        if key == "CTRL_S":
            self.save_and_reload()
            return True

        # Navigation.
        if key == "LEFT":
            self.move_left()
            return True

        if key == "RIGHT":
            self.move_right()
            return True

        if key == "UP":
            self.move_up()
            return True

        if key == "DOWN":
            self.move_down()
            return True

        # Editing.
        if key == "BACKSPACE":
            self.backspace()
            return True

        if key == "DELETE":
            self.delete()
            return True

        if key == "ENTER":
            self.enter()
            return True

        if key == "TAB":
            self.tab()
            return True

        # Escape.
        if key == "ESC":
            return False

        # Printable characters.
        if isinstance(key, str) and len(key) == 1:
            if ord(key) >= 32:
                self.insert_text(key)
                return True

        return True

# ============================================================
# Main
# ============================================================
def main(filename):
    editor = TextEditor(filename)
    clear()
    hide_cursor()
    try:
        while True:
            editor.render()
            key = get_key()
            if key is None:
                continue
            if not editor.handle_key(key):
                break
    except Exception as exc:
        move_cursor(0, FOOTER_Y)
        sys.stdout.write(
            pad_right(
                "ERROR: " + str(exc),
                SCREEN_WIDTH
            )
        )
    finally:
        show_cursor()
        move_cursor(0, SCREEN_HEIGHT)
        sys.stdout.write("\n")

# ============================================================
# Entry point
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main("data.txt")