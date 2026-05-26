class EditorState:
    def __init__(self):
        self.doc_lines = [""]
        self.view_offset = 0
        self.file_path = None

        # self.selection_active = False
        # self.selection_anchor = None
        # self.selection_end = None
        # self.selection_in_progress = False

# TODO define selection State class with methods

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