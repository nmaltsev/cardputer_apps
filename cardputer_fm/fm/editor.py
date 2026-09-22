import sys
import os
__version__ = '3.2026.09.22'

# ============================================================
# Immutable display geometry
# ============================================================
view_box1 = (0, 0, 40, 10)  # x,y,w,h (immutable!)
SCREEN_WIDTH = view_box1[2]
SCREEN_HEIGHT = view_box1[3]
HEADER_Y = 0
CONTENT_Y = 1
CONTENT_HEIGHT = view_box1[3] - 2
FOOTER_Y = view_box1[3] - 1
# Exactly one screen of editable data.
CHUNK_SIZE = view_box1[2] * (view_box1[3] - 2)

# ============================================================
# Terminal
# ============================================================
def clear():
    sys.stdout.write("\x1b[2J\x1b[H")

def move_cursor(x, y):
    sys.stdout.write(f"\x1b[{y + 1};{x + 1}H")

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
            return "CTRL_" + chr(code + 64)
        return ch
    except Exception:
        return None

def read_escape_sequence():
    """
    ANSI keyboard sequences.
    ESC [ A = UP
    ESC [ B = DOWN
    ESC [ C = RIGHT
    ESC [ D = LEFT
    ESC [ 3 ~ = DELETE
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
def load_file_bytes(path, offset, length):
    """
    Read only `length` bytes starting at `offset`.
    """
    try:
        with open(path, "rb") as f:
            f.seek(offset)
            return f.read(length)
    except OSError:
        return None

def get_file_size(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            return f.tell()
    except OSError:
        return 0

def file_exists(path):
    """
    CircuitPython-compatible existence check.
    Does not use os.path.exists().
    """
    try:
        with open(path, "rb"):
            return True
    except OSError:
        return False

def copy_bytes(src, dst, count):
    """
    Copy at most `count` bytes.
    The whole file is never loaded into RAM.
    """
    remaining = count
    while remaining > 0:
        size = 512
        if remaining < size:
            size = remaining
        data = src.read(size)
        if not data:
            break
        dst.write(data)
        remaining -= len(data)

def replace_file_chunk(path, offset, old_length, new_data):
    """
    Replace exactly `old_length` bytes at `offset`
    with `new_data`.
    Example:
        original:
            [prefix][240-byte chunk][suffix]
        after editing chunk to 270 bytes:
            [prefix][270-byte chunk][suffix]
    The suffix is shifted by +30 bytes.
    The whole file is never loaded into memory.
    """
    temp_path = path + ".tmp"
    try:
        # Remove an old temporary file if one exists.
        try:
            os.remove(temp_path)
        except OSError:
            pass
        with open(temp_path, "w+b") as dst:
            # ------------------------------------------------
            # 1. Copy prefix
            # ------------------------------------------------
            if file_exists(path):
                with open(path, "rb") as src:
                    copy_bytes(
                        src,
                        dst,
                        offset
                    )
                    # ----------------------------------------
                    # 2. Write replacement chunk
                    # ----------------------------------------
                    dst.write(new_data)
                    # ----------------------------------------
                    # 3. Skip old chunk
                    # ----------------------------------------
                    src.seek(
                        offset + old_length
                    )
                    # ----------------------------------------
                    # 4. Copy suffix
                    # ----------------------------------------
                    while True:
                        data = src.read(512)
                        if not data:
                            break
                        dst.write(data)
            else:
                # New file.
                dst.write(new_data)
        # Replace original with temporary file.
        try:
            os.remove(path)
        except OSError:
            pass
        os.rename(temp_path, path)
        return True
    except OSError:
        try:
            os.remove(temp_path)
        except OSError:
            pass
        return False

# ============================================================
# String helpers
# ============================================================
def pad_right(text, width):
    if len(text) >= width:
        return text[:width]
    return text + (" " * (width - len(text)))

def safe_char(ch):
    if ch == "\t":
        return " "
    if ch == "\r":
        return " "
    if ch == "\n":
        return " "
    if ord(ch) < 32:
        return " "
    return ch

# ============================================================
# Editor
# ============================================================
class TextEditor:
    def __init__(self, filename):
        self.filename = filename
        # ----------------------------------------------------
        # File/chunk state
        # ----------------------------------------------------
        # Current chunk offset in bytes.
        self.offset = 0
        # Number of ORIGINAL bytes loaded for this chunk.
        self.original_length = 0
        # Original bytes are retained only for this chunk.
        self.original_bytes = b""
        # Editable text.
        self.text = ""
        # ----------------------------------------------------
        # Cursor
        # ----------------------------------------------------
        # Character index in self.text.
        self.cursor = 0
        # Desired horizontal position used by UP/DOWN.
        self.preferred_col = 0
        # First visual line shown in the content area.
        self.scroll_line = 0
        # ----------------------------------------------------
        # State
        # ----------------------------------------------------
        self.changed = False
        self.status = ""
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
            # A non-existing file at offset 0 is treated as
            # an empty file.
            if offset == 0 and not file_exists(self.filename):
                data = b""
            else:
                self.status = "READ ERROR"
                return False
        self.original_bytes = data
        self.original_length = len(data)
        try:
            self.text = data.decode("utf-8")
        except UnicodeDecodeError:
            # Keep the editor usable for files containing
            # invalid/incomplete UTF-8.
            self.text = data.decode(
                "utf-8",
                "replace"
            )
        self.offset = offset
        self.cursor = 0
        self.preferred_col = 0
        self.scroll_line = 0
        self.changed = False
        self.status = ""
        return True

    def reload_chunk(self):
        return self.load_chunk(self.offset)

    def save_chunk(self):
        """
        Replace the ORIGINAL chunk with the edited chunk.
        If original chunk = 240 bytes
        and edited chunk = 270 bytes:
            file[240 bytes at offset] is removed
            270 new bytes are inserted
        The next chunk therefore starts at:
            offset + 270
        """
        # If nothing changed, do not rewrite the file.
        if not self.changed:
            self.status = "UNCHANGED"
            return True
        try:
            new_data = self.text.encode("utf-8")
        except UnicodeEncodeError:
            self.status = "ENCODE ERROR"
            return False
        success = replace_file_chunk(
            self.filename,
            self.offset,
            self.original_length,
            new_data
        )
        if not success:
            self.status = "WRITE ERROR"
            return False
        # The edited chunk has now become the current
        # on-disk chunk.
        self.original_bytes = new_data
        self.original_length = len(new_data)
        self.changed = False
        self.status = "SAVED"
        return True

    def save_and_reload(self):
        """
        CTRL_S:
            1. Replace current chunk.
            2. Read the newly saved chunk again.
        The offset remains unchanged.
        """
        if not self.save_chunk():
            return False
        return self.load_chunk(self.offset)

    # ========================================================
    # Chunk navigation
    # ========================================================
    def next_chunk(self):
        """
        CTRL_F.
        After saving, the next chunk begins immediately after
        the NEW chunk, not after the original chunk.
        Example:
            current offset = 480
            original      = 240 bytes
            edited        = 270 bytes
            next offset = 480 + 270 = 750
        Then 240 bytes are read from offset 750.
        """
        if self.changed:
            if not self.save_chunk():
                return False
        # IMPORTANT:
        # After saving, original_length is the NEW chunk size.
        new_offset = self.offset + self.original_length
        file_size = get_file_size(self.filename)
        if new_offset >= file_size:
            self.status = "EOF"
            return False
        return self.load_chunk(new_offset)

    def previous_chunk(self):
        """
        CTRL_B.
        Previous chunk navigation is based on the fixed
        CHUNK_SIZE.
        This is necessary because the previous chunk is
        determined by the current file layout.
        The current edited chunk is saved first.
        """
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
    # Visual line generation
    # ========================================================
    def build_visual_lines(self):
        """
        Convert logical text into screen-width visual lines.
        A visual line contains:
            start
            end
            text
        `start` and `end` are character indexes in self.text.
        Newlines create real visual lines.
        Long logical lines are wrapped at SCREEN_WIDTH.
        """
        lines = []
        text_length = len(self.text)
        # Empty document.
        if text_length == 0:
            lines.append({
                "start": 0,
                "end": 0,
                "text": ""
            })
            return lines
        start = 0
        i = 0
        column = 0
        while i < text_length:
            ch = self.text[i]
            # ------------------------------------------------
            # Explicit newline
            # ------------------------------------------------
            if ch == "\n":
                lines.append({
                    "start": start,
                    "end": i,
                    "text": self.text[start:i]
                })
                i += 1
                start = i
                column = 0
                continue
            # ------------------------------------------------
            # Width reached
            # ------------------------------------------------
            if column >= SCREEN_WIDTH:
                lines.append({
                    "start": start,
                    "end": i,
                    "text": self.text[start:i]
                })
                start = i
                column = 0
            column += 1
            i += 1
        # ----------------------------------------------------
        # Remaining text
        # ----------------------------------------------------
        lines.append({
            "start": start,
            "end": text_length,
            "text": self.text[start:text_length]
        })
        return lines

    def get_cursor_visual_position(self):
        """
        Return:
            visual_line
            visual_column
        Cursor means INSERTION POINT.
        If cursor == 0:
            _Hello
        If cursor == 5:
            Hello_
        If cursor == len(text):
            Hello_
        """
        lines = self.build_visual_lines()
        cursor = self.cursor
        # Prefer the line whose start is <= cursor and whose
        # end is >= cursor.
        #
        # At an exact wrapping boundary, the cursor belongs
        # to the NEXT visual line. This prevents the cursor
        # from jumping back to column 0 incorrectly.
        for index in range(len(lines)):
            line = lines[index]
            start = line["start"]
            end = line["end"]
            if cursor < start:
                continue
            if cursor < end:
                return (
                    index,
                    cursor - start
                )
            # Cursor at end of line.
            if cursor == end:
                # If another visual line starts at exactly
                # this position, this is the insertion point
                # at the beginning of the next line.
                if index + 1 < len(lines):
                    next_line = lines[index + 1]
                    if next_line["start"] == cursor:
                        return (
                            index + 1,
                            0
                        )
                return (
                    index,
                    end - start
                )
        last = lines[-1]
        return (
            len(lines) - 1,
            cursor - last["start"]
        )

    def get_cursor_character(self):
        """
        Return the character under the insertion cursor.
        This character is NOT replaced by the cursor on the
        footer. The content area displays '_'.
        Newline / tab are represented as spaces.
        """
        if self.cursor >= len(self.text):
            return " "
        ch = self.text[self.cursor]
        if ch == "\n":
            return "\\n"
        if ch == "\r":
            return "\\r"
        if ch == "\t":
            return "\\t"
        if ord(ch) < 32:
            return " "
        return ch

    # ========================================================
    # Cursor movement
    # ========================================================
    def move_left(self):
        if self.cursor > 0:
            self.cursor -= 1
            line, col = (
                self.get_cursor_visual_position()
            )
            self.preferred_col = col
            self.ensure_cursor_visible()

    def move_right(self):
        if self.cursor < len(self.text):
            self.cursor += 1
            line, col = (
                self.get_cursor_visual_position()
            )
            self.preferred_col = col
            self.ensure_cursor_visible()

    def move_up(self):
        lines = self.build_visual_lines()
        current_line, current_col = (
            self.get_cursor_visual_position()
        )
        if current_line <= 0:
            return
        target_line = current_line - 1
        target = lines[target_line]
        target_length = (
            target["end"] - target["start"]
        )
        target_col = self.preferred_col
        if target_col > target_length:
            target_col = target_length
        self.cursor = (
            target["start"] + target_col
        )
        self.ensure_cursor_visible()

    def move_down(self):
        lines = self.build_visual_lines()
        current_line, current_col = (
            self.get_cursor_visual_position()
        )
        # CRITICAL:
        # Never create a cursor position on a line that
        # doesn't exist.
        if current_line >= len(lines) - 1:
            return
        target_line = current_line + 1
        target = lines[target_line]
        target_length = (
            target["end"] - target["start"]
        )
        target_col = self.preferred_col
        if target_col > target_length:
            target_col = target_length
        self.cursor = (
            target["start"] + target_col
        )
        self.ensure_cursor_visible()

    # ========================================================
    # Scrolling
    # ========================================================
    def ensure_cursor_visible(self):
        cursor_line, cursor_col = (
            self.get_cursor_visual_position()
        )
        # Scroll down.
        if cursor_line >= (
            self.scroll_line + CONTENT_HEIGHT
        ):
            self.scroll_line = (
                cursor_line - CONTENT_HEIGHT + 1
            )
        # Scroll up.
        if cursor_line < self.scroll_line:
            self.scroll_line = cursor_line
        if self.scroll_line < 0:
            self.scroll_line = 0

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
        # Maintain normal cursor-column behavior.
        line, col = (
            self.get_cursor_visual_position()
        )
        self.preferred_col = col
        self.ensure_cursor_visible()

    def backspace(self):
        if self.cursor <= 0:
            return
        self.text = (
            self.text[:self.cursor - 1]
            + self.text[self.cursor:]
        )
        self.cursor -= 1
        self.changed = True
        line, col = (
            self.get_cursor_visual_position()
        )
        self.preferred_col = col
        self.ensure_cursor_visible()

    def delete(self):
        if self.cursor >= len(self.text):
            return
        self.text = (
            self.text[:self.cursor]
            + self.text[self.cursor + 1:]
        )
        self.changed = True
        self.ensure_cursor_visible()

    def enter(self):
        self.insert_text("\n")

    def tab(self):
        self.insert_text("    ")

    # ========================================================
    # Display
    # ========================================================
    def get_header(self):
        if self.changed:
            prefix = "~"
        else:
            prefix = " "
        return pad_right(
            prefix + self.filename,
            SCREEN_WIDTH
        )

    def get_footer(self):
        line, col = (
            self.get_cursor_visual_position()
        )
        char = self.get_cursor_character()
        # 1-based coordinates.
        line += 1
        col += 1
        # The footer is intentionally compact enough to fit
        # the immutable 40-character screen.
        #
        # Example:
        # Ln:3 Col:10 Len:120 Offset:1024 Ch:x
        footer = (
            "Ln:" + str(line)
            + " Col:" + str(col)
            + " Len:" + str(len(self.text))
            + " Offset:" + str(self.offset)
            + " Ch:" + char
        )
        return pad_right(
            footer,
            SCREEN_WIDTH - 1
        )

    def render(self):
        lines = self.build_visual_lines()
        cursor_line, cursor_col = (
            self.get_cursor_visual_position()
        )
        # ----------------------------------------------------
        # Header
        # ----------------------------------------------------
        move_cursor(0, HEADER_Y)
        sys.stdout.write(
            self.get_header()
        )
        # ----------------------------------------------------
        # Content
        # ----------------------------------------------------
        for screen_line in range(CONTENT_HEIGHT):
            move_cursor(
                0,
                CONTENT_Y + screen_line
            )
            visual_line = (
                self.scroll_line + screen_line
            )
            if visual_line >= len(lines):
                sys.stdout.write(
                    " " * SCREEN_WIDTH
                )
                continue
            text = lines[visual_line]["text"]
            display = ""
            for ch in text:
                display += safe_char(ch)
            display = pad_right(
                display,
                SCREEN_WIDTH
            )
            # ------------------------------------------------
            # Draw insertion cursor.
            #
            # The '_' REPLACES the current display position.
            # The actual character is shown in the footer.
            # ------------------------------------------------
            if visual_line == cursor_line:
                if cursor_col < SCREEN_WIDTH:
                    display = (
                        display[:cursor_col]
                        + "_"
                        + display[cursor_col + 1:]
                    )
                else:
                    # Cursor at the exact right edge.
                    #
                    # There is no character position at x=40,
                    # so display the cursor at x=39.
                    display = (
                        display[:SCREEN_WIDTH - 1]
                        + "_"
                    )
            sys.stdout.write(
                display[:SCREEN_WIDTH]
            )
        # ----------------------------------------------------
        # Footer
        # ----------------------------------------------------
        move_cursor(
            0,
            FOOTER_Y
        )
        sys.stdout.write(
            self.get_footer()
        )

    # ========================================================
    # Keyboard
    # ========================================================
    def handle_key(self, key):
        if key is None:
            return True
        # ----------------------------------------------------
        # CTRL_Q
        #
        # Exit WITHOUT saving.
        # ----------------------------------------------------
        if key == "CTRL_Q":
            return False
        # ----------------------------------------------------
        # CTRL_B
        #
        # Save current chunk and go backward.
        # ----------------------------------------------------
        if key == "CTRL_B":
            self.previous_chunk()
            return True
        # ----------------------------------------------------
        # CTRL_F
        #
        # Save current chunk and go forward.
        # ----------------------------------------------------
        if key == "CTRL_F":
            self.next_chunk()
            return True
        # ----------------------------------------------------
        # CTRL_L
        #
        # Throw away current edits and reload from disk.
        # ----------------------------------------------------
        if key == "CTRL_L":
            self.reload_chunk()
            return True
        # ----------------------------------------------------
        # CTRL_S
        #
        # Replace chunk and reload it.
        # ----------------------------------------------------
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
        # ESC
        # ----------------------------------------------------
        if key == "ESC":
            return False
        # ----------------------------------------------------
        # Printable characters
        # ----------------------------------------------------
        if isinstance(key, str):
            if len(key) == 1:
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
        move_cursor(
            0,
            FOOTER_Y
        )
        sys.stdout.write(
            pad_right(
                "ERROR: " + str(exc),
                SCREEN_WIDTH
            )
        )
    finally:
        show_cursor()
        move_cursor(
            0,
            SCREEN_HEIGHT
        )
        sys.stdout.write("\n")

# ============================================================
# Entry point
# ============================================================
if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main("data.txt")