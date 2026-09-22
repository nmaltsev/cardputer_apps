from .utils import pad_line, wrap_line, get_key
from .file_menu import file_menu



def read_page(path, offset, page_length, page_width):
    """Read one display page starting at offset.

    Returns:
        lines: display lines for the page
        next_offset: file offset for the next page
    """
    lines = []

    with open(path, "r") as f:
        f.seek(offset)

        while len(lines) < page_length:
            line = f.readline()

            if not line:
                # End of file.
                return lines, f.tell()

            line = line.rstrip("\n")
            wrapped = wrap_line(line)

            for part in wrapped:
                if len(lines) >= page_length:
                    break

                lines.append(part)

            # Remember where the next logical line starts.
            next_offset = f.tell()

    return lines, next_offset


# ---------- TYPE FUNCTION ----------
def type_file(path):
    # try:
    #     with open(path, "r") as f:
    #         raw_lines = f.readlines()
    # except Exception as e:
    #     print("Error opening file:", e)
    # with open(path, "r") as f:
    #     raw_lines = f.readlines()

    page_length = 8
    page_width = 39

    page = 0
    page_offsets = [0]

    while True:
        offset = page_offsets[page]

        lines, next_offset = read_page(
            path,
            offset,
            page_length,
            page_width
        )

        if not lines:
            print("<END>")
            break

        chunk = lines

        print()
        print(pad_line("b {}".format(path), width=page_width))

        for i in range(page_length):
            if i < len(chunk):
                print("{} {}".format(i, chunk[i]))
            else:
                print()  # empty line

        print(
            pad_line(
                "f q,m,e p=" + str(page),
                width=page_width
            ),
            end=''
        )

        key = get_key()

        if key == 'q':
            break

        elif key == 'm':
            file_menu(path)

        elif key == 'b':
            if page > 0:
                page -= 1

        elif key == 'e':
            from .editor import main as text_editor
            text_editor(path)

        else:
            if len(lines) == page_length:
                page_offsets.append(next_offset)
                page += 1
            else:
                print("<END>")
                break