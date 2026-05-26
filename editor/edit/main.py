import sys
import os
import subprocess
import platform
from .utils import get_key, clear, move_cursor
from .clipboard import copy_to_clipboard, paste_from_clipboard
from .file_helpers import load_file, save_file
from .state import EditorState, SelectionState

def fill(text, max_width):
    if len(text) >= max_width:
        return text[0:max_width]
    else:
        return text + '-' * (max_width - len(text))

view_box1 = (1,1,40,10)  # x,y,w,h (immutable!)


def get_selected_text(state, selectionState):
    r=selectionState.normalize_selection()

    if not r:
        return ""

    (r1,c1),(r2,c2)=r
    lines = state.doc_lines

    if r1==r2:
        return lines[r1][c1:c2]

    out=[]
    out.append(lines[r1][c1:])

    for y in range(r1+1,r2):
        out.append(lines[y])

    out.append(lines[r2][:c2])

    return "\n".join(out)


def delete_selection(state, selectionState):
    r=selectionState.normalize_selection()

    if not r:
        return None
    (r1,c1),(r2,c2)=r
    doc_lines = state.doc_lines

    if r1==r2:
        line=doc_lines[r1]
        doc_lines[r1]=(line[:c1]+line[c2:])
    else:
        first=doc_lines[r1][:c1]
        last=doc_lines[r2][c2:]
        doc_lines[r1]=first+last
        del doc_lines[r1+1:r2+1]
    selectionState.clear_selection()
    return r1,c1


def insert_text(state, row,col,text):
    parts=text.split("\n")
    doc_lines = state.doc_lines
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


def replace_selection(state, selectionState, text):
    pos=delete_selection(state, selectionState)

    if pos is None:
        return None

    row,col=pos

    return insert_text(state, row, col,text)


# --- WRAPPING ---
def build_visual_lines(state):
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
def fill_view_box(state, view_box, visual_lines, cursor=None):
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
def draw_status(state, selectionState, doc_y,real_x,ch,path):
    y=view_box1[1]+view_box1[3]
    move_cursor(view_box1[0],y)

    if selectionState.has_selection():
        (r1,c1),(r2,c2)=(selectionState.normalize_selection())

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
    state=EditorState()
    selectionState = SelectionState()
    clear()

    # --- CLI ARG ---
    if len(sys.argv)>1:
        # file_path=sys.argv[1]
        # load_file(file_path)
        state.file_path=sys.argv[1]
        state.doc_lines=load_file(state.file_path)
    else:
        state.file_path="untitled.txt"

    prev=None
    EDIT_MODE=True
    # <<<TODO refactor the code to open the file
    cursor_offset=[0,0]
    clear()
    visual=build_visual_lines(state)
    fill_view_box(state,view_box1,visual,cursor=cursor_offset)
    vis_idx=state.view_offset+cursor_offset[1]
    doc_y,start_idx,_=(visual[vis_idx])
    real_x=start_idx+cursor_offset[0]
    draw_status(state, selectionState, doc_y, real_x, '', state.file_path)
    # >>>

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
            # save_file(file_path)
            save_file(state.file_path, state.doc_lines)

        # --- ENTER EDIT MODE ---
        if key=="CTRL_P":
            EDIT_MODE=True
            cursor_offset=[0,0]
            clear()

        if EDIT_MODE:
            visual=build_visual_lines(state)
            cx,cy=cursor_offset
            vis_idx=(state.view_offset+cy)

            if vis_idx>=len(visual):
                vis_idx=(len(visual)-1)

            doc_y,start_idx,segment=(visual[vis_idx])
            line=state.doc_lines[doc_y]
            real_x=start_idx+cx

            shift_move=key in ('SHIFT+LEFT','SHIFT+RIGHT','SHIFT+UP','SHIFT+DOWN')

            if shift_move:
                if not selectionState.in_progress:
                    selectionState.begin_selection(doc_y,real_x)
            else:
                if selectionState.in_progress:
                    selectionState.finalize_selection()

            # ==================================================
            # SELECTION OPERATIONS
            # ==================================================
            if selectionState.has_selection():
                if key=="CTRL_C":
                    copy_to_clipboard(get_selected_text(state, selectionState))
                    prev=key
                    continue
                elif key=="CTRL_X":
                    copy_to_clipboard(get_selected_text(state, selectionState))
                    pos=delete_selection(state, selectionState)
                    if pos:
                        doc_y,real_x=pos
                elif key in ("DELETE","BACKSPACE"):
                    pos=delete_selection(state, selectionState)
                    if pos:
                        doc_y,real_x=pos
                elif len(key)==1:
                    pos=replace_selection(state, key)

                    if pos:
                        doc_y,real_x=pos
                elif not shift_move:
                    selectionState.clear_selection()

            # ==================================================
            # INPUT
            # ==================================================

            if key=="CTRL_V":
                text=(paste_from_clipboard())
                if selectionState.has_selection():
                    pos=replace_selection(state,text)
                    if pos:
                        doc_y,real_x=pos
                else:
                    doc_y,real_x=(insert_text(state, doc_y,real_x,text))
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
                    prev_line=state.doc_lines[doc_y-1]
                    real_x=len(prev_line)
                    state.doc_lines[doc_y-1]=(prev_line+line)
                    state.doc_lines.pop(doc_y)
                    doc_y-=1
            elif key=="DELETE":
                line=state.doc_lines[doc_y]
                if real_x<len(line):
                    line=(line[:real_x]+line[real_x+1:])

                    state.doc_lines[doc_y]=line
                elif (doc_y<len(state.doc_lines)-1):
                    state.doc_lines[doc_y]+=state.doc_lines[doc_y+1]
                    state.doc_lines.pop(doc_y+1)

            # ==================================================
            # NAVIGATION
            # ==================================================

            elif key in ("LEFT","SHIFT+LEFT"):
                if real_x>0:
                    real_x-=1
                elif doc_y>0:
                    doc_y-=1
                    real_x=len(state.doc_lines[doc_y])

            elif key in ("RIGHT","SHIFT+RIGHT"):
                if real_x<len(line):
                    real_x+=1
                elif (doc_y<len(state.doc_lines)-1):
                    doc_y+=1
                    real_x=0

            elif key in ("UP","SHIFT+UP"):
                if doc_y>0:
                    doc_y-=1
                    real_x=min(real_x,len(state.doc_lines[doc_y]))

            elif key in ("DOWN","SHIFT+DOWN"):
                if (doc_y < len(state.doc_lines)-1):
                    doc_y+=1
                    real_x=min(real_x, len(state.doc_lines[doc_y]))

            if shift_move:
                selectionState.update_selection(doc_y,real_x)

            # ==================================================
            # MAP DOCUMENT POSITION -> VISUAL POSITION
            # ==================================================

            visual=build_visual_lines(state)
            new_vis_idx=0

            for i,(dy,start,seg) in enumerate(visual):
                if (dy==doc_y and start <= real_x <= (start+len(seg))):
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

            fill_view_box(state,view_box1,visual,cursor=(cx,cy))
            ch=''

            if (doc_y<len(state.doc_lines)):
                if (real_x<len(state.doc_lines[doc_y])):
                    ch=state.doc_lines[doc_y][real_x]

            draw_status(state, selectionState, doc_y, real_x, ch,state.file_path)

        prev=key


if __name__=="__main__":
    main()