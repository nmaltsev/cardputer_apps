import sys
import os
import json

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
    # print(chr(27)+"[2J")
    print("\x1b[2J\x1b[H", end='')

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

def open_settings():
    try:
        # Detect current script directory
        try:
            base_dir = os.path.dirname(__file__)
            if not base_dir:
                base_dir = "/"
        except:
            base_dir = "/"

        settings_path = base_dir + "/settings.json"

        # Create default settings if missing
        if "settings.json" not in os.listdir(base_dir):
            default_settings = {
                "wifi": {
                    "known": [
                        {"ssid": "", "password": ""}
                    ],
                    "default": "ssid"
                },
                "brightness": 0.3
            }

            try:
                with open(settings_path, "w") as f:
                    json.dump(default_settings, f)
                print("Created settings.json")
            except Exception as e:
                print("Error creating settings.json:", e)
                return

        # Open editor
        try:
            from .editor import text_editor
            text_editor(settings_path)
        except Exception as e:
            print("Error opening editor:", e)

    except Exception as e:
        print("Settings error:", e)