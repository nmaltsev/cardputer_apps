import sys
import os
import shutil

from enum import Enum

from .utils import get_key, clear
from .file_helpers import load_file, save_file
from .state import (
    EditorState,
    SelectionState,
    FileBrowserState,
)
from .editor_helpers import (
    print_status,
    initial_set,
)
from .process_editor_keys import process_editor_keys
from .file_browser_helpers import (
    draw_file_browser,
    process_file_browser_key,
)


class MODE(Enum):
    EDIT = 0
    LOG = 1
    MODAL = 2
    FILE_BROWSER = 3
    TAB_BROWSER = 4
    TERM = 5


def redraw_all(state, selectionState, browser):
    draw_file_browser(browser)
    initial_set(state, selectionState)


def main(use_tab: bool = False, tab_size: int = 2):
    size = os.get_terminal_size()
    status_line_width = 1 # There will be a status line between the FileBrowser and TextEditor
    browser_width = 30
    editor_width = max(1, size.columns - browser_width - status_line_width)
    state = EditorState(
        use_tab=use_tab,
        tab_size=tab_size,
        view_box=(
            browser_width + status_line_width,
            0,
            editor_width,
            size.lines,
        ),
    )

    browser = FileBrowserState(
        view_box=(
            0,
            0,
            browser_width,
            size.lines,
        )
    )

    selectionState = SelectionState()

    if len(sys.argv) > 1:
        state.file_path = sys.argv[1]
        state.doc_lines = load_file(state.file_path)
    else:
        state.file_path = "untitled.txt"

    if not state.doc_lines:
        state.doc_lines = [""]

    prev_key = None
    mode = MODE.EDIT
    modal_payload = None
    clear()
    initial_set(state, selectionState)
    draw_file_browser(browser)
    # Use these 2 lines two draw UI
    print(end='')
    sys.stdout.flush()

    while True:
        key = get_key()

        # -----------------------------------------
        # Global shortcuts
        # -----------------------------------------
        if key == "CTRL_P" and (mode == MODE.EDIT or mode == MODE.LOG):
            mode = (MODE.EDIT if mode == MODE.LOG else MODE.LOG)
            clear()
            if mode == MODE.EDIT:
                initial_set(state, selectionState)
                draw_file_browser(browser)
                print(end='')
                sys.stdout.flush()
            else:
                print('DEBUG MODE')   
            prev_key = key
            continue

        # TODO use ALT_RIGHT
        if key == "CTRL_E":
            mode = MODE.FILE_BROWSER
            draw_file_browser(browser)
            sys.stdout.flush()
            prev_key = key
            continue

        if key == "CTRL_R":
            mode = MODE.EDIT
            initial_set(state, selectionState)
            draw_file_browser(browser)
            sys.stdout.flush()
            prev_key = key
            continue

        if (key == "CTRL_Z" and prev_key == "CTRL_Z"):
            clear()
            break

        # -----------------------------------------
        # LOG MODE
        # -----------------------------------------
        if mode == MODE.LOG:
            print(f"{key=}")

            if (key == "CTRL_T" and prev_key == "CTRL_T"):
                size = os.get_terminal_size()

                print(
                    f"columns: {size.columns} "
                    f"lines: {size.lines}"
                )

            if key == "CTRL_W":
                clear()

            prev_key = key
            continue

        # -----------------------------------------
        # MODAL MODE
        # -----------------------------------------

        if mode == MODE.MODAL:
            if modal_payload:
                action = modal_payload.get("action")

                # -------------------------
                # Exit confirmation
                # -------------------------
                if action == "exit":
                    if key == "y":
                        save_file(state.file_path, state.doc_lines,)
                        state.modified = False
                    clear()
                    break

                # -------------------------
                # Delete confirmation
                # -------------------------
                elif action == "delete":
                    if key == "y":
                        path = modal_payload["path"]

                        try:
                            if os.path.isdir(path):
                                shutil.rmtree(path)
                            elif os.path.exists(path):
                                os.remove(path)
                        except Exception as ex:
                            print_status(state,str(ex),)
                        browser.refresh()
                    modal_payload = None
                    mode = MODE.FILE_BROWSER
                    clear()

                    redraw_all(state, selectionState, browser,)
                    prev_key = key
                    continue

            prev_key = key
            continue

        # -----------------------------------------
        # EDIT MODE
        # -----------------------------------------
        if mode == MODE.EDIT:
            if (key == "CTRL_Q" and prev_key == "CTRL_Q"):
                if state.modified:
                    mode = MODE.MODAL
                    modal_payload = {
                        "action": "exit"
                    }

                    print_status(state, "Save before exit? y/n")
                    prev_key = key
                    continue
                clear()
                break

            if key == "CTRL_S":
                save_file(state.file_path, state.doc_lines,)
                state.modified = False
                redraw_all(state, selectionState, browser,)
                prev_key = key
                continue
            draw_file_browser(browser)
            process_editor_keys(key, prev_key, state,selectionState,)
            prev_key = key
            continue

        # -----------------------------------------
        # FILE BROWSER MODE
        # -----------------------------------------
        if mode == MODE.FILE_BROWSER:
            result = process_file_browser_key(key, browser,state,)
            draw_file_browser(browser)
            sys.stdout.flush()
            if result:
                action, path = result

                # ---------------------
                # Open file
                # ---------------------
                if action == "OPEN_FILE":
                    state.file_path = path
                    state.doc_lines = load_file(path)
                    if not state.doc_lines:
                        state.doc_lines = [""]

                    state.modified = False
                    state.view_offset = 0
                    state.cursor_offset = [0,0,]
                    selectionState.clear_selection()
                    mode = MODE.EDIT
                    initial_set(state, selectionState)
                    draw_file_browser(browser)
                    sys.stdout.flush()
                    prev_key = key
                    continue

                # ---------------------
                # Delete file
                # ---------------------
                elif action == "DELETE":
                    modal_payload = {
                        "action": "delete",
                        "path": path,
                    }
                    mode = MODE.MODAL
                    print_status(
                        state,
                        f"Delete '{os.path.basename(path)}'? y/n"
                    )
                    prev_key = key
                    continue

            draw_file_browser(browser)
            prev_key = key
            continue
        prev_key = key

if __name__ == "__main__":
    main()
