import os
import time

from .utils import pad_line, get_key


# ---------- HELPERS ----------
def get_dir_name(path):
    if path == "/":
        return "/"
    return path.rstrip("/").split("/")[-1]


def format_time(ts):
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
    except:
        return "N/A"

def copy_file(src, dst):
    print("CopyFile ", src, " to ", dst)
    with open(src, "rb") as fsrc:
        with open(dst, "wb") as fdst:  # "wb" already overwrites
            while True:
                chunk = fsrc.read(512)
                if not chunk:
                    break
                fdst.write(chunk)

def is_dir(path):
    return os.stat(path)[0] & 0x4000

def copy_dir(src, dst):
    print("CopyDir ", src, " to ", dst)

    # Create directory only if it doesn't exist
    try:
        os.mkdir(dst)
    except OSError:
        pass  # already exists

    for name in os.listdir(src):
        s = src.rstrip("/") + "/" + name
        d = dst.rstrip("/") + "/" + name

        try:
            if is_dir(s):
                copy_dir(s, d)
            else:
                copy_file(s, d)
        except Exception as e:
            print("copy error:", e)

def remove_dir(path):
    for name in os.listdir(path):
        full = path.rstrip("/") + "/" + name
        try:
            if os.stat(full)[0] & 0x4000:
                remove_dir(full)
            else:
                print('Remove: ', full)
                os.remove(full)
        except Exception as e:
            print("remove error:", e)

    try:
        print('Remove: ', path)
        os.rmdir(path)
    except Exception as e:
        print("rmdir error:", e)


def move_dir(src, dst):
    try:
        os.rename(src, dst)
    except:
        # fallback if rename fails (e.g. cross-device)
        copy_dir(src, dst)
        remove_dir(src)


# ---------- DIR MENU ----------
def dir_menu(path):
    blacklist = ["/"]

    try:
        stat = os.stat(path)
        ctime = format_time(stat[8] if len(stat) > 8 else stat[9])
        mtime = format_time(stat[9] if len(stat) > 9 else stat[8])
    except:
        ctime = "N/A"
        mtime = "N/A"

    while True:
        print()
        print(pad_line(f"D: {get_dir_name(path)}"))
        print(pad_line(f"C: {ctime}"))
        print(pad_line(f"M: {mtime}"))

        print("1 create file")
        print("2 create dir")
        print("3 copy to | 4 move to")
        print("5 rename")
        print("6 remove")
        print(pad_line("> 1-6 q"))

        key = get_key()

        if key == 'q':
            break

        # ---------- CREATE FILE ----------
        elif key == '1':
            name = input("file name: ").strip()
            if name:
                try:
                    full = path.rstrip("/") + "/" + name
                    with open(full, "w") as f:
                        pass
                    print("created:", full)
                except Exception as e:
                    print("error:", e)

        # ---------- CREATE DIR ----------
        elif key == '2':
            name = input("dir name: ").strip()
            if name:
                try:
                    full = path.rstrip("/") + "/" + name
                    os.mkdir(full)
                    print("created:", full)
                except Exception as e:
                    print("error:", e)

        # ---------- COPY ----------
        elif key == '3':
            dest = input("copy to: ").strip()
            if dest:
                try:
                    name = get_dir_name(path)
                    target = dest.rstrip("/") + "/" + name
                    copy_dir(path, target)
                    print("copied to:", target)
                except Exception as e:
                    print("error:", e)

        # ---------- MOVE ----------
        elif key == '4':
            dest = input("move to: ").strip()
            if dest:
                try:
                    name = get_dir_name(path)
                    target = dest.rstrip("/") + "/" + name
                    move_dir(path, target)
                    print("moved to:", target)
                    break
                except Exception as e:
                    print("error:", e)

        # ---------- RENAME ----------
        elif key == '5':
            new_name = input("new name: ").strip()
            if new_name:
                try:
                    parent = "/".join(path.rstrip("/").split("/")[:-1])
                    if parent == "":
                        parent = "/"
                    target = parent.rstrip("/") + "/" + new_name
                    os.rename(path, target)
                    print("renamed to:", target)
                    break
                except Exception as e:
                    print("error:", e)

        # ---------- REMOVE ----------
        elif key == '6':
            if path in blacklist:
                print("cannot remove:", path)
                continue

            confirm = input("confirm delete (y/n): ").strip().lower()
            if confirm == 'y':
                try:
                    remove_dir(path)
                    print("removed:", path)
                    break
                except Exception as e:
                    print("error:", e)
