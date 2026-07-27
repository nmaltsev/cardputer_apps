import wifi
import socketpool
import time
import os
from .settings import SSID, PASSWORD
from .utils import (
    parse_request_line, parse_query, http_response,
    recv_headers, parse_content_length
)
from .routes import routes, STATIC_DIR
from .handlers import (
    stream_file,
    post_file_handler_stream,
    upload_handler_stream,
)


def route_request(headers: bytes, leftover: bytes, content_length: int, client):
    """
    Decide what to do with a request.
    For body-consuming routes we hand the socket over to a streaming handler.
    """
    method, full_path = parse_request_line(headers)
    if not method:
        return http_response(b"Bad Request", status=b"400 Bad Request")

    path, params = parse_query(full_path)
    key = method + b" " + path

    # ---- body-streaming routes ----
    if key == b"POST /file":
        target = params.get(b"path")
        if not target:
            return http_response(b"Missing path", status=b"400 Bad Request")
        filepath = url_decode(target).decode()
        return post_file_handler_stream(client, headers, leftover, content_length, filepath)

    if key == b"POST /upload":
        return upload_handler_stream(client, headers, leftover, content_length)

    # ---- normal (no-body or small-body) routes ----
    handler = routes.get(key)
    if handler:
        # reconstruct a minimal request object for the old-style handlers
        req = headers + b"\r\n\r\n" + leftover
        return handler(req)

    # ---- static file ----
    try:
        fpath = STATIC_DIR.rstrip(b"/") + path
        filepath = fpath.decode()
        os.stat(filepath)
        return stream_file(filepath)
    except Exception as e:
        return http_response(str(e).encode(), status=b"500 Internal Server Error")


def start(host="0.0.0.0", port=80):
    wifi.radio.connect(SSID, PASSWORD)
    pool = socketpool.SocketPool(wifi.radio)
    server = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    server.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    server.setblocking(False)
    print("Listening. IP:", wifi.radio.ipv4_address)

    clients = []

    try:
        while True:
            # accept
            try:
                sock, addr = server.accept()
                sock.setblocking(False)
                clients.append({
                    "sock": sock,
                    "state": "headers",          # headers → send / stream
                    "file": None,
                    "out_buf": b"",
                    "headers": None,
                    "leftover": b"",
                    "clen": 0,
                })
                print("Client:", addr)
            except OSError:
                pass

            for c in clients[:]:
                client = c["sock"]
                try:
                    if c["state"] == "headers":
                        headers, leftover = recv_headers(client)
                        if headers is None:
                            # incomplete / error → drop
                            client.close()
                            clients.remove(c)
                            continue

                        clen = parse_content_length(headers)
                        c["headers"] = headers
                        c["leftover"] = leftover
                        c["clen"] = clen

                        # hand off to the router – may return a response
                        # or may already have consumed the body (streaming)
                        resp = route_request(headers, leftover, clen, client)

                        if isinstance(resp, tuple):          # (file, header)
                            f, header = resp
                            c["file"] = f
                            c["out_buf"] = header
                            c["state"] = "stream"
                        else:
                            c["out_buf"] = resp
                            c["state"] = "send"

                    # ---- send a normal (small) response ----
                    if c["state"] == "send":
                        if c["out_buf"]:
                            try:
                                sent = client.send(c["out_buf"])
                                c["out_buf"] = c["out_buf"][sent:]
                            except OSError:
                                pass
                        else:
                            client.close()
                            clients.remove(c)

                    # ---- stream a file download ----
                    elif c["state"] == "stream":
                        if c["out_buf"]:
                            try:
                                sent = client.send(c["out_buf"])
                                c["out_buf"] = c["out_buf"][sent:]
                                continue
                            except OSError:
                                continue

                        chunk = c["file"].read(512)
                        if chunk:
                            c["out_buf"] = chunk
                        else:
                            c["file"].close()
                            client.close()
                            clients.remove(c)

                except Exception as e:
                    print("Error:", e)
                    try:
                        client.close()
                    except:
                        pass
                    if c in clients:
                        clients.remove(c)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Shutting down…")
        for c in clients:
            try:
                c["sock"].close()
            except:
                pass
        try:
            server.close()
        except:
            pass
        print("Server stopped.")