import sys
import os
import subprocess
import platform
from .utils import get_key, clear, move_cursor
from .clipboard import copy_to_clipboard, paste_from_clipboard
from .file_helpers import load_file, save_file
from .state import EditorState, SelectionState
from enum import Enum
from .editor_helpers import fill, get_selected_text, delete_selection, insert_text, replace_selection, _unindent_line, shift_selected_lines, build_visual_lines, find_visual_index, move_page, fill_view_box, get_status, print_status, initial_set
from .process_editor_keys import process_editor_keys

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
            
            process_editor_keys(
                key,
                prev_key,
                state,
                selectionState,
            )
        prev_key = key
if __name__ == "__main__":
    main()
