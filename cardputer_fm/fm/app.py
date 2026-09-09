from .__main__ import list_dir as fm

try:
    import board
    # TODO get from properties
    board.DISPLAY.brightness = 0.35
except:
    pass
fm()
