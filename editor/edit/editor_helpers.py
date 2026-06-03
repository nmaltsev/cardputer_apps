import sys
from .utils import clear, move_cursor

def fill(text, max_width):
    if len(text) >= max_width:
        return text[0:max_width]
    else:
        return text + ' ' * (max_width - len(text))

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
def _unindent_line(line, state):
    indent = state.get_tab()
    if indent == "\t":
        if line.startswith("\t"):
            return line[1:]
        return line
    if line.startswith(indent):
        return line[len(indent):]
    if line.startswith("\t"):
        return line[1:]
    stripped = 0
    while stripped < state.tab_size and stripped < len(line) and line[stripped] == " ":
        stripped += 1
    return line[stripped:]
def shift_selected_lines(state, selectionState, direction):
    r = selectionState.normalize_selection()
    if not r:
        return None
    (r1, c1), (r2, c2) = r
    indent = state.get_tab()
    if direction > 0:
        for y in range(r1, r2 + 1):
            state.doc_lines[y] = indent + state.doc_lines[y]
    else:
        for y in range(r1, r2 + 1):
            state.doc_lines[y] = _unindent_line(state.doc_lines[y], state)
    return r1, c1
def build_visual_lines(state):
    visual = []
    width = state.view_box[2]
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
    target_vis_idx = current_vis_idx + (direction * state.view_box[3])
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

def print_status(state, message):
    y = state.view_box[1] + state.view_box[3]
    move_cursor(state.view_box[0], y)
    print(fill(message, state.view_box[2]), end='')
    sys.stdout.flush()

def initial_set(state, selectionState):
    # clear()
    visual = build_visual_lines(state)
    fill_view_box(state, state.view_box, visual, cursor=state.cursor_offset)
    vis_idx = state.view_offset + state.cursor_offset[1]
    if vis_idx >= len(visual):
        vis_idx = len(visual) - 1
    doc_y, start_idx, _ = (visual[vis_idx])
    real_x = start_idx + state.cursor_offset[0]
    print_status(state, get_status(selectionState, doc_y, real_x, '', state.file_path))

