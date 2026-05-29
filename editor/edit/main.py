import sys
import os
import subprocess
import platform
from .utils import get_key, clear, move_cursor
from .clipboard import copy_to_clipboard, paste_from_clipboard
from .file_helpers import load_file, save_file
from .state import EditorState, SelectionState
from enum import Enum
class MODE(Enum):
    EDIT = 0
    LOG = 1
    MODAL = 2
# TODO provide the settings to the main() function throught the argument
USE_TAB = False
TAB_SIZE = 2
def get_tab():
    if USE_TAB:
        return "\t"
    return " " * TAB_SIZE
def fill(text, max_width):
    if len(text) >= max_width:
        return text[0:max_width]
    else:
        return text + ' ' * (max_width - len(text))
view_box1 = (1, 1, 50, 20)  # x,y,w,h (immutable!)
def get_selected_text(state, selectionState):
    r = selectionState.normalize_selection()
    if not r:
        return ""
    (r1, c1), (r2, c2) = r
    lines = state.doc_lines
    if r1 == r2:
        return lines[r1][c1:c2]
    out = []
    out.append(lines[r1][c1:])
    for y in range(r1 + 1, r2):
        out.append(lines[y])
    out.append(lines[r2][:c2])
    return "\n".join(out)
def delete_selection(state, selectionState):
    r = selectionState.normalize_selection()
    if not r:
        return None
    (r1, c1), (r2, c2) = r
    doc_lines = state.doc_lines
    if r1 == r2:
        line = doc_lines[r1]
        doc_lines[r1] = (line[:c1] + line[c2:])
    else:
        first = doc_lines[r1][:c1]
        last = doc_lines[r2][c2:]
        doc_lines[r1] = first + last
        del doc_lines[r1 + 1:r2 + 1]
    selectionState.clear_selection()
    return r1, c1
def insert_text(state, row, col, text):
    parts = text.split("\n")
    doc_lines = state.doc_lines
    line = doc_lines[row]
    before = line[:col]
    after = line[col:]
    if len(parts) == 1:
        doc_lines[row] = (before + text + after)
        return row, col + len(text)
    doc_lines[row] = before + parts[0]
    insert_pos = row + 1
    for p in parts[1:-1]:
        doc_lines.insert(insert_pos, p)
        insert_pos += 1
    doc_lines.insert(insert_pos, parts[-1] + after)
    return insert_pos, len(parts[-1])
def replace_selection(state, selectionState, text):
    pos = delete_selection(state, selectionState)
    if pos is None:
        return None
    row, col = pos
    return insert_text(state, row, col, text)
def _unindent_line(line):
    indent = get_tab()
    if indent == "\t":
        if line.startswith("\t"):
            return line[1:]
        return line
    if line.startswith(indent):
        return line[len(indent):]
    if line.startswith("\t"):
        return line[1:]
    stripped = 0
    while stripped < TAB_SIZE and stripped < len(line) and line[stripped] == " ":
        stripped += 1
    return line[stripped:]
def shift_selected_lines(state, selectionState, direction):
    r = selectionState.normalize_selection()
    if not r:
        return None
    (r1, c1), (r2, c2) = r
    indent = get_tab()
    if direction > 0:
        for y in range(r1, r2 + 1):
            state.doc_lines[y] = indent + state.doc_lines[y]
    else:
        for y in range(r1, r2 + 1):
            state.doc_lines[y] = _unindent_line(state.doc_lines[y])
    return r1, c1
def build_visual_lines(state):
    visual = []
    width = view_box1[2]
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
    return visual
def find_visual_index(visual, doc_y, real_x):
    if not visual:
        return 0
    for i, (dy, start, seg) in enumerate(visual):
        if dy == doc_y and start <= real_x <= (start + len(seg)):
            return i
    return len(visual) - 1
