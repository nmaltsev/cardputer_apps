from .utils import pad_line, wrap_line, get_key
from .file_menu import file_menu
from .editor import text_editor

# ---------- TYPE FUNCTION ----------
def type_file(path):
    # try:
    #     with open(path, "r") as f:
    #         raw_lines = f.readlines()
    # except Exception as e:
    #     print("Error opening file:", e)
    with open(path, "r") as f:
        raw_lines = f.readlines()

    lines = []
    for l in raw_lines:
        l = l.rstrip("\n")
        lines.extend(wrap_line(l))

    page_size = 8
    page = 0

    while True:
        start = page * page_size
        end = start + page_size
        chunk = lines[start:end]
        print()
        print(pad_line("b {}".format(path), width=39))

        for i in range(page_size):
            if i < len(chunk):
                print("{} {}".format(i, chunk[i]))
            else:
                print()  # empty line

        print(pad_line("f q,m,ezw p=" + str(page), width=39), end='')

        key = get_key()

        if key == 'q':
            break
        elif key == 'm':
            file_menu(path)
        elif key == 'b':
            if page > 0:
                page -= 1
        elif key == 'e':
            text_editor(path)

        elif key == 'z':
            # todo temporal fix (last stable version)
            from .editor1 import text_editor as text_editor1
            text_editor1(path)  
        elif key == 'w':
            from .editor2 import text_editor as text_editor2
            text_editor2(path)
        else:
            if end < len(lines):
                page += 1
            else:
                print("<END>")
                break
