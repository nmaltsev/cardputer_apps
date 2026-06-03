from dataclasses import dataclass

from .editor_helpers import (
    get_selected_text,
    delete_selection,
    insert_text,
    replace_selection,
    shift_selected_lines,
    build_visual_lines,
    move_page,
    fill_view_box,
    get_status,
    print_status,
)
from .clipboard import copy_to_clipboard, paste_from_clipboard


@dataclass
class EditorResult:
    doc_y: int
    real_x: int
    visual: list
    exit_editor: bool = False


def process_editor_keys(key, prev_key, state, selectionState):
    visual = build_visual_lines(state)

    if not visual:
        visual = [(0, 0, "")]

    cx, cy = state.cursor_offset

    vis_idx = state.view_offset + cy

    if vis_idx >= len(visual):
        vis_idx = len(visual) - 1

    doc_y, start_idx, segment = visual[vis_idx]

    line = state.doc_lines[doc_y]
    real_x = start_idx + cx

    shift_move = key in (
        "SHIFT+LEFT",
        "SHIFT+RIGHT",
        "SHIFT+UP",
        "SHIFT+DOWN",
        "SHIFT+PAGE_DOWN",
        "SHIFT+PAGE_UP",
        "SHIFT+HOME",
        "SHIFT+END",
    )

    # --------------------------------------------------
    # Selection begin/end
    # --------------------------------------------------

    if shift_move:
        if not selectionState.in_progress:
            selectionState.begin_selection(doc_y, real_x)
    else:
        if selectionState.in_progress:
            selectionState.finalize_selection()

    # --------------------------------------------------
    # Shift selected block
    # --------------------------------------------------

    if selectionState.has_selection() and key in ("TAB", "[Z"):

        if key == "TAB":
            shift_selected_lines(state, selectionState, 1)
        else:
            shift_selected_lines(state, selectionState, -1)

        state.modified = True

    # --------------------------------------------------
    # Selection operations
    # --------------------------------------------------

    elif selectionState.has_selection():

        if key == "CTRL_C":
            copy_to_clipboard(
                get_selected_text(state, selectionState)
            )

        elif key == "CTRL_X":
            copy_to_clipboard(
                get_selected_text(state, selectionState)
            )

            pos = delete_selection(
                state,
                selectionState,
            )

            if pos:
                doc_y, real_x = pos
                state.modified = True

        elif key in ("DELETE", "BACKSPACE"):

            pos = delete_selection(
                state,
                selectionState,
            )

            if pos:
                doc_y, real_x = pos
                state.modified = True

        elif len(key) == 1:

            pos = replace_selection(
                state,
                selectionState,
                key,
            )

            if pos:
                doc_y, real_x = pos
                state.modified = True

        elif not shift_move:
            selectionState.clear_selection()

    # --------------------------------------------------
    # Paste
    # --------------------------------------------------

    if key == "CTRL_V":

        text = paste_from_clipboard()

        if selectionState.has_selection():

            pos = replace_selection(
                state,
                selectionState,
                text,
            )

            if pos:
                doc_y, real_x = pos
                state.modified = True

        else:

            doc_y, real_x = insert_text(
                state,
                doc_y,
                real_x,
                text,
            )

            state.modified = True

    # --------------------------------------------------
    # Insert tab
    # --------------------------------------------------

    elif key == "TAB":

        if not selectionState.has_selection():

            doc_y, real_x = insert_text(
                state,
                doc_y,
                real_x,
                state.get_tab(),
            )

            state.modified = True

    # --------------------------------------------------
    # Printable chars
    # --------------------------------------------------

    elif len(key) == 1:

        line = state.doc_lines[doc_y]

        state.doc_lines[doc_y] = (
            line[:real_x]
            + key
            + line[real_x:]
        )

        real_x += 1
        state.modified = True

    # --------------------------------------------------
    # Enter
    # --------------------------------------------------

    elif key == "ENTER":

        line = state.doc_lines[doc_y]

        new_line = line[real_x:]

        state.doc_lines[doc_y] = line[:real_x]

        state.doc_lines.insert(
            doc_y + 1,
            new_line,
        )

        doc_y += 1
        real_x = 0

        state.modified = True

    # --------------------------------------------------
    # Backspace
    # --------------------------------------------------

    elif key == "BACKSPACE":

        line = state.doc_lines[doc_y]

        if real_x > 0:

            state.doc_lines[doc_y] = (
                line[:real_x - 1]
                + line[real_x:]
            )

            real_x -= 1

        elif doc_y > 0:

            prev_line = state.doc_lines[doc_y - 1]

            real_x = len(prev_line)

            state.doc_lines[doc_y - 1] = (
                prev_line + line
            )

            state.doc_lines.pop(doc_y)

            doc_y -= 1

        state.modified = True

    # --------------------------------------------------
    # Delete
    # --------------------------------------------------

    elif key == "DELETE":

        line = state.doc_lines[doc_y]

        if real_x < len(line):

            state.doc_lines[doc_y] = (
                line[:real_x]
                + line[real_x + 1:]
            )

        elif doc_y < len(state.doc_lines) - 1:

            state.doc_lines[doc_y] += (
                state.doc_lines[doc_y + 1]
            )

            state.doc_lines.pop(doc_y + 1)

        state.modified = True

    # --------------------------------------------------
    # Navigation
    # --------------------------------------------------

    elif key in ("LEFT", "SHIFT+LEFT"):

        if real_x > 0:
            real_x -= 1
        elif doc_y > 0:
            doc_y -= 1
            real_x = len(state.doc_lines[doc_y])

    elif key in ("RIGHT", "SHIFT+RIGHT"):

        if real_x < len(line):
            real_x += 1
        elif doc_y < len(state.doc_lines) - 1:
            doc_y += 1
            real_x = 0

    elif key in ("UP", "SHIFT+UP"):

        if doc_y > 0:
            doc_y -= 1
            real_x = min(
                real_x,
                len(state.doc_lines[doc_y]),
            )

    elif key in ("DOWN", "SHIFT+DOWN"):

        if doc_y < len(state.doc_lines) - 1:
            doc_y += 1
            real_x = min(
                real_x,
                len(state.doc_lines[doc_y]),
            )

    elif key in ("HOME", "SHIFT+HOME"):
        real_x = 0

    elif key in ("END", "SHIFT+END"):
        real_x = len(state.doc_lines[doc_y])

    elif key in (
        "PAGEDOWN",
        "PAGE_DOWN",
        "PAGE DOWN",
        "SHIFT+PAGEDOWN",
        "SHIFT+PAGE_DOWN",
        "SHIFT+PAGE DOWN",
    ):
        doc_y, real_x, visual = move_page(
            state,
            doc_y,
            real_x,
            1,
        )

    elif key in (
        "PAGEUP",
        "PAGE_UP",
        "PAGE UP",
        "SHIFT+PAGEUP",
        "SHIFT+PAGE_UP",
        "SHIFT+PAGE UP",
    ):
        doc_y, real_x, visual = move_page(
            state,
            doc_y,
            real_x,
            -1,
        )

    # --------------------------------------------------
    # Selection update
    # --------------------------------------------------

    if shift_move:
        selectionState.update_selection(
            doc_y,
            real_x,
        )

    # --------------------------------------------------
    # Rebuild screen
    # --------------------------------------------------

    visual = build_visual_lines(state)

    new_vis_idx = 0

    for i, (dy, start, seg) in enumerate(visual):

        if (
            dy == doc_y
            and start <= real_x <= start + len(seg)
        ):
            new_vis_idx = i
            break

    dy, start, seg = visual[new_vis_idx]

    cx = real_x - start
    cy = new_vis_idx - state.view_offset

    if cy < 0:
        state.view_offset = new_vis_idx
        cy = 0

    elif cy >= state.view_box[3]:
        state.view_offset = (
            new_vis_idx
            - state.view_box[3]
            + 1
        )
        cy = state.view_box[3] - 1

    state.cursor_offset = [cx, cy]

    fill_view_box(
        state,
        state.view_box,
        visual,
        cursor=(cx, cy),
    )

    ch = ""

    if doc_y < len(state.doc_lines):
        if real_x < len(state.doc_lines[doc_y]):
            ch = state.doc_lines[doc_y][real_x]

    print_status(
        state,
        get_status(
            selectionState,
            doc_y,
            real_x,
            ch,
            state.file_path
            + ("*" if state.modified else ""),
        ),
    )

    return EditorResult(
        doc_y=doc_y,
        real_x=real_x,
        visual=visual,
    )