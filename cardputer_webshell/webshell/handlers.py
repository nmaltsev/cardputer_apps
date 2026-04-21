import os
from .utils import http_response, parse_request_line, parse_query, url_decode, guess_mime
# ==== HANDLERS ====

def stream_file(filepath):
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


def index_handler(request):
    return http_response(b"Hello, world!\n")

def get_debug_handler(request):
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
            try:
                stats = os.stat(full)
                filesize = stats[6]
                if stats[0] & 0x4000:
                    resource_type = 2
            except:
                pass

            result.append([name, resource_type, filesize])

        # TODO define json_response
        import json
        return http_response(
            json.dumps(result).encode(),
            content_type=b"application/json"
        )

    except:
        return http_response(b"Not Found", status=b"404 Not Found")

def get_file_handler(request):
    method, full_path = parse_request_line(request)
    path, params = parse_query(full_path)

    target = params.get(b"path", None)
    if not target:
        return http_response(b"Missing path", status=b"400 Bad Request")

    filepath = url_decode(target).decode()

    return stream_file(filepath)

def post_file_handler(request):
    method, full_path = parse_request_line(request)
    path, params = parse_query(full_path)

    target = params.get(b"path", None)
    if not target:
        return http_response(b"Missing path", status=b"400 Bad Request")

    split = request.find(b"\r\n\r\n")
    if split == -1:
        return http_response(b"Invalid request", status=b"400 Bad Request")

    body = request[split + 4:]
    filepath = url_decode(target).decode()

    try:
        with open(filepath, "wb") as f:
            f.write(body)
        return http_response(b"OK")
    except Exception as e:
        return http_response(str(e).encode(), status=b"500 Internal Server Error")

def parse_multipart(request: bytes):
    header_end = request.find(b"\r\n\r\n")
    if header_end == -1:
        return None, None

    headers = request[:header_end]
    body = request[header_end + 4:]

    boundary = None
    for line in headers.split(b"\r\n"):
        if b"Content-Type:" in line and b"multipart/form-data" in line:
            parts = line.split(b"boundary=")
            if len(parts) > 1:
                boundary = b"--" + parts[1].strip()
                break

    if not boundary:
        return None, None

    parts = body.split(boundary)

    file_content = None
    path_value = None

    for part in parts:
        if b"Content-Disposition" not in part:
            continue

        header_end = part.find(b"\r\n\r\n")
        if header_end == -1:
            continue

        part_headers = part[:header_end]
        part_body = part[header_end + 4:].rstrip(b"\r\n")

        if b'name="path"' in part_headers:
            path_value = part_body
        elif b'name="file"' in part_headers:
            file_content = part_body

    return path_value, file_content

def upload_handler(request):
    path, content = parse_multipart(request)

    if not path or content is None:
        return http_response(b"Invalid upload", status=b"400 Bad Request")

    try:
        with open(path.decode(), "wb") as f:
            f.write(content)
        return http_response(b"Upload OK")
    except Exception as e:
        return http_response(str(e).encode(), status=b"500 Internal Server Error")

def delete_handler(request):
    method, full_path = parse_request_line(request)
    path, params = parse_query(full_path)

    target = params.get(b"path", None)
    if not target:
        return http_response(b"Missing path", status=b"400 Bad Request")

    target = target.decode()

    # TODO define a function for recresivly removing directories
    try:
        st = os.stat(target)

        if st[0] & 0x4000:
            for name in os.listdir(target):
                try:
                    os.remove(target.rstrip("/") + "/" + name)
                except:
                    pass
            os.rmdir(target)
        else:
            os.remove(target)

        return http_response(b"Deleted")

    except Exception as e:
        return http_response(str(e).encode(), status=b"500 Internal Server Error")


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
    height: 50vh;
    overflow: auto;
    display: grid;
    grid-template-columns: 40px 1fr 100px;
    gap: 5px;
    margin-top: 10px;
}

#list div {
    padding: 5px;
    border-bottom: 1px solid #eee;
}

#list div:nth-child(3n+2) {
    cursor: pointer;
    color: #0077cc;
}

#list div:nth-child(3n+2):hover {
    text-decoration: underline;
}

.icon-dir {
    color: green;
    font-weight: bold;
}

.icon-file {
    color: #555;
}

#fileForm {
    width: 600px;
    max-width: 90vw;
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

    files.forEach(item => {
        let name = item[0];
        let type = item[1];
        let sizeVal = item[2] || 0;

        let icon = cr('div', 'class', (type==2 ? 'icon-dir' : 'icon-file'), 'textContent', (type==2 ? "📁" : "📄"));
        let link = cr('div', 'textContent', name);
        let size = cr('div', 'textContent', sizeVal + ' B');

        let full = (path.endsWith("/") ? path : path + "/") + name;

        if (type == 2) {
            link.onclick = () => {
                document.getElementById("path").value = full;
                listDir();
            };
        } else {
            // Fixed popover opening
            link.setAttribute('popovertarget', 'fileForm');
            link.onclick = () => {
                document.getElementById("file_path").value = full;
                // Explicitly show the popover (this is the missing piece)
                document.getElementById("fileForm").showPopover();
            };
        }

        list.appendChild(icon);
        list.appendChild(link);
        list.appendChild(size);
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
