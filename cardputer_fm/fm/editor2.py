from .utils import pad_line, get_key

# v2
def read_key():
    k = get_key()

    if k == '\x1b':  # ESC
        k2 = get_key()

        if k2 == '[':
            k3 = get_key()

            # Delete = ESC [ 3 ~
            if k3 == '3':
                get_key()  # consume '~'
                return 'DELETE'

            if k3 == 'A':
                return 'UP'
            elif k3 == 'B':
                return 'DOWN'
            elif k3 == 'C':
                return 'RIGHT'
            elif k3 == 'D':
                return 'LEFT'
        return 'ESC'
    if k == '\x13':
        return 'SAVE'      # Ctrl+S
    if k == '\x11':
        return 'QUIT'      # Ctrl+Q
    if k == '\r':
        return 'ENTER'
    if k == '\x7f':
        return 'BACKSPACE'
    return k


# ==========================================================
# WRAPPING
# ==========================================================
def build_visual_lines(lines, width):
    visual = []

    for doc_y, line in enumerate(lines):
        if line == "":
            visual.append((doc_y, 0, ""))
            continue
        start = 0
        while True:
            seg = line[start:start + width]
            visual.append(
                (doc_y, start, seg)
            )

            if start + width >= len(line):
                break

            start += width
    return visual


def doc_to_visual(visual, doc_y, real_x):
    for i, (dy, start, seg) in enumerate(visual):
        end = start + len(seg)
        if dy == doc_y and start <= real_x <= end:
            return i, real_x - start

    # Cursor at end of wrapped line
    for i in range(len(visual) - 1, -1, -1):
        dy, start, seg = visual[i]
        if dy == doc_y:
            return i, len(seg)
    return 0, 0


