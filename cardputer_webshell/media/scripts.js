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
