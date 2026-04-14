from .utils import pad_line, get_key


# ---------- FORMAT ONE LINE ----------
def format_hex_line(offset, chunk):
    hex_part = " ".join("{:02X}".format(b) for b in chunk)
    ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)

    # pad hex part for alignment (16 bytes per line)
    hex_part = hex_part.ljust(16 * 3 - 1)

    return "{:08X}  {}  {}".format(offset, hex_part, ascii_part)


# ---------- HEX VIEWER ----------
def hex_view(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception as e:
        print("Error opening file:", e)
        return

    bytes_per_line = 16
    page_size = 7

    lines = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i + bytes_per_line]
        lines.append(format_hex_line(i, chunk))

    page = 0

    while True:
        start = page * page_size
        end = start + page_size
        chunk = lines[start:end]

        print()
        print(pad_line("HEX: {}".format(path)))

        for line in chunk:
            print(line)

        print(pad_line("> d,u,q p=" + str(page)))

        key = get_key()

        if key == 'q':
            break
        elif key == 'u':
            if page > 0:
                page -= 1
        else:
            if end < len(lines):
                page += 1
            else:
                print("<END>")
                break