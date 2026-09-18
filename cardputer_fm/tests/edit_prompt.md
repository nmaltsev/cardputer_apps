You are a seniour embennded developer, developing a text editor for M5Stack Card puter in CircuitPython.

Provide the complete file with defined main function that accepts the file name as an argument


The editor must not read the entire file. There must be defined an internal offset counter keeping the chunk offet in the file.
- The app reads the chunk from the file, let users to change it and write back to the file.
- Chunk is a buffer equal to 40*8 chart.
- The chunk can grow in accordance of the user input


## The UI
It is expected that screen width will be no more then 40 characters and screen height no more than 8 lines

### Header
It is the first line:
- Contains the file name
- if the chunk was changed prefix the file name by ~
- if the chunk was not changed prefix the name by the space charater

### Footer
`Ln:3 Col: 10 Len: 120 Offset: 1024`
The footer contains the coordiantes of the cursor within chunk (line and column). The current offset in bytes/characters

## Ctrl keys

CTRL_B, CTRL_F
- Saves the curent chunk changes (write the chunk to the file )
- Change the document offset. CTRL_B reads the previos chunk from the file, CTRL_F reads the next chunk

CTRL_L
- reload the current chunk: replace the existing chunk content (the user's changes) by the current file content

CTRL_S 
- writes the current chunk to the file. Read the new chunk from the file 

## Navigation within chunk
1. arrow keys - change the cursor position within a chunk
2. del, backspace -removes the character close to the cursor
3. Use `_` to show the current cursor, the character located in the cursor position should be right from the cursor


## Code snippets

Use the folowing code compatible with Circuit Python:
```Python
import sys
import os

def clear():
    sys.stdout.write("\x1b[2J\x1b[H")
    # print("\x1b[2J\x1b[H", end='')

def move_cursor(x, y):
    sys.stdout.write(f"\x1b[{y+1};{x+1}H")

CTRL_KEYS = {
    # "\x03": "CTRL_C",
    # "\x04": "CTRL_D",
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
```

Use the following tupple to define the edit zone:
```
view_box1 = (0,0,40,8)  # x,y,w,h (immutable!)
```
where 
0,0 - are coordinates for the header
7,0 - are coordiantes for the footer


-----
```
def load_file(path, offset, length):
    try:
        with open(path, 'rb') as f:
            f.seek(offset)
            return f.read(length).decode('utf-8')
    except OSError:
        return None

def write_file_chunk(path, offset, data):
    try:
        try:
            f = open(path, 'r+b')
        except OSError:
            f = open(path, 'w+b')

        with f:
            f.seek(offset)
            f.write(data)

        return True
    except OSError:
        return False


text = "Hello, world!"
success = write_file_chunk(
    "data.txt",
    0,
    text.encode("utf-8")
)
```

## Do not user

CircuitPython does not support modules: 
- tty
- termios 

Does not support:
- .ljust()
- sys.stdout.flush()
- os.path
- os.path.exists(path)