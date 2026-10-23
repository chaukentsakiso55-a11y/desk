from pathlib import Path
import json
import sys

root = Path(sys.argv[1]).resolve()

main = root / "main.py"
text = main.read_text(encoding="utf-8")
if not text.startswith("from __future__ import annotations"):
    text = "from __future__ import annotations\n" + text

boot = '''import os as _ember_os\nimport sys as _ember_sys\nfrom pathlib import Path as _EmberPath\n_EMBER_ROOT = _EmberPath(__file__).resolve().parent\n_EMBER_VENDOR = _EMBER_ROOT / "vendor"\nif _EMBER_VENDOR.is_dir():\n    _ember_sys.path.insert(0, str(_EMBER_VENDOR))\n_ember_os.environ.setdefault("QT_QPA_PLATFORM", "xcb")\n_ember_os.environ.setdefault("GDK_BACKEND", "x11")\n\n'''
marker = "import platform as _platform\n"
if boot not in text:
    if marker not in text:
        raise SystemExit("Ember main import marker changed")
    text = text.replace(marker, boot + marker, 1)

old = '''import sounddevice as sd\nimport numpy as np\nfrom google import genai\nfrom google.genai import types\n'''
new = '''try:\n    import sounddevice as sd\nexcept Exception:\n    sd = None\nimport numpy as np\ntry:\n    from google import genai\n    from google.genai import types\nexcept Exception:\n    genai = None\n    types = None\n'''
if old not in text:
    raise SystemExit("Ember core dependency imports changed")
text = text.replace(old, new, 1)

run_marker = '''    async def run(self):\n        self._loop = asyncio.get_event_loop()\n'''
run_new = '''    async def run(self):\n        self._loop = asyncio.get_event_loop()\n        if genai is None or types is None or sd is None:\n            missing = []\n            if genai is None or types is None:\n                missing.append("Gemini Live SDK")\n            if sd is None:\n                missing.append("PortAudio voice bridge")\n            self.ui.write_log(\n                "SYS: DroidDesk mode active. Text chat, tools, files and controls are ready. "\n                + "Live voice is waiting for: " + ", ".join(missing)\n            )\n            self.ui.set_state("LISTENING")\n            while True:\n                await asyncio.sleep(3600)\n'''
if run_marker not in text:
    raise SystemExit("Ember run() marker changed")
text = text.replace(run_marker, run_new, 1)
main.write_text(text, encoding="utf-8")

config_manager = root / "memory/config_manager.py"
text = config_manager.read_text(encoding="utf-8")
text = text.replace('DEFAULT_VOICE    = "Charon"', 'DEFAULT_VOICE    = "Aoede"')
config_manager.write_text(text, encoding="utf-8")

ui = root / "ui.py"
text = ui.read_text(encoding="utf-8")
old = 'json.dumps({"gemini_api_key": key, "os_system": os_name}, indent=4),'
new = 'json.dumps({"gemini_api_key": key, "os_system": os_name, "multi_provider_enabled": True, "voice_name": "Aoede"}, indent=4),'
if old not in text:
    raise SystemExit("Ember setup save block changed")
text = text.replace(old, new, 1)
if 'self._win.show()' in text:
    text = text.replace(
        '        self._win.show()\n',
        '        self._win.showMaximized() if _OS == "Linux" else self._win.show()\n',
        1,
    )
ui.write_text(text, encoding="utf-8")

send_message = root / "actions/send_message.py"
text = send_message.read_text(encoding="utf-8")
if "import platform\n" not in text:
    text = text.replace("import json\n", "import json\nimport platform\n", 1)
old = '''def _get_os() -> str:\n    try:\n        cfg = json.loads(\n            (_base_dir() / "config" / "api_keys.json").read_text(encoding="utf-8")\n        )\n        return cfg.get("os_system", "windows").lower()\n    except Exception:\n        return "windows"\n'''
new = '''def _get_os() -> str:\n    try:\n        cfg = json.loads(\n            (_base_dir() / "config" / "api_keys.json").read_text(encoding="utf-8")\n        )\n        configured = str(cfg.get("os_system", "") or "").strip().lower()\n        if configured:\n            return configured\n    except Exception:\n        pass\n    detected = platform.system().lower()\n    return "mac" if detected == "darwin" else detected or "linux"\n'''
if old not in text:
    raise SystemExit("Ember send_message OS block changed")
text = text.replace(old, new, 1)
old = '''def _send_whatsapp(receiver: str, message: str) -> str:
    # Prefer the persistent WhatsApp Web controller because it can verify the
    # chat and message box through the DOM instead of relying on whichever
    # control happens to have focus. If it is not connected yet, fall back to
    # the installed desktop/PWA path so older setups keep working.
    try:
        from core import whatsapp_web
        result = whatsapp_web.send_message(receiver, message)
        if result.get("ok"):
            return f"Message sent to {receiver} via WhatsApp Web."
        web_error = result.get("error", "WhatsApp Web send failed")
    except Exception as e:
        web_error = str(e)
    desktop = _desktop_send("WhatsApp", receiver, message)
    if "sent" in desktop.lower():
        return desktop
    return f"WhatsApp Web: {web_error}; desktop fallback: {desktop}"
'''
new = '''def _send_whatsapp(receiver: str, message: str) -> str:
    try:
        from core import whatsapp_web
        result = whatsapp_web.send_message(receiver, message)
        if result.get("ok"):
            return f"Message sent to {receiver} via WhatsApp Web."
        web_error = result.get("error", "WhatsApp Web send failed")
    except Exception as e:
        web_error = str(e)
    if _get_os() == "linux":
        _require_pyautogui()
        if not _open_browser_url("https://web.whatsapp.com/"):
            return f"WhatsApp Web: {web_error}; Firefox could not be opened."
        time.sleep(5.0)
        pyautogui.hotkey("ctrl", "k")
        time.sleep(0.7)
        _clear_and_paste(receiver)
        time.sleep(1.0)
        pyautogui.press("enter")
        time.sleep(0.8)
        _paste_text(message)
        time.sleep(0.2)
        pyautogui.press("enter")
        return f"Message sent to {receiver} via WhatsApp Web."
    desktop = _desktop_send("WhatsApp", receiver, message)
    if "sent" in desktop.lower():
        return desktop
    return f"WhatsApp Web: {web_error}; desktop fallback: {desktop}"
'''
if old not in text:
    raise SystemExit("Ember WhatsApp block changed")
text = text.replace(old, new, 1)
send_message.write_text(text, encoding="utf-8")

screen = root / "actions/screen_processor.py"
text = screen.read_text(encoding="utf-8")
if "import platform\n" not in text:
    text = text.replace("import json\n", "import json\nimport platform\n", 1)
old = '''def _get_os() -> str:\n    return _load_config().get("os_system", "windows").lower()\n'''
new = '''def _get_os() -> str:\n    configured = str(_load_config().get("os_system", "") or "").strip().lower()\n    if configured:\n        return configured\n    detected = platform.system().lower()\n    return "mac" if detected == "darwin" else detected or "linux"\n'''
if old not in text:
    raise SystemExit("Ember screen OS block changed")
text = text.replace(old, new, 1)
screen.write_text(text, encoding="utf-8")

config = root / "config/api_keys.json"
config.parent.mkdir(parents=True, exist_ok=True)
config.write_text(json.dumps({
    "gemini_api_key": "",
    "os_system": "linux",
    "multi_provider_enabled": True,
    "voice_name": "Aoede",
}, indent=2), encoding="utf-8")
(root / "config/provider_secrets.json").write_text("{}\n", encoding="utf-8")

print("Ember Droid Linux compatibility patch applied.")
