from .utils import pad_line, wrap_line, get_key
from .file_menu import file_menu

# ---------- TYPE FUNCTION ----------
def type_file(path):
    try:
        with open(path, "r") as f:
            raw_lines = f.readlines()
    except Exception as e:
        print("Error opening file:", e)
        return

    lines = []
    for l in raw_lines:
        l = l.rstrip("\n")
        lines.extend(wrap_line(l))

    page_size = 7
    page = 0

    while True:
        start = page * page_size
        end = start + page_size
        chunk = lines[start:end]

        print()
        print(pad_line("F: {}".format(path)))

        for line in chunk:
            print(line)

        print(pad_line("? 0-6 <b f> q [m] p=" + str(page)))

        key = get_key()

        if key == 'q':
            break
        elif key == 'm':
            file_menu(path)
        elif key == 'b':
            if page > 0:
                page -= 1
        else:
            if end < len(lines):
                page += 1
            else:
                print("<END>")
                break