def move_page(state, doc_y, real_x, direction):
    visual = build_visual_lines(state)
    if not visual:
        return 0, 0, visual
    current_vis_idx = find_visual_index(visual, doc_y, real_x)
    _, current_start, _ = visual[current_vis_idx]
    cx = real_x - current_start
    target_vis_idx = current_vis_idx + (direction * view_box1[3])
    if target_vis_idx < 0:
        target_vis_idx = 0
    if target_vis_idx >= len(visual):
        target_vis_idx = len(visual) - 1
    target_dy, target_start, _ = visual[target_vis_idx]
    target_real_x = min(target_start + cx, len(state.doc_lines[target_dy]))
    return target_dy, target_real_x, visual
def fill_view_box(state, view_box, visual_lines, cursor=None):
    for i in range(view_box[3]):
        move_cursor(view_box[0], view_box[1] + i)
        idx = state.view_offset + i
        if idx < len(visual_lines):
            _, _, text = (visual_lines[idx])
        else:
            text = ""
        if cursor and i == cursor[1]:
            cx = cursor[0]
            if cx >= len(text):
                text = text + "_"
            else:
                text = (text[:cx] + "_" + text[cx:])
        print(fill(text, view_box[2]), end='')
    sys.stdout.flush()
def get_status(selectionState, doc_y, real_x, ch, path):
    """
    Returns the status bar content for Edit mode.
    The status bar displays:
    - the current file name
    - an asterisk (*) if the file has unsaved changes
    - the current cursor position or active selection location
    - the character at the current cursor position
    """
    if selectionState.has_selection():
        (r1, c1), (r2, c2) = selectionState.normalize_selection()
        return f"({r1 + 1},{c1 + 1},{r2 + 1},{c2 + 1}) {path}"
    else:
        return f"({doc_y + 1}:{real_x + 1}) {repr(ch)} {path}"
def print_status(message):
    # TODO paramtrize view_box
    y = view_box1[1] + view_box1[3]
    move_cursor(view_box1[0], y)
    print(fill(message, view_box1[2]), end='')
    sys.stdout.flush()
