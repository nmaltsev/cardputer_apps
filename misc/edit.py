from edit_utils import get_key, clear, move_cursor

def fill(text, max_width):
    if len(text) >= max_width:
        return text[0:max_width]
    else:
        return text + '-' * (max_width - len(text))


view_box1 = (5,5,40, 10) # x,y, w,h (immutable!)



def fill_view_box(view_box, content):
    relative_line_n = 0
    while relative_line_n < view_box[3]:
        move_cursor(view_box[0], view_box[1] + relative_line_n)
        relative_line_n += 1
        # TODO get content
        print(fill(f'{relative_line_n=}', view_box[2]), end='')
    print()

def main():
    prev = None
    EDIT_MODE = False
    cursor_offset = [0,0] # dx, dy
    buffer = [] # TODO array of  lines 
    while True:
        key = get_key()
         
        if EDIT_MODE is False:
            print(f"{key=}")
        if key == 'CTRL_C' and prev == 'CTRL_C':
            break

        if key == 'CTRL_W':
            clear()
        if key == 'CTRL_P':
            EDIT_MODE = True
            fill_view_box(view_box1, buffer)
            cursor_offset = [0,-1]
            move_cursor(view_box1[0] + cursor_offset[0], view_box1[1] + cursor_offset[1])
            print('_', end='')
            print()
        
        if EDIT_MODE is True:
            if len(key) == 1:
                move_cursor(view_box1[0] + cursor_offset[0], view_box1[1] + cursor_offset[1])
                print(key, end='')
                # TODO print cursor
                if cursor_offset[0] < view_box1[2]-1:
                    cursor_offset[0] += 1
                else: 
                    cursor_offset[0] = 0
                    cursor_offset[1] += 1
                
                if cursor_offset[1] > view_box1[3]-1:
                    # TODO call fill_view_box(view_box1)
                    cursor_offset[1] = view_box1[3] -1
                print()
            # TODO handle arrow keys, enter, backspcae and delte


        prev = key

if __name__ == '__main__':
    main()
