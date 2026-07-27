import os
from .utils import (
    http_response, parse_request_line, parse_query,
    url_decode, guess_mime
)

# ------------------------------------------------------------------
# Streaming file download (unchanged logic, just cleaner)
# ------------------------------------------------------------------
def stream_file(filepath: str):
    try:
        f = open(filepath, "rb")
        mime = guess_mime(filepath)
        filename = filepath.encode()
        header = (
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: " + mime + b"\r\n"
            b"Content-Disposition: inline; filename=\"" + filename + b"\"\r\n"
            b"Cache-Control: no-store\r\n"
            b"Connection: close\r\n\r\n"
        )
        return (f, header)
    except Exception as e:
        return http_response(str(e).encode(), status=b"500 Internal Server Error")


# ------------------------------------------------------------------
# Simple handlers that do not need a body
# ------------------------------------------------------------------
def index_handler(request):
    return http_response(b"Hello, world!\n")


def get_debug_handler(request):
    # request here is only the headers + whatever was already read
    return http_response(request)


def get_dir_handler(request):
    method, full_path = parse_request_line(request)
    path, params = parse_query(full_path)
    raw = params.get(b"path", b"/")
    target = url_decode(raw).decode()

    try:
        items = os.listdir(target)
        result = []
        for name in items:
            full = target.rstrip("/") + "/" + name
            resource_type = 1
            filesize = 0
            ctime = mtime = None
            try:
                stats = os.stat(full)
                filesize = stats[6]
                if stats[0] & 0x4000:          # S_IFDIR
                    resource_type = 2
                ctime = stats[8] if len(stats) > 8 else stats[9]
                mtime = stats[9] if len(stats) > 9 else stats[8]
            except OSError:
                pass
            result.append([name, resource_type, filesize, ctime, mtime])

        import json
        return http_response(
            json.dumps(result).encode(),
            content_type=b"application/json"
        )
    except OSError:
        return http_response(b"Not Found", status=b"404 Not Found")


def get_file_handler(request):
    method, full_path = parse_request_line(request)
    path, params = parse_query(full_path)
    target = params.get(b"path")
    if not target:
        return http_response(b"Missing path", status=b"400 Bad Request")
    filepath = url_decode(target).decode()
    return stream_file(filepath)


def delete_handler(request):
    method, full_path = parse_request_line(request)
    path, params = parse_query(full_path)
    target = params.get(b"path")
    if not target:
        return http_response(b"Missing path", status=b"400 Bad Request")
    target = url_decode(target).decode()
    try:
        remove_recursive(target)
        return http_response(b"Deleted")
    except Exception as e:
        return http_response(str(e).encode(), status=b"500 Internal Server Error")


def remove_recursive(path):
    st = os.stat(path)
    if st[0] & 0x4000:                       # directory
        for name in os.listdir(path):
            remove_recursive(path.rstrip("/") + "/" + name)
        os.rmdir(path)
    else:
        os.remove(path)


# ------------------------------------------------------------------
# Body-streaming handlers
# These are called from the server after headers have been parsed.
# They receive the client socket + already-read leftover body bytes
# and must consume the remaining Content-Length themselves.
# ------------------------------------------------------------------
def post_file_handler_stream(client, headers, leftover, content_length, filepath):
    """Write a raw POST body straight to disk."""
    try:
        with open(filepath, "wb") as f:
            # first write whatever was already read after the headers
            written = 0
            if leftover:
                f.write(leftover)
                written = len(leftover)

            buf = bytearray(512)
            while written < content_length:
                try:
                    n = client.recv_into(buf)
                except OSError:
                    break
                if n <= 0:
                    break
                f.write(buf[:n])
                written += n

        return http_response(b"OK")
    except Exception as e:
        return http_response(str(e).encode(), status=b"500 Internal Server Error")


def parse_multipart_boundary(headers: bytes):
    for line in headers.split(b"\r\n"):
        if b"Content-Type:" in line and b"multipart/form-data" in line:
            parts = line.split(b"boundary=")
            if len(parts) > 1:
                return b"--" + parts[1].strip()
    return None


