from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()

pubspec = root / "app/pubspec.yaml"
text = pubspec.read_text(encoding="utf-8")
old = "version: 2.0.3+203\n"
new = "version: 2.0.4+204\n"
if old not in text:
    raise SystemExit("Expected v2.0.3 version before v2.0.4 patch")
pubspec.write_text(text.replace(old, new, 1), encoding="utf-8")

runtime = root / "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt"
source = runtime.read_text(encoding="utf-8")

bad = [
    r'deb https://packages.termux.dev/apt/termux-main stable main\\n',
    r'deb https://packages-cf.termux.dev/apt/termux-main stable main\\n',
]
for value in bad:
    if value in source:
        raise SystemExit(f"Malformed literal newline still present: {value}")

required = [
    r'deb https://packages.termux.dev/apt/termux-main stable main\n',
    r'deb https://packages-cf.termux.dev/apt/termux-main stable main\n',
]
for value in required:
    if value not in source:
        raise SystemExit(f"Correct repository source missing: {value}")

print("v2.0.4 repository newline validation passed.")