def main():
    state = EditorState()
    selectionState = SelectionState()
    clear()
    if len(sys.argv) > 1:
        state.file_path = sys.argv[1]
        state.doc_lines = load_file(state.file_path)
    else:
        state.file_path = "untitled.txt"
    if not state.doc_lines:
        state.doc_lines = [""]
    prev = None
    mode = MODE.EDIT
    modal_id = None
    cursor_offset = [0, 0]
    clear()
    visual = build_visual_lines(state)
    fill_view_box(state, view_box1, visual, cursor=cursor_offset)
    vis_idx = state.view_offset + cursor_offset[1]
    if vis_idx >= len(visual):
        vis_idx = len(visual) - 1
    doc_y, start_idx, _ = (visual[vis_idx])
    real_x = start_idx + cursor_offset[0]
    print_status(get_status(selectionState, doc_y, real_x, '', state.file_path))
    while True:
        key = get_key()
        if mode == MODE.LOG:
            print(f"{key=}")
        if mode == MODE.MODAL:
            print(f"{key=} {modal_id=}")
            if modal_id == 1:
                if key == 'y':
                    save_file(state.file_path, state.doc_lines)
                    state.modified = False
                clear()
                break
        if (key == "CTRL_Q" and prev == "CTRL_Q"):
            if state.modified:
                mode = MODE.MODAL
                modal_id = 1
                print_status("Save before exit? y/n")
                continue
            else:
                clear()
                break
        if (key == "CTRL_Z" and prev == "CTRL_Z"):
            clear()
            break
        if key == "CTRL_W":
            clear()
        if key == "CTRL_S":
            save_file(state.file_path, state.doc_lines)
            state.modified = False
        if key == "CTRL_P" and (mode == MODE.EDIT or mode == MODE.LOG):
            mode = MODE.EDIT if mode == MODE.LOG else MODE.LOG
            cursor_offset = [0, 0]
            clear()
        if mode == MODE.EDIT:
            visual = build_visual_lines(state)
            if not visual:
                visual = [(0, 0, "")]
            cx, cy = cursor_offset
            vis_idx = (state.view_offset + cy)
            if vis_idx >= len(visual):
                vis_idx = (len(visual) - 1)
            doc_y, start_idx, segment = (visual[vis_idx])
            line = state.doc_lines[doc_y]
            real_x = start_idx + cx
            shift_move = key in ('SHIFT+LEFT', 'SHIFT+RIGHT', 'SHIFT+UP', 'SHIFT+DOWN', 'SHIFT+PAGE_DOWN', 'SHIFT+PAGE_UP', 'SHIFT+HOME', 'SHIFT+END')
            if shift_move:
                if not selectionState.in_progress:
                    selectionState.begin_selection(doc_y, real_x)
            else:
                if selectionState.in_progress:
                    selectionState.finalize_selection()
            if selectionState.has_selection() and key in ('TAB', '[Z'):
                if key == 'TAB':
                    pos = shift_selected_lines(state, selectionState, 1)
                else:
                    pos = shift_selected_lines(state, selectionState, -1)
                if pos:
                    state.modified = True
                prev = key
                clear()
                visual = build_visual_lines(state)
                cx, cy = cursor_offset
                vis_idx = (state.view_offset + cy)
                if vis_idx >= len(visual):
                    vis_idx = len(visual) - 1
                doc_y, start_idx, segment = (visual[vis_idx])
                line = state.doc_lines[doc_y]
                real_x = start_idx + cx
                if shift_move:
                    selectionState.update_selection(doc_y, real_x)
                new_vis_idx = 0
                for i, (dy, start, seg) in enumerate(visual):
                    if (dy == doc_y and start <= real_x <= (start + len(seg))):
                        new_vis_idx = i
                        break
                dy, start, seg = (visual[new_vis_idx])
                cx = real_x - start
                cy = new_vis_idx - state.view_offset
                if cy < 0:
                    state.view_offset = new_vis_idx
                    cy = 0
                elif cy >= view_box1[3]:
                    state.view_offset = new_vis_idx - view_box1[3] + 1
                    cy = view_box1[3] - 1
                cursor_offset = [cx, cy]
                fill_view_box(state, view_box1, visual, cursor=(cx, cy))
                ch = ''
                if (doc_y < len(state.doc_lines)):
                    if (real_x < len(state.doc_lines[doc_y])):
                        ch = state.doc_lines[doc_y][real_x]
                print_status(get_status(selectionState, doc_y, real_x, ch, state.file_path + ('*' if state.modified else '')))
                continue
            if selectionState.has_selection():
                if key == "CTRL_C":
                    copy_to_clipboard(get_selected_text(state, selectionState))
                    prev = key
                    continue
                elif key == "CTRL_X":
                    copy_to_clipboard(get_selected_text(state, selectionState))
                    pos = delete_selection(state, selectionState)
                    if pos:
                        doc_y, real_x = pos
                        state.modified = True
                elif key in ("DELETE", "BACKSPACE"):
                    pos = delete_selection(state, selectionState)
                    if pos:
                        doc_y, real_x = pos
                        state.modified = True
                elif len(key) == 1:
                    pos = replace_selection(state, selectionState, key)
                    if pos:
                        doc_y, real_x = pos
                        state.modified = True
                elif not shift_move:
                    selectionState.clear_selection()
            if key == "CTRL_V":
                text = (paste_from_clipboard())
                if selectionState.has_selection():
                    pos = replace_selection(state, selectionState, text)
                    if pos:
                        doc_y, real_x = pos
                        state.modified = True
                else:
                    doc_y, real_x = insert_text(state, doc_y, real_x, text)
                    state.modified = True
            elif key == "TAB":
                if selectionState.has_selection():
                    pass
                else:
                    doc_y, real_x = insert_text(state, doc_y, real_x, get_tab())
                    state.modified = True
            elif len(key) == 1:
                line = state.doc_lines[doc_y]
                line = (line[:real_x] + key + line[real_x:])
                state.doc_lines[doc_y] = line
                real_x += 1
                state.modified = True
            elif key == "ENTER":
                line = state.doc_lines[doc_y]
                new_line = (line[real_x:])
                state.doc_lines[doc_y] = (line[:real_x])
                state.doc_lines.insert(doc_y + 1, new_line)
                doc_y += 1
                real_x = 0
                state.modified = True
            elif key == "BACKSPACE":
                line = state.doc_lines[doc_y]
                if real_x > 0:
                    line = (line[:real_x - 1] + line[real_x:])
                    state.doc_lines[doc_y] = line
                    real_x -= 1
                elif doc_y > 0:
                    prev_line = state.doc_lines[doc_y - 1]
                    real_x = len(prev_line)
                    state.doc_lines[doc_y - 1] = (prev_line + line)
                    state.doc_lines.pop(doc_y)
                    doc_y -= 1
                state.modified = True
            elif key == "DELETE":
                line = state.doc_lines[doc_y]
                if real_x < len(line):
                    line = (line[:real_x] + line[real_x + 1:])
                    state.doc_lines[doc_y] = line
                elif (doc_y < len(state.doc_lines) - 1):
                    state.doc_lines[doc_y] += state.doc_lines[doc_y + 1]
                    state.doc_lines.pop(doc_y + 1)
                state.modified = True
            elif key in ("LEFT", "SHIFT+LEFT"):
                if real_x > 0:
                    real_x -= 1
                elif doc_y > 0:
                    doc_y -= 1
                    real_x = len(state.doc_lines[doc_y])
            elif key in ("RIGHT", "SHIFT+RIGHT"):
                if real_x < len(line):
                    real_x += 1
                elif (doc_y < len(state.doc_lines) - 1):
                    doc_y += 1
                    real_x = 0
            elif key in ("UP", "SHIFT+UP"):
                if doc_y > 0:
                    doc_y -= 1
                    real_x = min(real_x, len(state.doc_lines[doc_y]))
            elif key in ("DOWN", "SHIFT+DOWN"):
                if (doc_y < len(state.doc_lines) - 1):
                    doc_y += 1
                    real_x = min(real_x, len(state.doc_lines[doc_y]))
            elif key in ("HOME", "SHIFT+HOME"):
                real_x = 0
            elif key in ("END", "SHIFT+END"):
                real_x = len(state.doc_lines[doc_y])
            elif key in ("PAGEDOWN", "PAGE_DOWN", "PAGE DOWN", "SHIFT+PAGEDOWN", "SHIFT+PAGE_DOWN", "SHIFT+PAGE DOWN"):
                doc_y, real_x, visual = move_page(state, doc_y, real_x, 1)
            elif key in ("PAGEUP", "PAGE_UP", "PAGE UP", "SHIFT+PAGEUP", "SHIFT+PAGE_UP", "SHIFT+PAGE UP"):
                doc_y, real_x, visual = move_page(state, doc_y, real_x, -1)
            if shift_move:
                selectionState.update_selection(doc_y, real_x)
            visual = build_visual_lines(state)
            new_vis_idx = 0
            for i, (dy, start, seg) in enumerate(visual):
                if (dy == doc_y and start <= real_x <= (start + len(seg))):
                    new_vis_idx = i
                    break
            dy, start, seg = (visual[new_vis_idx])
            cx = real_x - start
            cy = new_vis_idx - state.view_offset
            if cy < 0:
                state.view_offset = new_vis_idx
                cy = 0
            elif cy >= view_box1[3]:
                state.view_offset = new_vis_idx - view_box1[3] + 1
                cy = view_box1[3] - 1
            cursor_offset = [cx, cy]
            fill_view_box(state, view_box1, visual, cursor=(cx, cy))
            ch = ''
            if (doc_y < len(state.doc_lines)):
                if (real_x < len(state.doc_lines[doc_y])):
                    ch = state.doc_lines[doc_y][real_x]
            print_status(get_status(selectionState, doc_y, real_x, ch, state.file_path + ('*' if state.modified else '')))
        prev = key
if __name__ == "__main__":
    main()
