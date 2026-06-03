class EditorState:
    def __init__(self, use_tab:bool = False, tab_size:int = 2, view_box = (1, 1, 50, 20)):
        self.use_tab = use_tab
        self.tab_size = tab_size
        self.doc_lines = [""]
        self.view_offset = 0
        self.file_path = None
        self.modified = False
        self.cursor_offset = [0, 0]
        self.view_box = view_box #  (x,y,w,h) immutable

    def get_tab(self):
        if self.use_tab:
            return '\t'
        return " " * self.tab_size

class SelectionState:
    def __init__(self):
        self.active = False
        self.anchor = None
        self.end = None
        self.in_progress = False

    def normalize_selection(self):
        if not self.anchor or not self.end:
            return None

        a = self.anchor
        b = self.end

        if a <= b:
            return a,b

        return b,a
    
    def has_selection(self):
        r = self.normalize_selection()

        if not r:
            return False
        a,b = r
        return a != b

    def clear_selection(self):
        self.active=False
        self.anchor=None
        self.end=None
        self.in_progress=False


    def begin_selection(self,row,col):
        if not self.active:
            self.active=True
            self.anchor=(row,col)

        self.end=(row,col)
        self.in_progress=True

    def update_selection(self, row,col):
        self.end=(row,col)

    def finalize_selection(self):
        self.in_progress=False