def upload_handler_stream(client, headers, leftover, content_length):
    """
    Extremely lightweight multipart parser that streams the file part
    directly to disk.  Only looks for the two fields we care about:
        name="path"
        name="file"
    """
    boundary = parse_multipart_boundary(headers)
    if not boundary:
        return http_response(b"No boundary", status=b"400 Bad Request")

    # We keep a small rolling buffer so we can detect the boundary
    # without holding the whole body.
    buf = leftover
    path_value = None
    file_opened = None
    state = "looking"          # looking | in_headers | in_file | in_path
    header_acc = b""

    try:
        remaining = content_length - len(leftover)
        chunk = bytearray(512)

        while True:
            # ---- feed more data if needed ----
            if len(buf) < 1024 and remaining > 0:
                try:
                    n = client.recv_into(chunk)
                except OSError:
                    n = 0
                if n <= 0:
                    break
                buf += bytes(chunk[:n])
                remaining -= n

            if not buf:
                break

            if state == "looking":
                idx = buf.find(boundary)
                if idx == -1:
                    # keep a little overlap so we never miss a boundary
                    if len(buf) > len(boundary) + 4:
                        buf = buf[-(len(boundary) + 4):]
                    else:
                        # need more data
                        if remaining <= 0:
                            break
                        continue
                else:
                    # consume up to (and including) the boundary
                    buf = buf[idx + len(boundary):]
                    # skip the optional \r\n that follows the boundary
                    if buf.startswith(b"\r\n"):
                        buf = buf[2:]
                    elif buf.startswith(b"--"):
                        # final boundary
                        break
                    state = "in_headers"
                    header_acc = b""
                    continue

            elif state == "in_headers":
                # accumulate until blank line
                end = buf.find(b"\r\n\r\n")
                if end == -1:
                    header_acc += buf
                    buf = b""
                    continue
                header_acc += buf[:end]
                buf = buf[end + 4:]

                # decide what this part is
                if b'name="path"' in header_acc:
                    state = "in_path"
                    path_value = b""
                elif b'name="file"' in header_acc:
                    # extract filename if present (optional)
                    # open the target file now that we know the path
                    if path_value is None:
                        # path part must come first in the form
                        return http_response(b"path must precede file", status=b"400 Bad Request")
                    try:
                        file_opened = open(path_value.decode(), "wb")
                    except Exception as e:
                        return http_response(str(e).encode(), status=b"500 Internal Server Error")
                    state = "in_file"
                else:
                    # unknown part – just skip until next boundary
                    state = "looking"
                header_acc = b""
                continue

            elif state == "in_path":
                # path is small – just collect until boundary
                idx = buf.find(b"\r\n" + boundary)
                if idx == -1:
                    path_value += buf
                    buf = b""
                    continue
                path_value += buf[:idx]
                buf = buf[idx:]          # leave the \r\n+boundary for the next state
                state = "looking"
                continue

            elif state == "in_file":
                # stream until we see the boundary
                idx = buf.find(b"\r\n" + boundary)
                if idx == -1:
                    # write everything except a possible partial boundary
                    keep = len(boundary) + 4
                    if len(buf) > keep:
                        file_opened.write(buf[:-keep])
                        buf = buf[-keep:]
                    # else wait for more data
                    if remaining <= 0 and len(buf) <= keep:
                        # end of stream – write the rest
                        file_opened.write(buf)
                        buf = b""
                        break
                    continue
                else:
                    # write up to the boundary
                    file_opened.write(buf[:idx])
                    buf = buf[idx:]          # leave \r\n+boundary
                    file_opened.close()
                    file_opened = None
                    state = "looking"
                    continue

        if file_opened:
            file_opened.close()

        if path_value is None:
            return http_response(b"Missing path", status=b"400 Bad Request")

        return http_response(b"Upload OK")

    except Exception as e:
        if file_opened:
            try:
                file_opened.close()
            except:
                pass
        return http_response(str(e).encode(), status=b"500 Internal Server Error")


