import sys
import tty
import termios


KEY_MAP = {
  9: 'TAB', # the same as Ctrl_I !
  13: 'ENTER',
  #27: 'ESC',
  # 32: 'SPACE',
  127: 'BACKSPACE',
}

def litter_key(code:int):
  if code == 65:
    return 'UP'
  if code == 66:
    return 'DOWN'
  if code == 67:
    return 'RIGHT'
  if code == 68:
    return 'LEFT'
  return None

def read_sequence():
    seq = []
    c = 0
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
      tty.setraw(fd)
      while True and c < 6:
          ch = sys.stdin.read(1)
          code = ord(ch)
          
          if c == 0 and (31 < code < 127):
            return ch

          if c == 0 and code in KEY_MAP:
            return KEY_MAP[code]

          # does not distingush Ctrl + a and ctrl + A 
          if c == 0 and (0 < code < 27):
            # Does not detect Ctrl+I
            return f"CTRL_{chr(code + 64)}"
          
          if c == 1 and (0 < code < 27) and seq[0] == 27:
            # Does not detect Ctrl+I
            return f"ALT+CTRL_{chr(code + 64)}"

          if True:
            print(f"{code=} {c=}", file=sys.stderr)
            seq.append(code)
            c+=1
            continue

          # -----------------------------------------------------------
          # macOS Terminal:
          #
          # Option+Left  -> ESC b
          # Option+Right -> ESC f
          # -----------------------------------------------------------
          if seq == [27]:
            if code == ord('b'):
              return 'ALT+LEFT'

            if code == ord('f'):
              return 'ALT+RIGHT'

          arrow_name = litter_key(code)

          if arrow_name:

            # ---------------------------------------------------------
            # Normal arrow:
            #
            # ESC [ A
            # ESC [ B
            # ESC [ C
            # ESC [ D
            # ---------------------------------------------------------
            if seq == [27,91]:
              return arrow_name

            # ---------------------------------------------------------
            # ALT + arrow, ESC ESC [ A/B/C/D
            # ---------------------------------------------------------
            if seq == [27,27,91]:
              return 'ALT+' + arrow_name

            # ---------------------------------------------------------
            # ALT + arrow, SS3 form:
            #
            # ESC O A
            # ESC O B
            # ESC O C
            # ESC O D
            #
            # Some terminal configurations use this form.
            # ---------------------------------------------------------
            if seq == [27,79]:
              return 'ALT+' + arrow_name

            if seq == [27,91,49,59,50]:
              return 'SHIFT+' + arrow_name

            if seq == [27,91,49,59,53]:
              return 'CTRL+' + arrow_name

            if seq == [27,91,49,59,51]:
              return 'ALT+' + arrow_name

            if seq == [27,91,49,59,52]:
              return 'SHIFT+ALT+' + arrow_name

            if seq == [27,91,49,59,54]:
              return 'CTRL+SHIFT+' + arrow_name

            if seq == [27,91,49,59,55]:
              return 'CTRL+ALT+' + arrow_name

            if seq == [27,91,49,59,56]:
              return 'CTRL+SHIFT+ALT+' + arrow_name
            
          if code == 126:
            if seq == [27,91,49]:
              return 'HOME'
            if seq == [27,91,50]:
              return 'INS'
            if seq == [27,91,51]:
              return 'DEL'
            if seq == [27,91,52]:
              return 'END'
            if seq == [27,91,53]:
              return 'PAGE_UP'
            if seq == [27,91,54]:
              return 'PAGE_DOWN'
            if seq == [27,91,49,53]:
              return 'F5'
            if seq == [27,91,49,55]:
              return 'F6'
            if seq == [27,91,49,56]:
              return 'F7'
            if seq == [27,91,49,57]:
              return 'F8'
            if seq == [27,91,50,48]:
              return 'F9'
            if seq == [27,91,50,49]:
              return 'F10'
            if seq == [27,91,50,52]:
              return 'F12'
            if seq == [27,27,91,50]:
              return 'ALT+INS'
            if seq == [27,27,91,51]:
              return 'ALT+DEL'
            if seq == [27,27,91,53]:
              return 'ALT+PAGE_UP'
            if seq == [27,27,91,54]:
              return 'ALT+PAGE_DOWN'

          if seq == [27,79]:
            if code == 80:
              return 'F1'
            if code == 81:
              return 'F2'
            if code == 82:
              return 'F3'
            if code == 83:
              return 'F4'
          if seq == [27,91]:
            if code == 90:
              return 'SHIFT+TAB'
          if seq == [27,91,49,59,50]:
            if code == 72:
              return 'SHIFT+HOME'
            if code == 70:
              return 'SHIFT+END'
          if seq == [27,91,49,59,51]:
            if code == 72:
              return 'ALT+HOME'
            if code == 70:
              return 'ALT+END'
          if seq == [27,91,49,59,53]:
            if code == 72:
              return 'CTRL+HOME'
            if code == 70:
              return 'CTRL+END'
          print(f"{code=} {c=}", file=sys.stderr)
          seq.append(code)
          c+=1
    finally:
      termios.tcsetattr(fd, termios.TCSADRAIN, old)

    return str(seq)


prev = None
while True:
  fd = sys.stdin.fileno()
  old = termios.tcgetattr(fd)
  seq = read_sequence()
  if seq == 'Q' and prev == 'Q':
    break
  print(f'{seq=}')
  prev = seq