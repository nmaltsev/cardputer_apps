import sys
import os

# ============================================================
# Terminal helpers (CircuitPython compatible)
# ============================================================

def clear():
    sys.stdout.write("\x1b[2J\x1b[H")

def move_cursor(x, y):
    sys.stdout.write(f"\x1b[{y+1};{x+1}H")

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
# File I/O helpers
# ============================================================

def load_file(path, offset, length):
    try:
        with open(path, 'rb') as f:
            f.seek(offset)
            return f.read(length).decode('utf-8')
    except OSError:
        return None

def write_file_chunk(path, offset, data):
    try:
        try:
            f = open(path, 'r+b')
        except OSError:
            f = open(path, 'w+b')
        with f:
            f.seek(offset)
            f.write(data.encode('utf-8') if isinstance(data, str) else data)
        return True
    except OSError:
        return False

# ============================================================
# Constants
# ============================================================

CHUNK_W = 40
CHUNK_H = 8
CHUNK_SIZE = CHUNK_W * CHUNK_H          # 320 characters

view_box1 = (0, 0, 40, 8)               # x, y, w, h  (immutable)

# ============================================================
# Editor state
# ============================================================

class Editor:
    def __init__(self, filename):
        self.filename = filename
        self.offset = 0                 # byte/character offset in file
        self.chunk = ""                 # current editable buffer (may grow)
        self.dirty = False              # True if chunk differs from file
        self.cursor_x = 0               # column inside chunk (0-based)
        self.cursor_y = 0               # line inside chunk (0-based)
        self.running = True

        # Load first chunk
        self._load_chunk()

    # ----------------------------------------------------------
    # Chunk management
    # ----------------------------------------------------------
    def _load_chunk(self):
        data = load_file(self.filename, self.offset, CHUNK_SIZE)
        if data is None:
            # File does not exist or error → start with empty chunk
            self.chunk = ""
        else:
            self.chunk = data
        self.dirty = False
        # Clamp cursor
        self._clamp_cursor()

    def _save_chunk(self):
        """Write current chunk back to file at current offset."""
        if write_file_chunk(self.filename, self.offset, self.chunk):
            self.dirty = False
            return True
        return False

    def _next_chunk(self):
        """Save current (if dirty) and load next chunk."""
        if self.dirty:
            self._save_chunk()
        self.offset += CHUNK_SIZE
        self._load_chunk()
        self.cursor_x = 0
        self.cursor_y = 0

    def _prev_chunk(self):
        """Save current (if dirty) and load previous chunk."""
        if self.dirty:
            self._save_chunk()
        if self.offset >= CHUNK_SIZE:
            self.offset -= CHUNK_SIZE
        else:
            self.offset = 0
        self._load_chunk()
        self.cursor_x = 0
        self.cursor_y = 0

    def _reload_chunk(self):
        """Discard user changes and reload from file."""
        self._load_chunk()

    def _save_and_reload(self):
        """Write current chunk, then reload it (CTRL_S)."""
        self._save_chunk()
        self._load_chunk()

    # ----------------------------------------------------------
    # Cursor helpers
    # ----------------------------------------------------------
    def _lines(self):
        """Split chunk into lines (keep empty lines)."""
        if not self.chunk:
            return [""]
        # Preserve trailing newline semantics
        lines = self.chunk.split("\n")
        return lines

    def _clamp_cursor(self):
        lines = self._lines()
        if self.cursor_y >= len(lines):
            self.cursor_y = max(0, len(lines) - 1)
        if self.cursor_y < 0:
            self.cursor_y = 0
        line = lines[self.cursor_y]
        if self.cursor_x > len(line):
            self.cursor_x = len(line)
        if self.cursor_x < 0:
            self.cursor_x = 0

    def _cursor_pos_in_chunk(self):
        """Absolute character index of cursor inside self.chunk."""
        lines = self._lines()
        pos = 0
        for i in range(self.cursor_y):
            pos += len(lines[i]) + 1   # +1 for the newline
        pos += self.cursor_x
        return pos

    # ----------------------------------------------------------
    # Editing operations
    # ----------------------------------------------------------
    def insert_char(self, ch):
        pos = self._cursor_pos_in_chunk()
        self.chunk = self.chunk[:pos] + ch + self.chunk[pos:]
        self.dirty = True
        if ch == "\n":
            self.cursor_y += 1
            self.cursor_x = 0
        else:
            self.cursor_x += 1
        self._clamp_cursor()

    def delete_char(self):
        """Delete character under / after cursor (DEL)."""
        pos = self._cursor_pos_in_chunk()
        if pos < len(self.chunk):
            self.chunk = self.chunk[:pos] + self.chunk[pos + 1:]
            self.dirty = True
            self._clamp_cursor()

    def backspace(self):
        """Delete character before cursor."""
        pos = self._cursor_pos_in_chunk()
        if pos > 0:
            # Move cursor left first so that the character disappears
            # under the cursor position
            self.chunk = self.chunk[:pos - 1] + self.chunk[pos:]
            self.dirty = True
            # Adjust cursor
            if self.cursor_x > 0:
                self.cursor_x -= 1
            else:
                # crossed a newline
                self.cursor_y -= 1
                lines = self._lines()
                if self.cursor_y >= 0:
                    self.cursor_x = len(lines[self.cursor_y])
            self._clamp_cursor()

    def move_up(self):
        if self.cursor_y > 0:
            self.cursor_y -= 1
            self._clamp_cursor()

    def move_down(self):
        lines = self._lines()
        if self.cursor_y < len(lines) - 1:
            self.cursor_y += 1
            self._clamp_cursor()

    def move_left(self):
        if self.cursor_x > 0:
            self.cursor_x -= 1
        elif self.cursor_y > 0:
            self.cursor_y -= 1
            lines = self._lines()
            self.cursor_x = len(lines[self.cursor_y])
        self._clamp_cursor()

    def move_right(self):
        lines = self._lines()
        line = lines[self.cursor_y]
        if self.cursor_x < len(line):
            self.cursor_x += 1
        elif self.cursor_y < len(lines) - 1:
            self.cursor_y += 1
            self.cursor_x = 0
        self._clamp_cursor()

    # ----------------------------------------------------------
    # Rendering
    # ----------------------------------------------------------
    def draw(self):
        clear()
        lines = self._lines()

        # ---- Header (line 0) ----
        prefix = "~" if self.dirty else " "
        # Truncate filename if needed
        name = self.filename
        max_name = CHUNK_W - 1
        if len(name) > max_name:
            name = name[:max_name]
        header = prefix + name
        # Pad with spaces (no .ljust)
        while len(header) < CHUNK_W:
            header += " "
        move_cursor(0, 0)
        sys.stdout.write(header[:CHUNK_W])

        # ---- Edit area (lines 1 .. 6)  → 6 visible lines ----
        # Header is y=0, footer is y=7 → edit zone height = 6
        edit_h = CHUNK_H - 2          # 6
        for row in range(edit_h):
            move_cursor(0, row + 1)
            if row < len(lines):
                line = lines[row]
            else:
                line = ""
            # Pad
            while len(line) < CHUNK_W:
                line += " "
            line = line[:CHUNK_W]
            sys.stdout.write(line)

        # ---- Footer (line 7) ----
        # Ln:3 Col: 10 Len: 120 Offset: 1024
        ln = self.cursor_y + 1
        col = self.cursor_x + 1
        length = len(self.chunk)
        footer = f"Ln:{ln} Col:{col} Len:{length} Offset:{self.offset}"
        while len(footer) < CHUNK_W:
            footer += " "
        footer = footer[:CHUNK_W]
        move_cursor(0, 7)
        sys.stdout.write(footer)

        # ---- Draw cursor as '_' and show the real character after it ----
        # Cursor is only drawn if it is inside the visible edit area
        if 0 <= self.cursor_y < edit_h:
            cy = self.cursor_y + 1          # screen row
            cx = self.cursor_x
            if cx >= CHUNK_W:
                cx = CHUNK_W - 1
            # Character that sits under the cursor
            lines = self._lines()
            if self.cursor_y < len(lines) and self.cursor_x < len(lines[self.cursor_y]):
                under = lines[self.cursor_y][self.cursor_x]
            else:
                under = " "
            # Draw '_' at cursor position
            move_cursor(cx, cy)
            sys.stdout.write("_")
            # Draw the original character immediately to the right of '_'
            if cx + 1 < CHUNK_W:
                move_cursor(cx + 1, cy)
                sys.stdout.write(under)

        # No flush available – just leave it

    # ----------------------------------------------------------
    # Main loop
    # ----------------------------------------------------------
    def run(self):
        while self.running:
            self.draw()
            key = get_key()
            if key is None:
                continue

            # ---- Control keys ----
            if key == "CTRL_B":
                self._prev_chunk()
            elif key == "CTRL_F":
                self._next_chunk()
            elif key == "CTRL_L":
                self._reload_chunk()
            elif key == "CTRL_S":
                self._save_and_reload()
            elif key == "CTRL_C" or key == "ESC":
                # Optional exit
                if self.dirty:
                    self._save_chunk()
                self.running = False

            # ---- Navigation ----
            elif key == "UP" or key == "\x1b[A":
                self.move_up()
            elif key == "DOWN" or key == "\x1b[B":
                self.move_down()
            elif key == "RIGHT" or key == "\x1b[C":
                self.move_right()
            elif key == "LEFT" or key == "\x1b[D":
                self.move_left()

            # ---- Editing ----
            elif key == "BACKSPACE":
                self.backspace()
            elif key == "DELETE" or key == "\x1b[3~":
                self.delete_char()
            elif key == "ENTER":
                self.insert_char("\n")
            elif key == "TAB":
                self.insert_char("    ")   # 4 spaces
            elif len(key) == 1 and ord(key) >= 32:
                # Printable character
                self.insert_char(key)

            # Ignore everything else

# ============================================================
# Arrow-key escape sequence handling (simple)
# ============================================================
# Because get_key only reads one character, we need a tiny
# state machine for CSI sequences.  We extend get_key slightly.

_original_get_key = get_key

def get_key():
    ch = _original_get_key()
    if ch != "ESC":
        return ch
    # Possible CSI sequence
    try:
        ch2 = sys.stdin.read(1)
        if ch2 != "[":
            return "ESC"
        ch3 = sys.stdin.read(1)
        if ch3 == "A":
            return "UP"
        if ch3 == "B":
            return "DOWN"
        if ch3 == "C":
            return "RIGHT"
        if ch3 == "D":
            return "LEFT"
        if ch3 == "3":
            # DELETE = ESC [ 3 ~
            ch4 = sys.stdin.read(1)
            if ch4 == "~":
                return "DELETE"
        return "ESC"
    except Exception:
        return "ESC"

# ============================================================
# Entry point
# ============================================================

def main(filename):
    """
    Main entry point of the text editor.
    :param filename: path to the file to edit
    """
    editor = Editor(filename)
    editor.run()

# ------------------------------------------------------------
# If the module is executed directly (for testing)
# ------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        # Fallback for interactive testing on Cardputer
        main("edit.txt")