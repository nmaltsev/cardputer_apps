import sys
import os

def clear():
    sys.stdout.write("\x1b[2J\x1b[H")
    # print("\x1b[2J\x1b[H", end='')

def move_cursor(x, y):
    sys.stdout.write(f"\x1b[{y+1};{x+1}H")

CTRL_KEYS = {
    "\x03": "CTRL_C",
    "\x04": "CTRL_D",
    "\x08": "BACKSPACE",
    "\x7f": "BACKSPACE",
    "\r": "ENTER",
    "\n": "ENTER",
    "\t": "TAB",
    "\x1b": "ESC",
}

def get_key():
    try:
        ch = sys.stdin.read(1)

        # Named control keys
        if ch in CTRL_KEYS:
            return CTRL_KEYS[ch]

        # CTRL+A ... CTRL+Z
        code = ord(ch)
        if 1 <= code <= 26:
            return f"CTRL_{chr(code + 64)}"

        return ch
    except Exception as exc:
        print("get_key error: ", exc)    

# --- ORIGINAL FUNCTIONS (preserved) ---
def fill(text, max_width):
    if len(text) >= max_width:
        return text[0:max_width]
    else:
        return text + '-' * (max_width - len(text))

view_box1 = (0,0,40,8)  # x,y,w,h (immutable!)

# --- DOCUMENT MODEL (state object to avoid global) ---
class EditorState:
    def __init__(self):
        self.doc_lines = [""]
        self.view_offset = 0
        self.file_path = None
        self.clipboard = ""
        self.selection_active = False
        self.selection_anchor = None
        self.selection_end = None
        self.selection_in_progress = False

state = EditorState()

# --- SELECTION / CLIPBOARD ---
# (state holds clipboard and selection fields)

# =========================================================
# CLIPBOARD CONFIG
# =========================================================


def copy_to_clipboard(text):
    state.clipboard = text

def paste_from_clipboard():
    return state.clipboard


# --- FILE IO ---
def load_file(path):
    if os.path.exists(path):
        with open(path, 'r') as f:
            state.doc_lines = f.read().split("\n")

        if not state.doc_lines:
            state.doc_lines = [""]
    else:
        state.doc_lines = [""]


def save_file(path):
    with open(path, 'w') as f:
        f.write("\n".join(state.doc_lines))


# --- SELECTION HELPERS ---

def normalize_selection():
    if state.selection_anchor is None or state.selection_end is None:
        return None

    a = state.selection_anchor
    b = state.selection_end

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
    state.selection_active=False
    state.selection_anchor=None
    state.selection_end=None
    state.selection_in_progress=False


def begin_selection(row,col):
    if not state.selection_active:
        state.selection_active=True
        state.selection_anchor=(row,col)

    state.selection_end=(row,col)
    state.selection_in_progress=True


def update_selection(row,col):
    state.selection_end=(row,col)


def finalize_selection():
    state.selection_in_progress=False


def get_selected_text():
    r=normalize_selection()

    if not r:
        return ""

    (r1,c1),(r2,c2)=r

    if r1==r2:
        return state.doc_lines[r1][c1:c2]

    out=[]
    out.append(state.doc_lines[r1][c1:])

    for y in range(r1+1,r2):
        out.append(state.doc_lines[y])

    out.append(state.doc_lines[r2][:c2])

    return "\n".join(out)


def delete_selection():
    r=normalize_selection()

    if not r:
        return None
    (r1,c1),(r2,c2)=r

    if r1==r2:
        line=state.doc_lines[r1]
        state.doc_lines[r1]=(line[:c1]+line[c2:])
    else:
        first=state.doc_lines[r1][:c1]
        last=state.doc_lines[r2][c2:]
        state.doc_lines[r1]=first+last
        del state.doc_lines[r1+1:r2+1]
    clear_selection()
    return r1,c1


