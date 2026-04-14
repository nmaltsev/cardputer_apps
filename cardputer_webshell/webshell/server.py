import wifi
import socketpool
import time
import os
import sys
from .settings import SSID, PASSWORD
from .utils import parse_request_line, parse_query
from .routes import routes

def route_request(request: bytes):
    method, full_path = parse_request_line(request)
    if not method:
        return http_response(b"Bad Request", status=b"400 Bad Request")

    path, _ = parse_query(full_path)
    key = method + b" " + path

    handler = routes.get(key)
    if not handler:
        # TODO check the file from the static directory
        return http_response(b"Not Found", status=b"404 Not Found")

    return handler(request)


def start(host='0.0.0.0', port=80):
    wifi.radio.connect(SSID, PASSWORD)
    pool = socketpool.SocketPool(wifi.radio)
    server = pool.socket(pool.AF_INET, pool.SOCK_STREAM)
    server.setsockopt(pool.SOL_SOCKET, pool.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)
    server.setblocking(False)
    print("Listening. IP: ", wifi.radio.ipv4_address)
    # ==== MAIN LOOP (NON-BLOCKING STREAMING) ====

    clients = []
    try:
        while True:
            try:
                sock, addr = server.accept()
                sock.setblocking(False)

                clients.append({
                    "sock": sock,
                    "state": "request",
                    "file": None,
                    "out_buf": b"",
                })

                print("Client:", addr)
            except OSError:
                pass

            for c in clients[:]:
                client = c["sock"]

                try:
                    if c["state"] == "request":
                        req = recv_all(client)

                        if req:
                            resp = route_request(req)

                            if isinstance(resp, tuple):
                                f, header = resp
                                c["file"] = f
                                c["out_buf"] = header
                                c["state"] = "stream"
                            else:
                                c["out_buf"] = resp
                                c["state"] = "send"

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
                    clients.remove(c)

            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Shutting down server...")

        # Close all clients
        for c in clients:
            try:
                c.close()
            except:
                pass

        clients.clear()

        # Close server socket
        try:
            server.close()
        except:
            pass

        print("Server stopped by user.")