# ==========================================================
# EDITOR
# ==========================================================
def text_editor(path):
    try:
        with open(path, "r") as f:
            lines = [l.rstrip("\n") for l in f.readlines()]
    except:
        lines = [""]

    if not lines:
        lines = [""]

    screen_h = 7
    screen_w = 38

    # Document cursor
    doc_y = 0
    real_x = 0

    # Scroll offset in visual lines
    view_offset = 0

    dirty = False

    prev_header = None
    prev_content = [None] * screen_h
    prev_status = None

    while True:
        # ==================================================
        # BUILD VISUAL LINES
        # ==================================================
        visual = build_visual_lines(lines, screen_w)
        vis_idx, vis_x = doc_to_visual(visual,doc_y,real_x)
        vis_y = vis_idx - view_offset
        # ==================================================
        # KEEP CURSOR VISIBLE
        # ==================================================
        if vis_y < 0:
            view_offset = vis_idx
            vis_y = 0
        elif vis_y >= screen_h:
            view_offset = vis_idx - screen_h + 1
            vis_y = screen_h - 1

        # recompute after scrolling
        vis_idx, vis_x = doc_to_visual(visual,doc_y,real_x)
        vis_y = vis_idx - view_offset
        # ==================================================
        # DRAW
        # ==================================================
        header = pad_line("EDIT: {}".format(path))
        content = []
        for row in range(screen_h):
            idx = view_offset + row
            if idx >= len(visual):
                c_line = pad_line("~")
            else:
                _, _, text = visual[idx]
                if idx == vis_idx:
                    disp = list(pad_line(text))
                    if 0 <= vis_x < screen_w:
                        disp[vis_x] = "_"
                    c_line = "".join(disp)
                else:
                    c_line = pad_line(text)
            content.append(c_line)

        inner_status = "[{}:{}] {}".format(doc_y,real_x,"*" if dirty else "")
        status = pad_line(inner_status +" Ctrl+Q quit Ctrl+S save")

        # ==================================================
        # PARTIAL REDRAW
        # ==================================================
        if prev_header is None or header != prev_header:
            print("\x1b[1;1H", end="")
            print(header, end="")
            prev_header = header

        for i in range(screen_h):
            if (prev_content[i] is None or content[i] != prev_content[i]):
                print("\x1b[{};1H".format(2 + i), end="")
                print(content[i], end="")
                prev_content[i] = content[i]

        if prev_status is None or status != prev_status:
            print("\x1b[{};1H".format(2 + screen_h), end="")
            print(status, end="")
            prev_status = status

        # ==================================================
        # INPUT
        # ==================================================
        key = read_key()

        # ==================================================
        # QUIT
        # ==================================================
        if key == 'QUIT':
            if dirty:
                msg_row = 2 + screen_h + 1
                print("\x1b[{};1H".format(msg_row), end="")
                print(pad_line("Unsaved! press Ctrl+Q again"),end="")
                k2 = read_key()
                if k2 == 'QUIT':
                    break

                print("\x1b[{};1H".format(msg_row),end="")
                print(" " * screen_w,end="")
            else:
                break

        # ==================================================
        # SAVE
        # ==================================================
        elif key == 'SAVE':
            try:
                with open(path, "w") as f:
                    for l in lines:
                        f.write(l + "\n")
                dirty = False
            except Exception as e:
                msg_row = 2 + screen_h + 1
                print("\x1b[{};1H".format(msg_row),end="")
                print(pad_line("save error: {}".format(e)),end="")

        # ==================================================
        # INSERT CHAR
        # ==================================================
        elif isinstance(key, str) and len(key) == 1:
            line = lines[doc_y]
            lines[doc_y] = (line[:real_x] +key +line[real_x:])
            real_x += 1
            dirty = True
            prev_content = [None] * screen_h

        # ==================================================
        # ENTER
        # ==================================================
        elif key == 'ENTER':
            line = lines[doc_y]
            new_line = line[real_x:]
            lines[doc_y] = line[:real_x]
            lines.insert(doc_y + 1,new_line)
            doc_y += 1
            real_x = 0
            dirty = True
            prev_content = [None] * screen_h

        # ==================================================
        # BACKSPACE
        # ==================================================
        elif key == 'BACKSPACE':
            line = lines[doc_y]
            if real_x > 0:
                lines[doc_y] = (line[:real_x - 1] +line[real_x:])
                real_x -= 1
            elif doc_y > 0:
                prev_len = len(lines[doc_y - 1])
                lines[doc_y - 1] += line
                lines.pop(doc_y)
                doc_y -= 1
                real_x = prev_len
            dirty = True
            prev_content = [None] * screen_h

        # ==================================================
        # DELETE
        # ==================================================
        elif key == 'DELETE':
            line = lines[doc_y]
            if real_x < len(line):
                lines[doc_y] = (line[:real_x] +line[real_x + 1:])
            elif doc_y < len(lines) - 1:
                lines[doc_y] += lines[doc_y + 1]
                lines.pop(doc_y + 1)
            dirty = True
            prev_content = [None] * screen_h

        # ==================================================
        # LEFT
        # ==================================================
        elif key == 'LEFT':
            if real_x > 0:
                real_x -= 1
            elif doc_y > 0:
                doc_y -= 1
                real_x = len(lines[doc_y])

        # ==================================================
        # RIGHT
        # ==================================================
        elif key == 'RIGHT':
            if real_x < len(lines[doc_y]):
                real_x += 1
            elif doc_y < len(lines) - 1:
                doc_y += 1
                real_x = 0

        # ==================================================
        # UP
        # ==================================================
        elif key == 'UP':
            visual = build_visual_lines(lines,screen_w)
            vis_idx, vis_x = doc_to_visual(visual,doc_y,real_x)
            if vis_idx > 0:
                target_doc_y, target_start, target_seg = \
                    visual[vis_idx - 1]
                doc_y = target_doc_y
                real_x = min(target_start + vis_x,len(lines[doc_y]))

        # ==================================================
        # DOWN
        # ==================================================
        elif key == 'DOWN':
            visual = build_visual_lines(lines,screen_w)
            vis_idx, vis_x = doc_to_visual(visual,doc_y,real_x)
            if vis_idx < len(visual) - 1:
                target_doc_y, target_start, target_seg = \
                    visual[vis_idx + 1]
                doc_y = target_doc_y
                real_x = min(target_start + vis_x,len(lines[doc_y]))

        # ==================================================
        # CLAMPS
        # ==================================================
        if doc_y < 0:
            doc_y = 0

        if doc_y >= len(lines):
            doc_y = len(lines) - 1

        if real_x < 0:
            real_x = 0

        if real_x > len(lines[doc_y]):
            real_x = len(lines[doc_y])
