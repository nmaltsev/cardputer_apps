# ==== HELPERS ====

def http_response(body=b"", status=b"200 OK", content_type=b"text/plain"):
    return (
        b"HTTP/1.1 " + status + b"\r\n"
        b"Content-Type: " + content_type + b"\r\n"
        b"Cache-Control: no-store\r\n"
        b"Connection: close\r\n\r\n"
        + body
    )


def url_decode(value: bytes) -> bytes:
    # Minimal decoder – enough for the characters we actually use
    replacements = {
        b"%2F": b"/",
        b"%20": b" ",
        b"%3A": b":",
        b"%2E": b".",
        b"%2D": b"-",
        b"%5F": b"_",
        b"%2B": b"+",
    }
    for k, v in replacements.items():
        value = value.replace(k, v)
    return value


def recv_headers(client, max_header=2048):
    """
    Read until \r\n\r\n (or timeout / disconnect).
    Returns (headers_bytes, leftover_body_bytes) or (None, None) on error.
    Never grows beyond max_header + a little bit.
    """
    buffer = bytearray(256)
    data = b""

    while b"\r\n\r\n" not in data:
        if len(data) > max_header:
            return None, None          # header too large → reject
        try:
            n = client.recv_into(buffer)
        except OSError:
            return None, None
        if n <= 0:
            return None, None
        data += bytes(buffer[:n])

    headers, rest = data.split(b"\r\n\r\n", 1)
    return headers, rest


def parse_content_length(headers: bytes) -> int:
    for line in headers.split(b"\r\n"):
        if line.lower().startswith(b"content-length:"):
            try:
                return int(line.split(b":", 1)[1].strip())
            except ValueError:
                return 0
    return 0


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


def guess_mime(_path: str) -> bytes:
    path = _path.lower()
    if path.endswith((".txt", ".md", ".py", ".css")):
        return b"text/plain"
    if path.endswith(".html"):
        return b"text/html"
    if path.endswith(".js"):
        return b"application/javascript"
    if path.endswith(".json"):
        return b"application/json"
    if path.endswith((".jpg", ".jpeg")):
        return b"image/jpeg"
    if path.endswith(".png"):
        return b"image/png"
    return b"application/octet-stream"