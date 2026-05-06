# --- ORIGINAL IMPORTS (preserved) ---
from edit_utils import get_key, clear, move_cursor

# --- ORIGINAL FUNCTIONS (preserved) ---
def fill(text, max_width):
    if len(text) >= max_width:
        return text[0:max_width]
    else:
        return text + '-' * (max_width - len(text))

view_box1 = (5,5,40, 10) # x,y, w,h (immutable!)

# --- NEW: document + viewport state ---
doc_lines = [""]  # full document
view_offset = 0    # first visible line index in doc

# --- UPDATED: render using buffer ---
def fill_view_box(view_box, buffer):
    for i in range(view_box[3]):
        move_cursor(view_box[0], view_box[1] + i)
        line = buffer[i] if i < len(buffer) else ""
        print(fill(line, view_box[2]), end='')
    print()

# --- NEW: sync document -> buffer ---
def build_buffer():
    buffer = []
    for i in range(view_box1[3]):
        idx = view_offset + i
        if idx < len(doc_lines):
            buffer.append(doc_lines[idx])
        else:
            buffer.append("")
    return buffer

# --- NEW: cursor drawing ---
def draw_cursor(cx, cy):
    move_cursor(view_box1[0] + cx, view_box1[1] + cy)
    print('_', end='')

# --- MAIN ---
def main():
    global view_offset

    prev = None
    EDIT_MODE = False
    cursor_offset = [0,0] # dx, dy

    while True:
        key = get_key()

        if EDIT_MODE is False:
            print(f"{key=}")

        if key == 'CTRL_C' and prev == 'CTRL_C':
            break

        if key == 'CTRL_W':
            clear()

        if key == 'CTRL_P':
            EDIT_MODE = True
            buffer = build_buffer()
            fill_view_box(view_box1, buffer)
            cursor_offset = [0,0]
            draw_cursor(*cursor_offset)
            print()

        if EDIT_MODE:
            cx, cy = cursor_offset
            doc_y = view_offset + cy

            # ensure line exists
            while doc_y >= len(doc_lines):
                doc_lines.append("")

            line = doc_lines[doc_y]

            # --- TEXT INPUT ---
            if len(key) == 1:
                line = line[:cx] + key + line[cx:]
                doc_lines[doc_y] = line
                cx += 1

            # --- ENTER ---
            elif key == 'ENTER':
                new_line = line[cx:]
                doc_lines[doc_y] = line[:cx]
                doc_lines.insert(doc_y + 1, new_line)
                cx = 0
                cy += 1

            # --- BACKSPACE ---
            elif key == 'BACKSPACE':
                if cx > 0:
                    line = line[:cx-1] + line[cx:]
                    doc_lines[doc_y] = line
                    cx -= 1
                elif doc_y > 0:
                    prev_line = doc_lines[doc_y - 1]
                    cx = len(prev_line)
                    doc_lines[doc_y - 1] = prev_line + line
                    doc_lines.pop(doc_y)
                    cy -= 1

            # --- DELETE ---
            elif key == 'DELETE':
                if cx < len(line):
                    line = line[:cx] + line[cx+1:]
                    doc_lines[doc_y] = line
                elif doc_y < len(doc_lines) - 1:
                    doc_lines[doc_y] += doc_lines[doc_y + 1]
                    doc_lines.pop(doc_y + 1)

            # --- ARROWS ---
            elif key == 'LEFT':
                if cx > 0:
                    cx -= 1
                elif doc_y > 0:
                    cy -= 1
                    cx = len(doc_lines[doc_y - 1])

            elif key == 'RIGHT':
                if cx < len(line):
                    cx += 1
                elif doc_y < len(doc_lines) - 1:
                    cy += 1
                    cx = 0

            elif key == 'UP':
                if cy > 0:
                    cy -= 1
                elif view_offset > 0:
                    view_offset -= 1
                cx = min(cx, len(doc_lines[view_offset + cy]))

            elif key == 'DOWN':
                if cy < view_box1[3] - 1:
                    cy += 1
                else:
                    view_offset += 1
                if view_offset + cy < len(doc_lines):
                    cx = min(cx, len(doc_lines[view_offset + cy]))

            # clamp cursor
            cy = max(0, min(cy, view_box1[3]-1))
            cx = max(0, cx)

            cursor_offset = [cx, cy]

            # --- RENDER ---
            buffer = build_buffer()
            fill_view_box(view_box1, buffer)
            draw_cursor(cx, cy)
            print()

        prev = key

if __name__ == '__main__':
    main()
