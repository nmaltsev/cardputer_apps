import platform
import subprocess

clipboard = ""
USE_OS_CLIPBOARD = True


def copy_to_clipboard(text):
    global clipboard

    if not USE_OS_CLIPBOARD:
        clipboard = text
        return

    system = platform.system()

    try:
        if system == "Darwin":
            p = subprocess.Popen(
                ["pbcopy"],
                stdin=subprocess.PIPE
            )
            p.communicate(text.encode("utf-8"))

        elif system == "Linux":
            p = subprocess.Popen(
                ["xclip", "-selection", "clipboard"],
                stdin=subprocess.PIPE
            )
            p.communicate(text.encode("utf-8"))

        else:
            clipboard = text

    except Exception:
        clipboard = text


def paste_from_clipboard():
    global clipboard

    if not USE_OS_CLIPBOARD:
        return clipboard

    system = platform.system()

    try:
        if system == "Darwin":
            return subprocess.check_output(
                ["pbpaste"]
            ).decode("utf-8")

        elif system == "Linux":
            return subprocess.check_output(
                ["xclip", "-selection", "clipboard", "-o"]
            ).decode("utf-8")

    except Exception:
        pass

    return clipboard