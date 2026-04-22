from .utils import pad_line, get_key
import os


# ---------- FORMAT ONE LINE ----------
def format_hex_line(offset, chunk):
    hex_part = " ".join("{:02X}".format(b) for b in chunk)
    ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)

    target_len = 16 * 3 - 1
    if len(hex_part) < target_len:
        hex_part = hex_part + " " * (target_len - len(hex_part))

    return "{:08X}  {}  {}".format(offset, hex_part, ascii_part)


# ---------- HEX VIEWER (STREAMING) ----------
def hex_view(path):
    try:
        size = os.stat(path)[6]  # file size
    except:
        print("[HEX]Cannot access:", path)
        return

    bytes_per_line = 16
    lines_per_page = 4
    page_size_bytes = bytes_per_line * lines_per_page

    offset = 0

    while True:
        try:
            with open(path, "rb") as f:
                f.seek(offset)
                data = f.read(page_size_bytes)
        except Exception as e:
            print("Error:", e)
            return

        print()
        print(pad_line("HEX: {} [{}]".format(path, offset)))

        # Render lines
        for i in range(0, len(data), bytes_per_line):
            chunk = data[i:i + bytes_per_line]
            print(format_hex_line(offset + i, chunk))

        print(pad_line("? b,f,q off=" + str(offset)))

        key = get_key()

        if key == 'q':
            break

        elif key == 'b':
            offset -= page_size_bytes
            if offset < 0:
                offset = 0

        elif key == 'f':
            if offset + page_size_bytes < size:
                offset += page_size_bytes
            else:
                print("<END>")
