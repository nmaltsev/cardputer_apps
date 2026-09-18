import sys
import os

# ============================================================
# Configuration
# ============================================================
SCREEN_WIDTH = 40
SCREEN_HEIGHT = 8
CHUNK_SIZE = 40 * 8
HEADER_Y = 0
CONTENT_Y = 1
CONTENT_HEIGHT = 6
FOOTER_Y = 7
view_box1 = (0, 0, 40, 8)  # x,y,w,h (immutable!)

# ============================================================
# Terminal control
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
    "\x1b": "ESC",
}

def get_key():
    try:
        ch = sys.stdin.read(1)
        if ch in CTRL_KEYS:
            return CTRL_KEYS[ch]
        code = ord(ch)
        if 1 <= code <= 26:
            return f"CTRL_{chr(code + 64)}"
        return ch
    except Exception as exc:
        print("get_key error: ", exc)
        return None

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
        # Decode incomplete or invalid UTF-8 safely.
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
# String helpers
# ============================================================
def pad_right(text, width):
    """
    Replacement for str.ljust().
    """
    if len(text) >= width:
        return text[:width]
    return text + (" " * (width - len(text)))

def safe_char(ch):
    """
    Ensure the character can be displayed in the terminal.
    """
    if ch == "\t":
        return " "
    if ch == "\r":
        return " "
    if ord(ch) < 32:
        return " "
    return ch

def split_lines(text):
    """
    Split text into logical lines.
    Does not use str.splitlines() so that the behavior
    remains predictable on CircuitPython.
    """
    lines = []
    current = ""
    for ch in text:
        if ch == "\n":
            lines.append(current)
            current = ""
        elif ch == "\r":
            pass
        else:
            current += ch
    lines.append(current)
    return lines

