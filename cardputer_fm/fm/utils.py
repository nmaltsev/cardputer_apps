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
    return text + "_" * (width - len(text))


# ---------- TEXT WRAP ----------
def wrap_line(line, width=37):
    lines = []
    while len(line) > width:
        lines.append(line[:width])
        line = line[width:]
    lines.append(line)
    return lines

def clear():
	# sys.stderr.write("\x1b[2J\x1b[H")
    print(chr(27)+"[2J")

# ---------- BINARY DETECTION ----------
def is_text_file(path):
    # Whitelisted text extensions (lowercase, no allocation-heavy ops)
    TEXT_EXTS = (
        ".py", ".yaml", ".yml", '.bat',
        ".txt", ".log", ".htm", ".html", ".xml",
        ".toml", ".json", ".md", ".js", ".css"
    )

    # Extract filename (avoid os.path to keep it lightweight)
    name = path.rsplit("/", 1)[-1]

    # Find extension
    dot = name.rfind(".")
    if dot == -1:
        return False

    ext = name[dot:].lower()

    # Check against whitelist
    for e in TEXT_EXTS:
        if ext == e:
            return True

    return False
