# --- ORIGINAL IMPORTS (preserved) ---
from edit_utils import get_key, clear, move_cursor
import sys
import os

# --- ORIGINAL FUNCTIONS (preserved) ---
def fill(text, max_width):
    if len(text) >= max_width:
        return text[0:max_width]
    else:
        return text + '-' * (max_width - len(text))

view_box1 = (1,1,40, 10) # x,y, w,h (immutable!)

# --- DOCUMENT MODEL ---
doc_lines = [""]
view_offset = 0
file_path = None

# --- FILE IO ---
def load_file(path):
    global doc_lines
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            doc_lines = f.read().splitlines()
        if not doc_lines:
            doc_lines = [""]
    else:
        doc_lines = [""]


def save_file(path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(doc_lines))

# --- WRAPPING ---
def build_visual_lines():
    visual = []
    width = view_box1[2]

    for doc_y, line in enumerate(doc_lines):
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

    return visual

# --- RENDER ---
def fill_view_box(view_box, visual_lines):
    for i in range(view_box[3]):
        move_cursor(view_box[0], view_box[1] + i)
        idx = view_offset + i
        if idx < len(visual_lines):
            _, _, text = visual_lines[idx]
        else:
            text = ""
        print(fill(text, view_box[2]), end='')
    print()

# --- STATUS BAR ---
def draw_status(doc_y, real_x, ch):
    y = view_box1[1] + view_box1[3]
    move_cursor(view_box1[0], y)
    status = f"Ln {doc_y+1}, Col {real_x+1} | Char: {repr(ch)}"
    print(fill(status, view_box1[2]), end='')

# --- CURSOR ---
def draw_cursor(cx, cy):
    move_cursor(view_box1[0] + cx, view_box1[1] + cy)
    print('_', end='')

# --- MAIN ---
def main():
    global view_offset, file_path

    # --- CLI ARG ---
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        load_file(file_path)
    else:
        file_path = "untitled.txt"

    prev = None
    EDIT_MODE = False
    cursor_offset = [0,0]

    while True:
        key = get_key()

        if EDIT_MODE is False:
            print(f"{key=}")

        if key == 'CTRL_C' and prev == 'CTRL_C':
            break

        if key == 'CTRL_W':
            clear()

        if key == 'CTRL_S':
            save_file(file_path)

        if key == 'CTRL_P':
            EDIT_MODE = True
            cursor_offset = [0,0]

        if EDIT_MODE:
            visual = build_visual_lines()

            cx, cy = cursor_offset
            vis_idx = view_offset + cy

            if vis_idx >= len(visual):
                vis_idx = len(visual) - 1

            doc_y, start_idx, segment = visual[vis_idx]
            line = doc_lines[doc_y]
            real_x = start_idx + cx

            # --- INPUT ---
            if len(key) == 1:
                line = line[:real_x] + key + line[real_x:]
                doc_lines[doc_y] = line
                real_x += 1

            elif key == 'ENTER':
                new_line = line[real_x:]
                doc_lines[doc_y] = line[:real_x]
                doc_lines.insert(doc_y + 1, new_line)
                doc_y += 1
                real_x = 0

            elif key == 'BACKSPACE':
                if real_x > 0:
                    line = line[:real_x-1] + line[real_x:]
                    doc_lines[doc_y] = line
                    real_x -= 1
                elif doc_y > 0:
                    prev_line = doc_lines[doc_y - 1]
                    real_x = len(prev_line)
                    doc_lines[doc_y - 1] = prev_line + line
                    doc_lines.pop(doc_y)
                    doc_y -= 1

            elif key == 'DELETE':
                if real_x < len(line):
                    line = line[:real_x] + line[real_x+1:]
                    doc_lines[doc_y] = line
                elif doc_y < len(doc_lines) - 1:
                    doc_lines[doc_y] += doc_lines[doc_y + 1]
                    doc_lines.pop(doc_y + 1)

            # --- NAVIGATION ---
            elif key == 'LEFT':
                if real_x > 0:
                    real_x -= 1
                elif doc_y > 0:
                    doc_y -= 1
                    real_x = len(doc_lines[doc_y])

            elif key == 'RIGHT':
                if real_x < len(line):
                    real_x += 1
                elif doc_y < len(doc_lines) - 1:
                    doc_y += 1
                    real_x = 0

            elif key == 'UP':
                if doc_y > 0:
                    doc_y -= 1
                    real_x = min(real_x, len(doc_lines[doc_y]))

            elif key == 'DOWN':
                if doc_y < len(doc_lines) - 1:
                    doc_y += 1
                    real_x = min(real_x, len(doc_lines[doc_y]))

            # --- MAP BACK TO VISUAL ---
            visual = build_visual_lines()

            new_vis_idx = 0
            for i, (dy, start, seg) in enumerate(visual):
                if dy == doc_y and start <= real_x <= start + len(seg):
                    new_vis_idx = i
                    break

            dy, start, seg = visual[new_vis_idx]
            cx = real_x - start
            cy = new_vis_idx - view_offset

            # scrolling
            if cy < 0:
                view_offset = new_vis_idx
                cy = 0
            elif cy >= view_box1[3]:
                view_offset = new_vis_idx - view_box1[3] + 1
                cy = view_box1[3] - 1

            cursor_offset = [cx, cy]

            # --- RENDER ---
            fill_view_box(view_box1, visual)

            ch = ''
            if doc_y < len(doc_lines) and real_x < len(doc_lines[doc_y]):
                ch = doc_lines[doc_y][real_x]

            draw_status(doc_y, real_x, ch)
            draw_cursor(cx, cy)
            # Why print is necessery for showing cursor defined by draw_cursor()?
            # Is it possible to type the cursor at the same moment as the character? 
            print()
            # so the cursor moves to the next line as the first element of the next line
            # Is it possible to not show the cursor or move it at the draw_cursor position 

        prev = key

if __name__ == '__main__':
    main()
