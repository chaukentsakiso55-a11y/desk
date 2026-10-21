#!/usr/bin/env python3
import html
import json
import os
import re
import socket
import subprocess
import threading
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HOME = Path.home()
PREFIX = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
CONFIG = HOME / ".config" / "ember"
KEY_FILE = CONFIG / "gemini_api_key"
MODEL_FILE = CONFIG / "gemini_model"
HOST = "127.0.0.1"
PORT = 8765
BRIDGE = "\0droiddesk.android-app-launcher"
DEFAULT_MODEL = "gemini-2.5-flash"
CHAT = []
LOCK = threading.Lock()

HTML = r'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ember</title>
<style>
:root{color-scheme:dark;--bg:#070b12;--card:#111827;--line:#22304a;--accent:#53b9ff;--accent2:#8b5cf6;--text:#edf5ff;--muted:#91a2bb}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 70% 10%,#151f3c 0,#070b12 42%);font:15px system-ui,sans-serif;color:var(--text)}
header{padding:22px 24px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:14px;position:sticky;top:0;background:#070b12e8;backdrop-filter:blur(12px)}
.core{width:40px;height:40px;border-radius:50%;background:radial-gradient(circle,#fff 0 8%,#53b9ff 9% 25%,#8b5cf6 26% 47%,transparent 48%);box-shadow:0 0 30px #53b9ff88}
h1{font-size:20px;margin:0}.sub{color:var(--muted);font-size:12px}
main{max-width:1080px;margin:auto;padding:18px}.tabs{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}.tabs button{background:#0e1625;border:1px solid var(--line);color:var(--text);padding:10px 14px;border-radius:12px}.tabs button.active{border-color:var(--accent);box-shadow:0 0 18px #53b9ff44}
.panel{display:none}.panel.active{display:block}.card{background:linear-gradient(180deg,#121b2c,#0d1421);border:1px solid var(--line);border-radius:18px;padding:16px;margin-bottom:14px}
.row{display:flex;gap:10px;flex-wrap:wrap}.row>*{flex:1;min-width:160px}
input,textarea,select{width:100%;background:#08101d;border:1px solid #2a3851;color:var(--text);padding:11px;border-radius:10px;outline:none}textarea{min-height:90px}
button.action{background:linear-gradient(135deg,var(--accent2),var(--accent));border:0;color:white;font-weight:700;padding:11px 14px;border-radius:10px;cursor:pointer}
button.secondary{background:#162236;border:1px solid #30425f;color:var(--text);padding:10px 12px;border-radius:10px;cursor:pointer}
#chat{height:360px;overflow:auto;padding:10px;background:#080f1a;border-radius:12px;border:1px solid var(--line)}.msg{padding:10px 12px;margin:8px 0;border-radius:12px;white-space:pre-wrap}.user{background:#17304e;margin-left:15%}.bot{background:#171f31;margin-right:15%}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:10px}.app{padding:12px;border:1px solid var(--line);border-radius:12px;background:#0d1522}.app b{display:block;margin-bottom:5px}.muted{color:var(--muted)}.status{font-size:12px;color:#8bd5ff;margin-top:8px}
</style>
</head>
<body>
<header><div class="core"></div><div><h1>Ember</h1><div class="sub">MARK LI control core · DroidDesk built-in</div></div></header>
<main>
<div class="tabs">
<button class="active" data-tab="assistant">Assistant</button>
<button data-tab="apps">Apps & Control</button>
<button data-tab="whatsapp">WhatsApp</button>
<button data-tab="settings">Settings</button>
</div>

<section id="assistant" class="panel active">
<div class="card"><div id="chat"></div><div class="row" style="margin-top:10px"><textarea id="prompt" placeholder="Ask Ember anything..."></textarea><button class="action" onclick="sendChat()">Send</button></div><div id="chatStatus" class="status"></div></div>
</section>

<section id="apps" class="panel">
<div class="card"><h3>Linux applications</h3><p class="muted">Launch apps installed inside DroidDesk.</p><div id="appsGrid" class="grid"></div></div>
<div class="card"><h3>Browser control</h3><div class="row"><input id="url" placeholder="https://example.com"><button class="action" onclick="openUrl()">Open URL</button></div></div>
</section>

<section id="whatsapp" class="panel">
<div class="card"><h3>WhatsApp</h3><p class="muted">Uses your normal authenticated WhatsApp/WhatsApp Web session. Ember does not bypass login or auto-send messages.</p>
<div class="row"><button class="action" onclick="wa('app')">Open WhatsApp</button><button class="secondary" onclick="wa('web')">Open WhatsApp Web</button></div></div>
<div class="card"><h3>Compose</h3><div class="row"><input id="waNumber" placeholder="Phone number with country code"><textarea id="waText" placeholder="Message"></textarea></div><button class="action" onclick="wa('compose')">Open message in WhatsApp</button></div>
</section>

<section id="settings" class="panel">
<div class="card"><h3>Gemini API</h3><p class="muted">The key is stored only in your DroidDesk Linux home, not in the public APK or GitHub repository.</p>
<div class="row"><input id="apiKey" type="password" placeholder="Gemini API key"><input id="model" value="gemini-2.5-flash" placeholder="Model"></div><button class="action" onclick="saveSettings()">Save locally</button><div id="settingsStatus" class="status"></div></div>
</section>
</main>
<script>
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button,.panel').forEach(x=>x.classList.remove('active'));b.classList.add('active');document.getElementById(b.dataset.tab).classList.add('active');if(b.dataset.tab==='apps')loadApps()})
async function api(path,data={}){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});return await r.json()}
function addMsg(role,text){let d=document.createElement('div');d.className='msg '+(role==='user'?'user':'bot');d.textContent=text;document.getElementById('chat').appendChild(d);d.scrollIntoView()}
async function sendChat(){let p=document.getElementById('prompt');let text=p.value.trim();if(!text)return;p.value='';addMsg('user',text);document.getElementById('chatStatus').textContent='Thinking...';let r=await api('/api/chat',{text});addMsg('bot',r.reply||r.error||'No response');document.getElementById('chatStatus').textContent=''}
async function loadApps(){let r=await fetch('/api/apps');let apps=await r.json();let g=document.getElementById('appsGrid');g.innerHTML='';apps.forEach(a=>{let d=document.createElement('div');d.className='app';d.innerHTML='<b></b><span class="muted"></span><br><button class="secondary">Open</button>';d.querySelector('b').textContent=a.name;d.querySelector('span').textContent=a.id;d.querySelector('button').onclick=()=>api('/api/launch',{id:a.id});g.appendChild(d)})}
async function openUrl(){let u=document.getElementById('url').value.trim();let r=await api('/api/url',{url:u});if(!r.ok)alert(r.error||'Could not open URL')}
async function wa(action){let data={action};if(action==='compose'){data.number=document.getElementById('waNumber').value;data.text=document.getElementById('waText').value}let r=await api('/api/whatsapp',data);if(!r.ok)alert(r.error||'WhatsApp action failed')}
async function saveSettings(){let r=await api('/api/settings',{key:document.getElementById('apiKey').value,model:document.getElementById('model').value});document.getElementById('settingsStatus').textContent=r.ok?'Saved on this device':'Could not save'}
fetch('/api/settings').then(r=>r.json()).then(s=>{document.getElementById('model').value=s.model||'gemini-2.5-flash';document.getElementById('settingsStatus').textContent=s.hasKey?'API key is configured on this device':'Add your API key to enable chat'})
</script>
</body></html>'''

def bridge(command):
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(BRIDGE)
        client.sendall((command + "\n").encode())
        client.close()
        return True
    except Exception:
        return False

def open_url(url):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    firefox = PREFIX / "bin" / "firefox"
    if firefox.exists():
        try:
            subprocess.Popen([str(firefox), "--new-window", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            pass
    return bridge("url:" + url)

def desktop_apps():
    result = {}
    for directory in (PREFIX / "share" / "applications", HOME / ".local" / "share" / "applications"):
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.desktop"):
            try:
                fields = {}
                for line in path.read_text(errors="ignore").splitlines():
                    if "=" in line:
                        k, v = line.split("=", 1)
                        fields.setdefault(k, v)
                if fields.get("Type", "Application") != "Application":
                    continue
                if fields.get("NoDisplay", "").lower() == "true":
                    continue
                name = fields.get("Name")
                if not name:
                    continue
                result[path.stem] = {"id": path.stem, "name": name}
            except Exception:
                pass
    return sorted(result.values(), key=lambda x: x["name"].lower())[:180]

def safe_launch(app_id):
    ids = {a["id"] for a in desktop_apps()}
    if app_id not in ids or not re.fullmatch(r"[A-Za-z0-9_.+-]{1,160}", app_id):
        return False
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
    try:
        subprocess.Popen(["gtk-launch", app_id], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def load_key():
    if KEY_FILE.is_file():
        return KEY_FILE.read_text().strip()
    legacy = HOME / ".config" / "api_keys.json"
    if legacy.is_file():
        try:
            data = json.loads(legacy.read_text())
            return (data.get("gemini") or data.get("GEMINI_API_KEY") or "").strip()
        except Exception:
            pass
    return os.environ.get("GEMINI_API_KEY", "").strip()

def model_name():
    if MODEL_FILE.is_file():
        value = MODEL_FILE.read_text().strip()
        if re.fullmatch(r"[A-Za-z0-9._-]{1,100}", value):
            return value
    return DEFAULT_MODEL

def gemini_chat(text):
    key = load_key()
    if not key:
        return None, "Open Settings and save your Gemini API key first."
    model = model_name()
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/" + urllib.parse.quote(model, safe=".-_") + ":generateContent?key=" + urllib.parse.quote(key, safe="")
    with LOCK:
        recent = CHAT[-10:]
    contents = []
    for role, value in recent:
        contents.append({"role": "user" if role == "user" else "model", "parts": [{"text": value}]})
    contents.append({"role": "user", "parts": [{"text": text}]})
    body = json.dumps({"contents": contents}).encode()
    request = urllib.request.Request(endpoint, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            payload = json.loads(response.read().decode())
        candidates = payload.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        answer = "\n".join(p.get("text", "") for p in parts if p.get("text")).strip()
        if not answer:
            return None, "Gemini returned no text response."
        with LOCK:
            CHAT.extend([("user", text), ("model", answer)])
            del CHAT[:-20]
        return answer, None
    except Exception as exc:
        return None, "Gemini request failed: " + str(exc)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def send_json(self, data, code=200):
        raw = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def read_json(self):
        try:
            size = min(int(self.headers.get("Content-Length", "0")), 65536)
            return json.loads(self.rfile.read(size) or b"{}")
        except Exception:
            return {}

    def do_GET(self):
        if self.path == "/":
            raw = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        elif self.path == "/api/apps":
            self.send_json(desktop_apps())
        elif self.path == "/api/settings":
            self.send_json({"hasKey": bool(load_key()), "model": model_name()})
        else:
            self.send_error(404)

    def do_POST(self):
        data = self.read_json()
        if self.path == "/api/chat":
            text = str(data.get("text", "")).strip()[:12000]
            if not text:
                return self.send_json({"error": "Message is empty"}, 400)
            reply, error = gemini_chat(text)
            return self.send_json({"reply": reply} if reply else {"error": error}, 200 if reply else 503)
        if self.path == "/api/launch":
            return self.send_json({"ok": safe_launch(str(data.get("id", "")))})
        if self.path == "/api/url":
            url = str(data.get("url", "")).strip()[:2000]
            ok = open_url(url)
            return self.send_json({"ok": ok, "error": None if ok else "Only http/https URLs are supported."})
        if self.path == "/api/whatsapp":
            action = str(data.get("action", ""))
            if action == "app":
                return self.send_json({"ok": bridge("com.whatsapp") or bridge("com.whatsapp.w4b")})
            if action == "web":
                return self.send_json({"ok": open_url("https://web.whatsapp.com/")})
            if action == "compose":
                number = re.sub(r"\D", "", str(data.get("number", "")))[:20]
                text = str(data.get("text", ""))[:4000]
                if not number:
                    return self.send_json({"ok": False, "error": "Enter a phone number with country code."}, 400)
                url = "https://wa.me/" + number + "?text=" + urllib.parse.quote(text)
                return self.send_json({"ok": open_url(url)})
            return self.send_json({"ok": False, "error": "Unknown WhatsApp action"}, 400)
        if self.path == "/api/settings":
            key = str(data.get("key", "")).strip()
            model = str(data.get("model", DEFAULT_MODEL)).strip()
            CONFIG.mkdir(parents=True, exist_ok=True)
            if key:
                KEY_FILE.write_text(key)
                os.chmod(KEY_FILE, 0o600)
            if re.fullmatch(r"[A-Za-z0-9._-]{1,100}", model):
                MODEL_FILE.write_text(model)
                os.chmod(MODEL_FILE, 0o600)
            return self.send_json({"ok": True})
        self.send_error(404)

def main():
    CONFIG.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()

if __name__ == "__main__":
    main()
