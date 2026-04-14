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

    try:
        with open(target.decode(), "wb") as f:
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
<html>
<body>

<h3>File Explorer</h3>

<input id="path" value="/" style="width:300px">
<button onclick="listDir()">List</button>

<ul id="list" style="height:50vh;overflow:auto;"></ul>

<hr>

<h3>Editor</h3>
<input id="filepath" style="width:300px"><br><br>
<textarea id="editor" rows="15" cols="80"></textarea><br>

<button onclick="loadFile()">Load</button>
<button onclick="saveFile()">Save</button>

<script>
async function listDir() {
  try {
    let path = document.getElementById("path").value;
    let res = await fetch("/dir?path=" + encodeURIComponent(path));
    let files = await res.json();

    let list = document.getElementById("list");
    list.innerHTML = "";

    files.forEach(item => {
      let li = document.createElement("li");

      let name = item[0];
      let type = item[1];

      li.textContent = `[${type==2 ? "D" : "F"}] ${name} ${item[2]}B`;

      li.onclick = () => {
        let full = (path.endsWith("/") ? path : path + "/") + name;

        if (type == 2) {
          document.getElementById("path").value = full;
          listDir();
        } else {
          document.getElementById("filepath").value = full;
        }
      };

      list.appendChild(li);
    });
  } catch(e) {
    alert("Error loading directory: " + String(e));
  }
}

async function loadFile() {
  let path = document.getElementById("filepath").value;
  let res = await fetch("/file?path=" + encodeURIComponent(path));
  let text = await res.text();
  document.getElementById("editor").value = text;
}

async function saveFile() {
  let path = document.getElementById("filepath").value;
  let content = document.getElementById("editor").value;

  await fetch("/file?path=" + encodeURIComponent(path), {
    method: "POST",
    body: content
  });

  alert("Saved");
}
</script>

</body>
</html>
"""
    return http_response(html, content_type=b"text/html")