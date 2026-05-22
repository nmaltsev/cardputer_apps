import os

def load_file(path):
    if os.path.exists(path):
        with open(path,"r",encoding="utf-8") as f:
            lines = f.read().splitlines()
        return lines or [""]
    return [""]


def save_file(path, doc_lines):
    with open(path,"w",encoding="utf-8") as f:
        f.write("\n".join(doc_lines))