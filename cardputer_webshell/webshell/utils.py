# ==== HELPERS ====

def http_response(body=b"", status=b"200 OK", content_type=b"text/plain"):
    return b"HTTP/1.1 " + status + b"\r\n" + \
    b"Content-Type: " + content_type + b"\r\n" + \
    b"Cache-Control: no-store\r\n" + \
    b"Connection: close\r\n\r\n" + \
    body

def url_decode(value: bytes):
    replacements = {
        b"%2F": b"/",
        b"%20": b" ",
        b"%3A": b":",
        b"%2E": b".",
        b"%2D": b"-",
        b"%5F": b"_",
    }
    for k, v in replacements.items():
        value = value.replace(k, v)
    return value

def recv_all(client):
    buffer = bytearray(512)
    data = b""

    while True:
        try:
            n = client.recv_into(buffer)
        except OSError:
            break

        if n <= 0:
            break

        data += bytes(buffer[:n])

        if b"\r\n\r\n" in data:
            break

    return data

def parse_request_line(req: bytes):
    line_end = req.find(b"\r\n")
    if line_end == -1:
        return None, None

    parts = req[:line_end].split(b" ")
    if len(parts) < 2:
        return None, None

    return parts[0], parts[1]

def parse_query(path: bytes):
    if b"?" not in path:
        return path, {}

    p, q = path.split(b"?", 1)
    params = {}

    for pair in q.split(b"&"):
        if b"=" in pair:
            k, v = pair.split(b"=", 1)
            params[k] = v

    return p, params

def guess_mime(_path: str):
    path = _path.lower()
    if path.endswith(".txt") or path.endswith(".md") or path.endswith(".py"):
        return b"text/plain"
    if path.endswith(".html"):
        return b"text/html"
    if path.endswith(".css"):
        return b"text/css"
    if path.endswith(".js"):
        return b"application/javascript"
    if path.endswith(".json"):
        return b"application/json"
    if path.endswith((".jpg", ".jpeg")):
        return b"image/jpeg"
    if path.endswith(".png"):
        return b"image/png"
    return b"application/octet-stream"
 