def insert_text(row,col,text):
    parts=text.split("\n")
    line=state.doc_lines[row]
    before=line[:col]
    after=line[col:]
    if len(parts)==1:
        state.doc_lines[row]=(before+text+after)

        return row,col+len(text)

    state.doc_lines[row]=before+parts[0]
    insert_pos=row+1
    for p in parts[1:-1]:
        state.doc_lines.insert(insert_pos, p)
        insert_pos+=1

    state.doc_lines.insert(insert_pos, parts[-1]+after)

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

    for doc_y,line in enumerate(state.doc_lines):
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
        idx=state.view_offset+i
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
def main(path):
    clear()

    # --- CLI ARG ---
    if path is not None:
        state.file_path=path
        load_file(state.file_path)
    else:
        state.file_path="untitled.txt"
    prev=None
    EDIT_MODE=False
    cursor_offset=[0,0]
    while True:
        key=get_key()
        if EDIT_MODE is False:
            print(f"{key=}")

        # --- EXIT ---
        if (key=="CTRL_Q" and prev=="CTRL_Q"):
            clear()
            break

        # --- CLEAR ---
        if key=="CTRL_W":
            clear()

        # --- SAVE ---
        if key=="CTRL_S":
            save_file(state.file_path)

        # --- ENTER EDIT MODE ---
        if key=="CTRL_P":
            EDIT_MODE=True
            cursor_offset=[0,0]
            clear()

        if EDIT_MODE:
            visual=build_visual_lines()
            cx,cy=cursor_offset
            vis_idx=(state.view_offset+cy)

            if vis_idx>=len(visual):
                vis_idx=(len(visual)-1)

            doc_y,start_idx,segment=(visual[vis_idx])
            line=state.doc_lines[doc_y]
            real_x=start_idx+cx

            shift_move=key in ('SHIFT+LEFT','SHIFT+RIGHT','SHIFT+UP','SHIFT+DOWN')

            if shift_move:
                if not state.selection_in_progress:
                    begin_selection(doc_y,real_x)
            else:
                if state.selection_in_progress:
                    finalize_selection()

            # ==================================================
            # SELECTION OPERATIONS
            # ==================================================
            handled = False
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
                    handled = True
                elif key in ("DELETE","BACKSPACE"):
                    pos=delete_selection()
                    if pos:
                        doc_y,real_x=pos
                    handled = True
                elif key=="CTRL_V":
                    text=(paste_from_clipboard())
                    pos=replace_selection(text)
                    if pos:
                        doc_y,real_x=pos
                    handled = True
                elif key=="TAB":
                    r=normalize_selection()
                    if r:
                        (r1,c1),(r2,c2)=r
                        for y in range(r1, r2+1):
                            state.doc_lines[y] = "  " + state.doc_lines[y]
                        # adjust selection columns
                        state.selection_anchor = (state.selection_anchor[0], state.selection_anchor[1] + 2)
                        state.selection_end = (state.selection_end[0], state.selection_end[1] + 2)
                        real_x += 2
                    handled = True
                elif key=="SHIFT+TAB":
                    r=normalize_selection()
                    if r:
                        (r1,c1),(r2,c2)=r
                        for y in range(r1, r2+1):
                            line = state.doc_lines[y]
                            if line.startswith("  "):
                                state.doc_lines[y] = line[2:]
                            elif line.startswith(" "):
                                state.doc_lines[y] = line[1:]
                        # adjust selection columns (approximate, clamp to 0)
                        state.selection_anchor = (state.selection_anchor[0], max(0, state.selection_anchor[1] - 2))
                        state.selection_end = (state.selection_end[0], max(0, state.selection_end[1] - 2))
                        real_x = max(0, real_x - 2)
                    handled = True
                elif len(key)==1:
                    pos=replace_selection(key)
                    if pos:
                        doc_y,real_x=pos
                    handled = True
                elif not shift_move:
                    clear_selection()

            # ==================================================
            # INPUT
            # ==================================================

            if not handled:
                if key=="CTRL_V":
                    text=(paste_from_clipboard())
                    if has_selection():
                        pos=replace_selection(text)
                        if pos:
                            doc_y,real_x=pos
                    else:
                        doc_y,real_x=(insert_text(doc_y,real_x,text))
                elif key=="CTRL_A":
                    # select all text
                    if state.doc_lines:
                        state.selection_active = True
                        state.selection_anchor = (0, 0)
                        last_y = len(state.doc_lines) - 1
                        state.selection_end = (last_y, len(state.doc_lines[last_y]))
                        state.selection_in_progress = False
                elif key=="TAB":
                    # add two spaces
                    doc_y, real_x = insert_text(doc_y, real_x, "  ")
                elif len(key)==1:
                    line=state.doc_lines[doc_y]
                    line=(line[:real_x]+key+line[real_x:]                )
                    state.doc_lines[doc_y]=line
                    real_x+=1
                elif key=="ENTER":
                    line=state.doc_lines[doc_y]
                    new_line=(line[real_x:])
                    state.doc_lines[doc_y]=(line[:real_x])
                    state.doc_lines.insert(doc_y+1,new_line)
                    doc_y+=1
                    real_x=0
                elif key=="BACKSPACE":
                    line=state.doc_lines[doc_y]
                    if real_x>0:
                        line=(line[:real_x-1]+line[real_x:])
                        state.doc_lines[doc_y]=line
                        real_x-=1
                    elif doc_y>0:
                        prev_line=(state.doc_lines[doc_y-1])
                        real_x=len(prev_line)
                        state.doc_lines[doc_y-1]=(prev_line+line)
                        state.doc_lines.pop(doc_y)
                        doc_y-=1
                elif key=="DELETE":
                    line=state.doc_lines[doc_y]
                    if real_x<len(line):
                        line=line[:real_x]+line[real_x+1:]
                        state.doc_lines[doc_y]=line
                    elif (doc_y < len(state.doc_lines)-1):
                        state.doc_lines[doc_y]+=state.doc_lines[doc_y+1]

                        state.doc_lines.pop(doc_y+1)

            # ==================================================
            # NAVIGATION
            # ==================================================
            if key in ("LEFT", "SHIFT+LEFT"):
                if real_x>0:
                    real_x-=1
                elif doc_y>0:
                    doc_y-=1
                    real_x=len(state.doc_lines[doc_y])

            elif key in ("RIGHT", "SHIFT+RIGHT"):
                if real_x < len(state.doc_lines[doc_y]):
                    real_x+=1
                elif (doc_y < len(state.doc_lines)-1):
                    doc_y+=1
                    real_x=0
            elif key in ("UP","SHIFT+UP"):
                if doc_y>0:
                    doc_y-=1
                    real_x=min(real_x, len(state.doc_lines[doc_y]))

            elif key in ("DOWN", "SHIFT+DOWN"):
                if (doc_y < len(state.doc_lines)-1):
                    doc_y+=1
                    real_x=min(real_x, len(state.doc_lines[doc_y]))

            if shift_move:
                update_selection(doc_y, real_x)

            # ==================================================
            # MAP DOCUMENT POSITION -> VISUAL POSITION
            # ==================================================

            visual=build_visual_lines()
            new_vis_idx=0

            for i,(dy,start,seg) in enumerate(visual):
                if (dy==doc_y and start<=real_x<=(start+len(seg))):
                    new_vis_idx=i
                    break

            dy,start,seg=(visual[new_vis_idx])
            cx=real_x-start

            cy=new_vis_idx-state.view_offset

            # ==================================================
            # SCROLLING
            # ==================================================

            if cy<0:
                state.view_offset=new_vis_idx
                cy=0
            elif cy>=view_box1[3]:
                state.view_offset=new_vis_idx-view_box1[3]+1
                cy=view_box1[3]-1

            cursor_offset=[cx,cy]

            # ==================================================
            # RENDER
            # ==================================================

            fill_view_box(view_box1,visual,cursor=(cx,cy))

            ch=''

            if (doc_y < len(state.doc_lines)):
                if (real_x < len(state.doc_lines[doc_y])):
                    ch=state.doc_lines[doc_y][real_x]

            draw_status(doc_y,real_x,ch,state.file_path)

        prev=key


if __name__=="__main__":
    if len(sys.argv)>1:
        path = sys.argv[1]
    else:
        path = None
    main(path)