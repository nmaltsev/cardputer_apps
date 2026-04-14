import os
import time

from .utils import pad_line, get_key


# ---------- HELPERS ----------
def format_time(ts):
    try:
        t = time.localtime(ts)

        def pad(n):
            return '0' + str(n) if n < 10 else str(n)

        return (
            str(t[0]) + "-" +
            pad(t[1]) + "-" +
            pad(t[2]) + " " +
            pad(t[3]) + ":" +
            pad(t[4]) + ":" +
            pad(t[5])
        )
    except:
        return "N/A"


def copy_file(src, dst):
    with open(src, "rb") as fsrc:
        with open(dst, "wb") as fdst:
            while True:
                chunk = fsrc.read(512)
                if not chunk:
                    break
                fdst.write(chunk)


# ---------- FILE MENU ----------
def file_menu(path):
    try:
        stat = os.stat(path)
        size = stat[6]
        ctime = format_time(stat[8] if len(stat) > 8 else stat[9])
        mtime = format_time(stat[9] if len(stat) > 9 else stat[8])
    except:
        size = 0
        ctime = "N/A"
        mtime = "N/A"

    name = path.rstrip("/").split("/")[-1]

    while True:
        print()
        print(pad_line(f"F: {name}"))
        print(pad_line(f"S: {size}"))
        print(pad_line(f"C: {ctime}"))
        print(pad_line(f"M: {mtime}"))

        print("1 rename")
        print("2 append line")
        print("3 delete last line")
        print("4 remove file")
        print("5 copy file")
        print(pad_line("> 1-5 q"))

        key = get_key()

        if key == 'q':
            break

        # ---------- RENAME ----------
        elif key == '1':
            new_path = input("new path/name: ").strip()
            if new_path:
                try:
                    if not new_path.startswith("/"):
                        parent = "/".join(path.rstrip("/").split("/")[:-1])
                        if parent == "":
                            parent = "/"
                        new_path = parent.rstrip("/") + "/" + new_path

                    os.rename(path, new_path)
                    print("renamed to:", new_path)
                    break
                except Exception as e:
                    print("error:", e)

        # ---------- APPEND LINE ----------
        elif key == '2':
            line = input("append: ")
            if line:
                try:
                    with open(path, "a") as f:
                        f.write(line + "\n")
                    print("appended")
                except Exception as e:
                    print("error:", e)

        # ---------- DELETE LAST LINE ----------
        elif key == '3':
            try:
                with open(path, "r") as f:
                    lines = f.readlines()

                if not lines:
                    print("empty file")
                    continue

                lines = lines[:-1]

                with open(path, "w") as f:
                    f.writelines(lines)

                print("last line removed")
            except Exception as e:
                print("error:", e)

        # ---------- REMOVE ----------
        elif key == '4':
            confirm = input("confirm delete (y/n): ").strip().lower()
            if confirm == 'y':
                try:
                    os.remove(path)
                    print("removed:", path)
                    break
                except Exception as e:
                    print("error:", e)

        # ---------- COPY ----------
        elif key == '5':
            dest = input("copy to: ").strip()
            if dest:
                try:
                    if not dest.endswith("/"):
                        target = dest
                    else:
                        name = path.rstrip("/").split("/")[-1]
                        target = dest.rstrip("/") + "/" + name

                    copy_file(path, target)
                    print("copied to:", target)
                except Exception as e:
                    print("error:", e)