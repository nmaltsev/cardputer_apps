import sys
import os
import subprocess
import platform
from .utils import get_key, clear, move_cursor
from .clipboard import copy_to_clipboard, paste_from_clipboard
from .file_helpers import load_file, save_file
from .state import EditorState, SelectionState
from .edior_helpers import get_selected_text, delete_selection, insert_text, replace_selection, _unindent_line, shift_selected_lines, build_visual_lines, find_visual_index, move_page, fill_view_box, get_status, print_status, initial_set, fill
from enum import Enum

class MODE(Enum):
    EDIT = 0
    LOG = 1
    MODAL = 2
    FILE_NAV = 3
    TAB_NAV = 4
    TERM = 5

def main(use_tab:bool = False, tab_size:int = 2):
    size = os.get_terminal_size()
    state = EditorState(
        use_tab=use_tab, 
        tab_size=tab_size, 
        view_box=(0, 0, size.columns, size.lines)
    )
    selectionState = SelectionState()
    clear()
    if len(sys.argv) > 1:
        state.file_path = sys.argv[1]
        state.doc_lines = load_file(state.file_path)
    else:
        state.file_path = "untitled.txt"
    if not state.doc_lines:
        state.doc_lines = [""]
    prev_key = None
    mode = MODE.EDIT
    modal_id = None
    initial_set(state, selectionState)
    while True:
        key = get_key()
        if key == "CTRL_P" and (mode == MODE.EDIT or mode == MODE.LOG):
            mode = MODE.EDIT if mode == MODE.LOG else MODE.LOG
            clear()
        if (key == "CTRL_Z" and prev_key == "CTRL_Z"):
            clear()
            break
        if mode == MODE.LOG:
            print(f"{key=}")
            if (key == "CTRL_T" and prev_key == "CTRL_T"):
                size = os.get_terminal_size()
                print(f'columns: {size.columns} lines: {size.lines}')
            if key == "CTRL_W":
                clear()

        if mode == MODE.MODAL:
            print(f"{key=} {modal_id=}")
            if modal_id == 1:
                if key == 'y':
                    save_file(state.file_path, state.doc_lines)
                    state.modified = False
                clear()
                break
        
        
        if mode == MODE.EDIT:
            # XXX(key, prev_key, state)
            if (key == "CTRL_Q" and prev_key == "CTRL_Q"):
                if state.modified:
                    mode = MODE.MODAL
                    modal_id = 1
                    print_status(state, 'Save before exit? y/n')
                    continue
                else:
                    clear()
                    break
            if key == "CTRL_S":
                save_file(state.file_path, state.doc_lines)
                state.modified = False
            
            visual = build_visual_lines(state)
            if not visual:
                visual = [(0, 0, "")]
            cx, cy = state.cursor_offset
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
                prev_key = key
                clear()
                visual = build_visual_lines(state)
                cx, cy = state.cursor_offset
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
                elif cy >= state.view_box[3]:
                    state.view_offset = new_vis_idx - state.view_box[3] + 1
                    cy = state.view_box[3] - 1
                state.cursor_offset = [cx, cy]
                fill_view_box(state, state.view_box, visual, cursor=(cx, cy))
                ch = ''
                if (doc_y < len(state.doc_lines)):
                    if (real_x < len(state.doc_lines[doc_y])):
                        ch = state.doc_lines[doc_y][real_x]
                print_status(state, get_status(selectionState, doc_y, real_x, ch, state.file_path + ('*' if state.modified else '')))
                continue
            if selectionState.has_selection():
                if key == "CTRL_C":
                    copy_to_clipboard(get_selected_text(state, selectionState))
                    prev_key = key
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
                    doc_y, real_x = insert_text(state, doc_y, real_x, state.get_tab())
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
                    prev_key_line = state.doc_lines[doc_y - 1]
                    real_x = len(prev_key_line)
                    state.doc_lines[doc_y - 1] = (prev_key_line + line)
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
            elif cy >= state.view_box[3]:
                state.view_offset = new_vis_idx - state.view_box[3] + 1
                cy = state.view_box[3] - 1
            state.cursor_offset = [cx, cy]
            fill_view_box(state, state.view_box, visual, cursor=(cx, cy))
            ch = ''
            if (doc_y < len(state.doc_lines)):
                if (real_x < len(state.doc_lines[doc_y])):
                    ch = state.doc_lines[doc_y][real_x]
            print_status(state, get_status(selectionState, doc_y, real_x, ch, state.file_path + ('*' if state.modified else '')))
        prev_key = key
if __name__ == "__main__":
    main()
