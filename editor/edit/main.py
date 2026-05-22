import sys
import os
import subprocess
import platform
from .utils import get_key, clear, move_cursor

# --- ORIGINAL FUNCTIONS (preserved) ---
def fill(text, max_width):
    if len(text) >= max_width:
        return text[0:max_width]
    else:
        return text + '-' * (max_width - len(text))

view_box1 = (1,1,40,10)  # x,y,w,h (immutable!)

# --- DOCUMENT MODEL ---
doc_lines = [""]
view_offset = 0
file_path = None

# --- SELECTION / CLIPBOARD ---
clipboard = ""

selection_active = False
selection_anchor = None
selection_end = None
selection_in_progress = False

# =========================================================
# CLIPBOARD CONFIG
# =========================================================

USE_OS_CLIPBOARD = True

def copy_to_clipboard(text):
    global clipboard

    if not USE_OS_CLIPBOARD:
        clipboard = text
        return

    system = platform.system()

    try:
        # macOS 10.12–10.15
        if system == "Darwin":
            p = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            p.communicate(text.encode("utf-8"))

        # Ubuntu/Linux
        elif system == "Linux":
            p = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
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
        # macOS
        if system == "Darwin":
            return subprocess.check_output(["pbpaste"]).decode("utf-8")

        # Ubuntu/Linux
        elif system == "Linux":
            return subprocess.check_output(["xclip", "-selection", "clipboard", "-o"]).decode("utf-8")
    except Exception:
        pass

    return clipboard


# --- FILE IO ---
def load_file(path):
    global doc_lines

    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            doc_lines = f.read().splitlines()

        if not doc_lines:
            doc_lines = [""]
    else:
        doc_lines = [""]


def save_file(path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(doc_lines))


# --- SELECTION HELPERS ---

def normalize_selection():
    if not selection_anchor or not selection_end:
        return None

    a = selection_anchor
    b = selection_end

    if a <= b:
        return a,b

    return b,a


def has_selection():
    r = normalize_selection()

    if not r:
        return False
    a,b = r
    return a != b


def clear_selection():
    global selection_active
    global selection_anchor
    global selection_end
    global selection_in_progress

    selection_active=False
    selection_anchor=None
    selection_end=None
    selection_in_progress=False


def begin_selection(row,col):
    global selection_active
    global selection_anchor
    global selection_end
    global selection_in_progress

    if not selection_active:
        selection_active=True
        selection_anchor=(row,col)

    selection_end=(row,col)
    selection_in_progress=True


def update_selection(row,col):
    global selection_end
    selection_end=(row,col)


def finalize_selection():
    global selection_in_progress
    selection_in_progress=False


def get_selected_text():
    r=normalize_selection()

    if not r:
        return ""

    (r1,c1),(r2,c2)=r

    if r1==r2:
        return doc_lines[r1][c1:c2]

    out=[]
    out.append(doc_lines[r1][c1:])

    for y in range(r1+1,r2):
        out.append(doc_lines[y])

    out.append(doc_lines[r2][:c2])

    return "\n".join(out)


def delete_selection():
    r=normalize_selection()

    if not r:
        return None
    (r1,c1),(r2,c2)=r

    if r1==r2:
        line=doc_lines[r1]
        doc_lines[r1]=(line[:c1]+line[c2:])
    else:
        first=doc_lines[r1][:c1]
        last=doc_lines[r2][c2:]
        doc_lines[r1]=first+last
        del doc_lines[r1+1:r2+1]
    clear_selection()
    return r1,c1


def insert_text(row,col,text):
    parts=text.split("\n")
    line=doc_lines[row]
    before=line[:col]
    after=line[col:]
    if len(parts)==1:
        doc_lines[row]=(before+text+after)

        return row,col+len(text)

    doc_lines[row]=before+parts[0]
    insert_pos=row+1
    for p in parts[1:-1]:
        doc_lines.insert(insert_pos, p)
        insert_pos+=1

    doc_lines.insert(insert_pos, parts[-1]+after)

    return insert_pos,len(parts[-1])


def replace_selection(text):
    pos=delete_selection()

    if pos is None:
        return None

    row,col=pos

    return insert_text(row, col,text)


