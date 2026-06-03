import os

from .utils import move_cursor
from .editor_helpers import fill
from .file_helpers import load_file


def draw_file_browser(browser):
    x,y,w,h = browser.view_box
    visible = browser.items[
        browser.scroll_offset:
        browser.scroll_offset + h
    ]
    for row in range(h):
        move_cursor(x,y+row)
        idx = browser.scroll_offset + row
        if idx < len(browser.items):
            name = browser.items[idx]
            prefix = ">" if idx == browser.selected_index else " "
            text = prefix + name
        else:
            text = ""
        print(fill(text,w),end="")


def process_file_browser_key(
    key,
    browser,
    editor_state
):
    """
    returns:
        None

        ("OPEN_FILE", path)

        ("DELETE", path)
    """

    if key == "UP":
        if browser.selected_index > 0:
            browser.selected_index -= 1

            if browser.selected_index < browser.scroll_offset:
                browser.scroll_offset -= 1

    elif key == "DOWN":

        if browser.selected_index < len(browser.items)-1:
            browser.selected_index += 1

            bottom = (
                browser.scroll_offset
                + browser.view_box[3]
            )

            if browser.selected_index >= bottom:
                browser.scroll_offset += 1

    elif key == "ENTER":

        path = browser.current_full_path()

        if os.path.isdir(path):

            browser.current_path = path
            browser.selected_index = 0
            browser.scroll_offset = 0
            browser.refresh()

        elif os.path.isfile(path):

            return ("OPEN_FILE", path)

    elif key == "DELETE":

        path = browser.current_full_path()

        return ("DELETE", path)

    return None