# ------------------------------------------------------------------
# UI handler (unchanged – still returns a big static string)
# ------------------------------------------------------------------
def ui_handler(request):
    html = b"""HTTP/1.1 200 OK\r
Content-Type: text/html\r
Cache-Control: no-store\r
Connection: close\r
\r
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>File Explorer</title>
<style>
body {
    font-family: Arial, sans-serif;
    background: #f5f7fa;
    margin: 20px;
}

fieldset {
    border: 1px solid #ccc;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
    background: white;
}

legend {
    font-weight: bold;
    padding: 0 10px;
}

input, textarea, button {
    font-size: 14px;
    padding: 6px;
}

button {
    cursor: pointer;
    border-radius: 5px;
    border: 1px solid #888;
    background: #eee;
}

button:hover {
    background: #ddd;
}

#list {
    max-height: 50vh;
    overflow: auto;
    display: grid;
    grid-template-columns: 40px 1fr 100px 140px 140px 80px 80px;
    gap: 5px;
    margin-top: 10px;
}

#list div {
    padding: 5px;
    border-bottom: 1px solid #eee;
}

#list div:nth-child(7n+2) {
    cursor: pointer;
    color: #0077cc;
}

#list div:nth-child(7n+2):hover {
    text-decoration: underline;
}
.header {
    font-weight: bold;
    background: #eee;
}

.icon-dir {
    color: green;
    font-weight: bold;
}

.icon-file {
    color: #555;
}

#fileForm[popover] {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 600px;
    max-width: 90vw;
    z-index: 1001;
    border-radius: 10px;
}

#fileForm::backdrop {
    background: rgba(0,0,0,0.5);
}

textarea {
    width: 100%;
    box-sizing: border-box;
    font-family: monospace;
}

.close-btn {
    float: right;
    background: #ff5c5c;
    color: white;
    border: none;
}
</style>
</head>
<body>

<form onsubmit="event.preventDefault(); listDir();">
    <fieldset>
        <legend>File Explorer</legend>
        <fieldset>
            <legend>Upload File</legend>
            <input type="file" id="upload_file">
            <button onclick="uploadFile()">Upload</button>
        </fieldset>
        <div>
            <input id="path" value="/" style="width:300px">
            <button type="submit">List</button>
        </div>
        <div id="list"></div>
    </fieldset>
</form>

<fieldset id="fileForm" popover="auto">
    <legend>Editor</legend>
    <button type="button" class="close-btn" popovertarget="fileForm">X</button>

    <form onsubmit="event.preventDefault(); loadFile();">
        <input id="file_path" style="width:300px">
        <button type="submit">Load</button>
    </form>

    <form onsubmit="event.preventDefault(); saveFile();">
        <textarea id="editor" rows="15"></textarea>
        <button type="submit">Save</button>
    </form>
</fieldset>

<script>
function t(text){return document.createTextNode(text);} // preserved

function cr(){
    if (arguments.length === 0) throw('No tag name');
    var el = document.createElement(arguments[0]);
    for(var i = 1, m = arguments.length; i < m; i += 2){
        if(arguments[i] && arguments[i + 1] !== undefined) {
            if (arguments[i] === 'class') {
                el.className = arguments[i + 1];
            } else {
                el[arguments[i]] = arguments[i + 1];
            }
        }
    }
    return el;
}

async function listDir() {
  try {
    let path = document.getElementById("path").value;
    let res = await fetch("/dir?path=" + encodeURIComponent(path));

    if (!res.ok) throw new Error("HTTP " + res.status);

    let files = await res.json();
    let list = document.getElementById("list");
    list.innerHTML = "";

    // header row
    ["", "Name", "Size", "Created", "Modified", "Download", "Delete"].forEach(h => {
        let el = cr('div', 'class', 'header', 'textContent', h);
        list.appendChild(el);
    });

    files.forEach(item => {
        let name = item[0];
        let type = item[1];
        let sizeVal = item[2] || 0;
        let ctime = item[3] ? new Date(item[3]*1000).toLocaleString() : "-";
        let mtime = item[4] ? new Date(item[4]*1000).toLocaleString() : "-";

        let full = (path.endsWith("/") ? path : path + "/") + name;

        let icon = cr('div', 'class', (type==2 ? 'icon-dir' : 'icon-file'),
            'textContent', (type==2 ? "📁" : "📄"));

        let link = cr('div', 'textContent', name);

        if (type == 2) {
            link.onclick = () => {
                document.getElementById("path").value = full;
                listDir();
            };
        } else {
            link.setAttribute('popovertarget', 'fileForm');
            link.onclick = () => {
                document.getElementById("file_path").value = full;
                document.getElementById("editor").value = '';
                document.getElementById("fileForm").showPopover();
            };
        }

        let size = cr('div', 'textContent', sizeVal + ' B');
        let c = cr('div', 'textContent', ctime);
        let m = cr('div', 'textContent', mtime);

        let download = cr('button', 'textContent', '⬇');
        download.onclick = () => {
            window.location = "/file?path=" + encodeURIComponent(full);
        };

        let del = cr('button', 'textContent', '🗑');
        del.onclick = async () => {
            if (!confirm("Delete " + full + " ?")) return;
            let res = await fetch("/delete?path=" + encodeURIComponent(full), { method: "POST"});
            if (!res.ok) {
                alert("Delete failed");
            } else {
                listDir();
            }
        };

        list.appendChild(icon);
        list.appendChild(link);
        list.appendChild(size);
        list.appendChild(c);
        list.appendChild(m);
        list.appendChild(download);
        list.appendChild(del);
    });

  } catch(e) {
    alert("Error loading directory: " + String(e));
  }
}

async function loadFile() {
  try {
    let path = document.getElementById("file_path").value;
    let res = await fetch("/file?path=" + encodeURIComponent(path));

    if (!res.ok) throw new Error("HTTP " + res.status);

    let text = await res.text();
    document.getElementById("editor").value = text;
  } catch (e) {
    alert("Error loading file: " + e);
  }
}
async function uploadFile() {
  try {
    let fileInput = document.getElementById("upload_file");
    if (!fileInput.files.length) return alert("No file selected");

    let path = document.getElementById("path").value;
    let file = fileInput.files[0];

    let form = new FormData();
    form.append("path", (path.endsWith("/") ? path : path + "/") + file.name);
    form.append("file", file);

    let res = await fetch("/upload", {
        method: "POST",
        body: form
    });

    if (!res.ok) throw new Error("HTTP " + res.status);

    alert("Uploaded");
    listDir();

  } catch (e) {
    alert("Upload failed: " + e);
  }
}

async function saveFile() {
  try {
    let path = document.getElementById("file_path").value;
    let content = document.getElementById("editor").value;

    let res = await fetch("/file?path=" + encodeURIComponent(path), {
      method: "POST",
      headers: { 'Content-Type': 'text/plain' },
      body: content
    });

    if (!res.ok) throw new Error("HTTP " + res.status);

    alert("Saved");
  } catch (e) {
    alert("Error saving file: " + e);
  }
}
</script>

</body>
</html>
"""
    return http_response(html, content_type=b"text/html")