# --- WRAPPING ---
def build_visual_lines():
    visual=[]
    width=view_box1[2]

    for doc_y,line in enumerate(doc_lines):
        if line=="":
            visual.append((doc_y,0,""))

            continue
        start=0
        while True:
            segment=line[start:start+width]
            visual.append((doc_y, start, segment))

            if start+width>=len(line):
                break

            start+=width
    return visual


# --- RENDER ---
def fill_view_box(view_box, visual_lines, cursor=None):
    for i in range(view_box[3]):
        move_cursor(view_box[0], view_box[1]+i)
        idx=view_offset+i
        if idx<len(visual_lines):
            _,_,text=(visual_lines[idx])
        else:
            text=""

        # --- INLINE CURSOR ---
        if cursor and i==cursor[1]:
            cx=cursor[0]
            if cx>=len(text):
                text=text+"_"
            else:
                text=(text[:cx] + "_" + text[cx:])
        print(fill(text, view_box[2]), end='')
    sys.stdout.flush()


# --- STATUS BAR ---
def draw_status(doc_y,real_x,ch,path):
    y=view_box1[1]+view_box1[3]
    move_cursor(view_box1[0],y)

    if has_selection():
        (r1,c1),(r2,c2)=(normalize_selection())

        status=(
            f"({r1+1},{c1+1},"
            f"{r2+1},{c2+1}) "
            f"{path}"
        )
    else:
        status=(
            f"({doc_y+1}:{real_x+1}) "
            f"{repr(ch)} "
            f"{path}"
        )
    print(fill(status,view_box1[2]),end='')

    sys.stdout.flush()


