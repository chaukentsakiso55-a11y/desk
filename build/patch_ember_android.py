from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()

main = root / "main.py"
text = main.read_text(encoding="utf-8")
needle = "from __future__ import annotations\nimport sys\n"
replacement = """from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "vendor"
if VENDOR.is_dir():
    sys.path.insert(0, str(VENDOR))
os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
os.environ.setdefault("EMBER_DATA_DIR", str(Path.home() / ".config" / "ember"))
"""
if needle not in text:
    raise SystemExit("Ember main.py header changed")
main.write_text(text.replace(needle, replacement, 1), encoding="utf-8")

state = root / "desktop/state.py"
text = state.read_text(encoding="utf-8")
start = text.index("class Vault:")
new_vault = r'''class Vault:
    @staticmethod
    def _path():
        path = DATA / "provider_secrets.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def get(pid):
        env_names = {
            "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY"),
            "openai": ("OPENAI_API_KEY",),
            "anthropic": ("ANTHROPIC_API_KEY",),
            "groq": ("GROQ_API_KEY",),
            "openrouter": ("OPENROUTER_API_KEY",),
            "grok": ("XAI_API_KEY",),
            "xkiro": ("XKIRO_API_KEY",),
        }
        values = []
        for name in env_names.get(pid, ()):
            value = os.environ.get(name, "").strip()
            if value and value not in values:
                values.append(value)
        try:
            saved = read_json(Vault._path(), {})
            for value in saved.get(pid, []):
                value = str(value or "").strip()
                if value and value not in values:
                    values.append(value)
        except Exception:
            pass
        return values

    @staticmethod
    def set(pid, keys):
        path = Vault._path()
        saved = read_json(path, {})
        saved[str(pid)] = [str(k).strip() for k in keys if str(k).strip()]
        write_json(path, saved)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
'''
state.write_text(text[:start] + new_vault + "\n", encoding="utf-8")

services = root / "desktop/services.py"
text = services.read_text(encoding="utf-8")
old = """                    if pid=='gemini':
                        from desktop.gemini_backend import chat
                        return chat(turns,tools,p.get('model',''),budget,settings['temperature'])
                    return pool.chat(turns,tools=tools,timeout=45,max_tokens=budget,temperature=settings['temperature'],provider_id=pid)
"""
new = """                    return pool.chat(turns,tools=tools,timeout=45,max_tokens=budget,temperature=settings['temperature'],provider_id=pid)
"""
if old not in text:
    raise SystemExit("Gemini request block changed")
text = text.replace(old, new, 1)
old2 = """        def test():
            if pid=='gemini':
                from desktop.gemini_backend import models
                return models()
            p=next(x for x in self.store.providers['providers'] if x['id']==pid)
"""
new2 = """        def test():
            p=next(x for x in self.store.providers['providers'] if x['id']==pid)
"""
if old2 not in text:
    raise SystemExit("Gemini test block changed")
text = text.replace(old2, new2, 1)
services.write_text(text, encoding="utf-8")

settings = root / "desktop/settings.py"
text = settings.read_text(encoding="utf-8")
text = text.replace("Start Ember on Windows startup", "Start Ember with desktop")
text = text.replace("'Windows System'", "'Android / Linux System'")
text = text.replace("'Windows System':'Control apps and folders'", "'Android / Linux System':'Control apps and folders'")
settings.write_text(text, encoding="utf-8")

reference = root / "desktop/reference_settings.py"
text = reference.read_text(encoding="utf-8")
text = text.replace("Start Ember on Windows startup", "Start Ember with desktop")
text = text.replace("'Windows System'", "'Android / Linux System'")
text = text.replace("'Windows System':'⊞'", "'Android / Linux System':'⊞'")
text = text.replace("'Windows System':'Control apps and folders'", "'Android / Linux System':'Control apps and folders'")
reference.write_text(text, encoding="utf-8")

print("Ember Android/Linux compatibility patch applied.")