# ============================================================
# Editor class
# ============================================================
class TextEditor:
    def __init__(self, filename):
        self.filename = filename
        # Internal file offset in bytes.
        self.offset = 0
        # Offset of the next chunk.
        self.next_offset = 0
        # Original bytes loaded from disk.
        self.original_bytes = b""
        # Current editable text.
        self.text = ""
        # Cursor position as character index.
        self.cursor = 0
        # Vertical and horizontal cursor position.
        self.cursor_line = 0
        self.cursor_col = 0
        # Horizontal display scroll.
        self.scroll_x = 0
        # Chunk changed flag.
        self.changed = False
        # File exists flag.
        self.file_exists = False
        # Status message.
        self.status = ""
        # Load initial chunk.
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
        self.changed = False
        self.status = ""
        self.update_cursor_position()
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
        # Save changes before navigating.
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
    # Cursor management
    # ========================================================
    def update_cursor_position(self):
        before = self.text[:self.cursor]
        lines = before.split("\n")
        self.cursor_line = len(lines) - 1
        self.cursor_col = len(lines[-1])

    def set_cursor(self, position):
        if position < 0:
            position = 0
        if position > len(self.text):
            position = len(self.text)
        self.cursor = position
        self.update_cursor_position()

    def move_left(self):
        if self.cursor > 0:
            self.cursor -= 1
            self.update_cursor_position()

    def move_right(self):
        if self.cursor < len(self.text):
            self.cursor += 1
            self.update_cursor_position()

    def move_up(self):
        self.update_cursor_position()
        current_line = self.cursor_line
        current_col = self.cursor_col
        if current_line <= 0:
            return
        lines = split_lines(self.text)
        target_line = current_line - 1
        if target_line >= len(lines):
            return
        target_col = current_col
        if target_col > len(lines[target_line]):
            target_col = len(lines[target_line])
        position = 0
        for i in range(target_line):
            position += len(lines[i]) + 1
        position += target_col
        self.set_cursor(position)

    def move_down(self):
        self.update_cursor_position()
        current_line = self.cursor_line
        current_col = self.cursor_col
        lines = split_lines(self.text)
        target_line = current_line + 1
        if target_line >= len(lines):
            return
        target_col = current_col
        if target_col > len(lines[target_line]):
            target_col = len(lines[target_line])
        position = 0
        for i in range(target_line):
            position += len(lines[i]) + 1
        position += target_col
        self.set_cursor(position)

    # ========================================================
    # Editing
    # ========================================================
    def insert_text(self, text):
        self.text = (
            self.text[:self.cursor]
            + text
            + self.text[self.cursor:]
        )
        self.cursor += len(text)
        self.changed = True
        self.update_cursor_position()

    def backspace(self):
        if self.cursor <= 0:
            return
        self.text = (
            self.text[:self.cursor - 1]
            + self.text[self.cursor:]
        )
        self.cursor -= 1
        self.changed = True
        self.update_cursor_position()

    def delete(self):
        if self.cursor >= len(self.text):
            return
        self.text = (
            self.text[:self.cursor]
            + self.text[self.cursor + 1:]
        )
        self.changed = True
        self.update_cursor_position()

    def enter(self):
        self.insert_text("\n")

    def tab(self):
        self.insert_text("    ")

    # ========================================================
    # Display
    # ========================================================
    def get_header(self):
        prefix = "~" if self.changed else " "
        name = self.filename
        header = prefix + name
        return pad_right(header, SCREEN_WIDTH)

    def get_footer(self):
        self.update_cursor_position()
        line = self.cursor_line + 1
        col = self.cursor_col + 1
        length = len(self.text)
        footer = (
            "Ln:" + str(line)
            + " Col:" + str(col)
            + " Len:" + str(length)
            + " Offset:" + str(self.offset)
        )
        return pad_right(footer, SCREEN_WIDTH)

    def get_display_lines(self):
        """
        Returns exactly six display lines.
        Lines are wrapped to screen width.
        """
        lines = []
        current = ""
        for ch in self.text:
            if ch == "\n":
                lines.append(current)
                current = ""
            else:
                current += safe_char(ch)
                if len(current) >= SCREEN_WIDTH:
                    lines.append(current[:SCREEN_WIDTH])
                    current = current[SCREEN_WIDTH:]

        lines.append(current)
        # Ensure at least six lines.
        while len(lines) < CONTENT_HEIGHT:
            lines.append("")
        # Limit to visible area.
        lines = lines[:CONTENT_HEIGHT]
        # Horizontal cursor positioning.
        return lines

    def get_cursor_screen_position(self):
        """
        Determine the cursor position on screen.
        The cursor is represented by '_' and the
        character at the cursor is placed to its right.
        """
        self.update_cursor_position()
        line = self.cursor_line
        col = self.cursor_col
        # Wrap long lines.
        if col >= SCREEN_WIDTH:
            extra_lines = col // SCREEN_WIDTH
            line += extra_lines
            col = col % SCREEN_WIDTH
        return col, line

    def render(self):
        move_cursor(0, HEADER_Y)
        sys.stdout.write(self.get_header())
        lines = self.get_display_lines()
        for i in range(CONTENT_HEIGHT):
            move_cursor(0, CONTENT_Y + i)
            line = lines[i]
            line = pad_right(line, SCREEN_WIDTH)
            sys.stdout.write(line[:SCREEN_WIDTH])
        move_cursor(0, FOOTER_Y)
        sys.stdout.write(self.get_footer())
        # Draw cursor indicator.
        x, y = self.get_cursor_screen_position()
        if y < CONTENT_HEIGHT:
            screen_y = CONTENT_Y + y
            screen_x = x
            if screen_x >= SCREEN_WIDTH:
                screen_x = SCREEN_WIDTH - 1
            move_cursor(screen_x, screen_y)
            sys.stdout.write("_")
        move_cursor(0, FOOTER_Y)
        sys.stdout.write(self.status)
        sys.stdout.write(" " * (
            SCREEN_WIDTH - len(self.status)
        ))
        move_cursor(0, FOOTER_Y)
        sys.stdout.write(self.get_footer())

    # ========================================================
    # Key handling
    # ========================================================
    def handle_key(self, key):
        if key is None:
            return True
        # ----------------------------------------------------
        # Control keys
        # ----------------------------------------------------
        if key == "CTRL_B":
            self.previous_chunk()
            return True

        if key == "CTRL_F":
            self.next_chunk()
            return True

        if key == "CTRL_L":
            self.reload_chunk()
            return True

        if key == "CTRL_S":
            self.save_and_reload()
            return True

        # ----------------------------------------------------
        # Navigation
        # ----------------------------------------------------
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

        # ----------------------------------------------------
        # Editing
        # ----------------------------------------------------
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

        # ----------------------------------------------------
        # Escape
        # ----------------------------------------------------
        if key == "ESC":
            return False

        # ----------------------------------------------------
        # Printable characters
        # ----------------------------------------------------
        if isinstance(key, str) and len(key) == 1:
            if ord(key) >= 32:
                self.insert_text(key)
                return True

        return True

# ============================================================
# Arrow key parser
# ============================================================
def read_arrow_key():
    """
    Parse ANSI escape sequences.
    Arrow keys:
        ESC [ A = UP
        ESC [ B = DOWN
        ESC [ C = RIGHT
        ESC [ D = LEFT
    Delete:
        ESC [ 3 ~
    """
    ch = sys.stdin.read(1)
    if ch != "[":
        return "ESC"
    ch2 = sys.stdin.read(1)
    if ch2 == "A":
        return "UP"
    if ch2 == "B":
        return "DOWN"
    if ch2 == "C":
        return "RIGHT"
    if ch2 == "D":
        return "LEFT"
    if ch2 == "3":
        ch3 = sys.stdin.read(1)
        if ch3 == "~":
            return "DELETE"
    return "ESC"

def get_key_extended():
    try:
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            return read_arrow_key()
        if ch in CTRL_KEYS:
            return CTRL_KEYS[ch]
        code = ord(ch)
        if 1 <= code <= 26:
            return f"CTRL_{chr(code + 64)}"
        return ch
    except Exception as exc:
        print("get_key error:", exc)
        return None

# ============================================================
# Main function
# ============================================================
def main(filename):
    editor = TextEditor(filename)
    clear()
    hide_cursor()
    try:
        while True:
            editor.render()
            key = get_key_extended()
            if key is None:
                continue
            should_continue = editor.handle_key(key)
            if not should_continue:
                break
    except Exception as exc:
        editor.status = "ERROR"
        move_cursor(0, FOOTER_Y)
        sys.stdout.write(
            pad_right(str(exc), SCREEN_WIDTH)
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