# --- MAIN ---
def main():

    global view_offset
    global file_path

    clear()

    # --- CLI ARG ---
    if len(sys.argv)>1:
        file_path=sys.argv[1]
        load_file(file_path)
    else:
        file_path=("untitled.txt")
    prev=None
    EDIT_MODE=False
    cursor_offset=[0,0]
    while True:
        key=get_key()
        if EDIT_MODE is False:
            print(f"{key=}")

        # --- EXIT ---
        if (key=="CTRL_C" and prev=="CTRL_C"):
            clear()
            break

        # --- CLEAR ---
        if key=="CTRL_W":
            clear()

        # --- SAVE ---
        if key=="CTRL_S":
            save_file(file_path)

        # --- ENTER EDIT MODE ---
        if key=="CTRL_P":
            EDIT_MODE=True
            cursor_offset=[0,0]
            clear()

        if EDIT_MODE:
            visual=build_visual_lines()
            cx,cy=cursor_offset
            vis_idx=(view_offset+cy)

            if vis_idx>=len(visual):
                vis_idx=(len(visual)-1)

            doc_y,start_idx,segment=(visual[vis_idx])
            line=doc_lines[doc_y]
            real_x=start_idx+cx

            shift_move=key in ('SHIFT+LEFT','SHIFT+RIGHT','SHIFT+UP','SHIFT+DOWN')

            if shift_move:
                if not selection_in_progress:
                    begin_selection(doc_y,real_x)
            else:
                if selection_in_progress:
                    finalize_selection()

            # ==================================================
            # SELECTION OPERATIONS
            # ==================================================
            if has_selection():
                if key=="CTRL_C":
                    copy_to_clipboard(get_selected_text())
                    prev=key
                    continue
                elif key=="CTRL_X":
                    copy_to_clipboard(get_selected_text())
                    pos=delete_selection()
                    if pos:
                        doc_y,real_x=pos
                elif key in ("DELETE","BACKSPACE"):
                    pos=delete_selection()
                    if pos:
                        doc_y,real_x=pos
                elif len(key)==1:
                    pos=replace_selection(key)

                    if pos:
                        doc_y,real_x=pos
                elif not shift_move:
                    clear_selection()

            # ==================================================
            # INPUT
            # ==================================================

            if key=="CTRL_V":
                text=(paste_from_clipboard())
                if has_selection():
                    pos=replace_selection(text)
                    if pos:
                        doc_y,real_x=pos
                else:
                    doc_y,real_x=(insert_text(doc_y,real_x,text))
            elif len(key)==1:
                line=doc_lines[doc_y]
                line=(line[:real_x]+key+line[real_x:]                )
                doc_lines[doc_y]=line
                real_x+=1
            elif key=="ENTER":
                line=doc_lines[doc_y]
                new_line=(line[real_x:])
                doc_lines[doc_y]=(line[:real_x])
                doc_lines.insert(doc_y+1,new_line)
                doc_y+=1
                real_x=0
            elif key=="BACKSPACE":
                line=doc_lines[doc_y]
                if real_x>0:
                    line=(line[:real_x-1]+line[real_x:])
                    doc_lines[doc_y]=line
                    real_x-=1
                elif doc_y>0:
                    prev_line=(doc_lines[doc_y-1])
                    real_x=len(prev_line)
                    doc_lines[doc_y-1]=(prev_line+line)
                    doc_lines.pop(doc_y)
                    doc_y-=1
            elif key=="DELETE":
                line=doc_lines[doc_y]
                if real_x<len(line):
                    line=(
                        line[:real_x]
                        +line[
                            real_x+1:
                        ]
                    )

                    doc_lines[
                        doc_y
                    ]=line

                elif (
                    doc_y
                    <
                    len(doc_lines)-1
                ):

                    doc_lines[
                        doc_y
                    ]+=doc_lines[
                        doc_y+1
                    ]

                    doc_lines.pop(
                        doc_y+1
                    )

            # ==================================================
            # NAVIGATION
            # ==================================================

            elif key in (
                "LEFT",
                "SHIFT+LEFT"
            ):

                if real_x>0:

                    real_x-=1

                elif doc_y>0:

                    doc_y-=1

                    real_x=len(
                        doc_lines[
                            doc_y
                        ]
                    )

            elif key in (
                "RIGHT",
                "SHIFT+RIGHT"
            ):

                if real_x<len(line):

                    real_x+=1

                elif (
                    doc_y
                    <
                    len(doc_lines)-1
                ):

                    doc_y+=1
                    real_x=0

            elif key in (
                "UP",
                "SHIFT+UP"
            ):

                if doc_y>0:

                    doc_y-=1

                    real_x=min(
                        real_x,
                        len(
                            doc_lines[
                                doc_y
                            ]
                        )
                    )

            elif key in (
                "DOWN",
                "SHIFT+DOWN"
            ):

                if (
                    doc_y
                    <
                    len(doc_lines)-1
                ):

                    doc_y+=1

                    real_x=min(
                        real_x,
                        len(
                            doc_lines[
                                doc_y
                            ]
                        )
                    )

            if shift_move:

                update_selection(
                    doc_y,
                    real_x
                )

            # ==================================================
            # MAP DOCUMENT POSITION -> VISUAL POSITION
            # ==================================================

            visual=build_visual_lines()

            new_vis_idx=0

            for i,(dy,start,seg) in enumerate(
                visual
            ):

                if (
                    dy==doc_y
                    and
                    start<=real_x<=(
                        start+len(seg)
                    )
                ):

                    new_vis_idx=i
                    break

            dy,start,seg=(
                visual[
                    new_vis_idx
                ]
            )

            cx=real_x-start

            cy=(
                new_vis_idx
                -view_offset
            )

            # ==================================================
            # SCROLLING
            # ==================================================

            if cy<0:

                view_offset=(
                    new_vis_idx
                )

                cy=0

            elif cy>=view_box1[3]:

                view_offset=(
                    new_vis_idx
                    -view_box1[3]
                    +1
                )

                cy=(
                    view_box1[3]-1
                )

            cursor_offset=[cx,cy]

            # ==================================================
            # RENDER
            # ==================================================

            fill_view_box(
                view_box1,
                visual,
                cursor=(cx,cy)
            )

            ch=''

            if (
                doc_y
                <
                len(doc_lines)
            ):

                if (
                    real_x
                    <
                    len(
                        doc_lines[
                            doc_y
                        ]
                    )
                ):

                    ch=doc_lines[
                        doc_y
                    ][real_x]

            draw_status(
                doc_y,
                real_x,
                ch,
                file_path
            )

        prev=key


if __name__=="__main__":
    main()