#!/usr/bin/python
import sys
import termios
import tty
import select
import os

fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)


def read_key():
    # Wait until at least one byte is available.
    select.select([fd], [], [])

    # Read exactly one byte from the terminal.
    ch = os.read(fd, 1)

    if not ch:
        return None

    # Normal key
    if ch != b"\x1b":
        return ch.decode(errors="replace")

    # ESC - collect the rest of an escape sequence.
    seq = ch

    while select.select([fd], [], [], 0.05)[0]:
        seq += os.read(fd, 1)

    return seq.decode(errors="replace")


def main():
    try:
        # cbreak mode + disable echo
        tty.setcbreak(fd)

        # Disable terminal echo.
        attrs = termios.tcgetattr(fd)
        attrs[3] &= ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSADRAIN, attrs)

        while True:
            key = read_key()

            if key:
                print(f"{key=}", flush=True)

    except KeyboardInterrupt:
        pass

    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


if __name__ == "__main__":
    main()
