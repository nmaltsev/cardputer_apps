from .handlers import (
    index_handler, get_debug_handler, get_dir_handler,
    get_file_handler, ui_handler, delete_handler,
)

STATIC_DIR = b"/media"

routes = {
    b"GET /":        index_handler,
    b"GET /debug":   get_debug_handler,
    b"POST /debug":  get_debug_handler,
    b"GET /dir":     get_dir_handler,
    b"GET /file":    get_file_handler,
    b"GET /ui":      ui_handler,
    b"POST /delete": delete_handler,
    # POST /file and POST /upload are handled specially in server.py
}