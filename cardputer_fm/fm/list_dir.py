import os
from .utils import pad_line, get_key, clear, is_binary_file
from .type import type_file
from .dir_menu import dir_menu
from .hex_view_streaming import hex_view

# ---------- FILE MANAGER ----------
def list_dir(path='/'):
    page_size = 7
    page = 0

    while True:
        try:
            entries = sorted(os.listdir(path))
        except Exception as e:
            print("Error:", e)
            return

        # Add parent directory
        if path != "/":
            entries = [".."] + entries
        # entries = [".."] + entries

        start = page * page_size
        end = start + page_size
        chunk = entries[start:end]

        #print()
        # clear()
        print(pad_line(">{} {}".format(path, path != '/')))

        for i, name in enumerate(chunk):
            print("{} {}".format(i, name))

        if (len(chunk) < page_size):
            print('\n' * (page_size - len(chunk) -1))

        # m - means menu (file_size, creation_date, modification_date, remove, rename, move, edit)
        print(pad_line("? 0-" + str(page_size - 1) +" <bf> q t [m] p:"+str(page)))

        key = get_key()
        
        if key == 'q':
            break

        if key == 't':
            return

        elif key == 'b':
            if page > 0:
                page -= 1

        elif key == 'f':
            if end < len(entries):
                page += 1

        elif key == 'm':
            dir_menu(path)

        elif key.isdigit():
            idx = int(key)
            if idx < len(chunk):
                selected = chunk[idx]

                # Handle parent directory
                if selected == "..":
                    if path != "/":
                        path = "/".join(path.rstrip("/").split("/")[:-1])
                        if path == "":
                            path = "/"
                        page = 0
                    continue

                full_path = path.rstrip("/") + "/" + selected

                try:
                    if os.stat(full_path)[0] & 0x4000:
                        list_dir(full_path)
                    else:
                        type_file(full_path)
                        # if is_binary_file(full_path):
                        #     hex_view(full_path)
                        # else:
                        #     type_file(full_path)
                except Exception as exc:
                    print("[DIR]Cannot access:", full_path)
                    print(exc)

        # Reset page if out of range
        if page * page_size >= len(entries):
            page = 0