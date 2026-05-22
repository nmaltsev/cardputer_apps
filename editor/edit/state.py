class EditorState:
    def __init__(self):
        self.doc_lines = [""]
        self.view_offset = 0
        self.file_path = None

        self.selection_active = False
        self.selection_anchor = None
        self.selection_end = None
        self.selection_in_progress = False