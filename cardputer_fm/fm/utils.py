import sys
import os

# ---------- KEY INPUT ----------
def get_key():
    try:
        import supervisor
        while not supervisor.runtime.serial_bytes_available:
            pass
        return sys.stdin.read(1)
    except:
        return input()[0]


# ---------- FORMAT LINE ----------
def pad_line(text, width=38):
    if len(text) >= width:
        return text[:width]
    return text + "-" * (width - len(text))


# ---------- TEXT WRAP ----------
def wrap_line(line, width=38):
    lines = []
    while len(line) > width:
        lines.append(line[:width])
        line = line[width:]
    lines.append(line)
    return lines

def clear():
	sys.stderr.write("\x1b[2J\x1b[H")

# ---------- BINARY DETECTION ----------
def is_binary_file(path, sample_size=512):
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
            if not chunk:
                return False  # empty file = treat as text

            # Null byte check (strong binary indicator)
            if b"\x00" in chunk:
                return True

            # Count non-text bytes
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(32, 127)))
            nontext = sum(1 for b in chunk if b not in text_chars)

            # If more than 30% non-text → binary
            return (nontext / len(chunk)) > 0.3

    except:
        return True  # safest fallback