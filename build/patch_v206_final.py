from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()

pubspec = root / "app/pubspec.yaml"
text = pubspec.read_text(encoding="utf-8")
if "version: 2.0.5+205" not in text:
    raise SystemExit("Expected v2.0.5 before v2.0.6")
pubspec.write_text(text.replace("version: 2.0.5+205", "version: 2.0.6+206", 1), encoding="utf-8")

runtime = root / "app/android/app/src/main/kotlin/com/orailnoor/droiddesk/runtime/LinuxRuntime.kt"
text = runtime.read_text(encoding="utf-8")

old = """            export GDK_BACKEND=x11
            export MOZ_ENABLE_WAYLAND=0
            export MOZ_DBUS_REMOTE=0
"""
new = """            export GDK_BACKEND=x11
            export MOZ_ENABLE_WAYLAND=0
            export MOZ_DBUS_REMOTE=0
            export TMPDIR="${tmpDir.absolutePath}"
            export XDG_RUNTIME_DIR="${tmpDir.absolutePath}"
"""
if old not in text:
    raise SystemExit("Firefox launcher block changed")
text = text.replace(old, new, 1)

old = """            export DISPLAY="${'$'}{DISPLAY:-:0}"
            export QT_QPA_PLATFORM=xcb
            exec "${File(binDir, "vlc").absolutePath}" "${'$'}@"
"""
new = """            export DISPLAY="${'$'}{DISPLAY:-:0}"
            export QT_QPA_PLATFORM=xcb
            export XDG_RUNTIME_DIR="${tmpDir.absolutePath}"
            exec "${File(binDir, "vlc").absolutePath}" "${'
"""
if old not in text:
    raise SystemExit("VLC launcher block changed")
text = text.replace(old, new, 1)

old = """                "xdg-mime default vlc-droiddesk.desktop video/webm >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/mpeg >/dev/null 2>&1 || true",
"""
new = """                "xdg-mime default vlc-droiddesk.desktop video/webm >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop video/quicktime >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop video/x-msvideo >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/mpeg >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/flac >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/ogg >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/x-wav >/dev/null 2>&1 || true",
"""
if old not in text:
    raise SystemExit("VLC MIME block changed")
text = text.replace(old, new, 1)

runtime.write_text(text, encoding="utf-8")

print("Applied v2.0.6 final runtime hardening.")
}@"
"""
if old not in text:
    raise SystemExit("VLC launcher block changed")
text = text.replace(old, new, 1)

old = """                "xdg-mime default vlc-droiddesk.desktop video/webm >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/mpeg >/dev/null 2>&1 || true",
"""
new = """                "xdg-mime default vlc-droiddesk.desktop video/webm >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop video/quicktime >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop video/x-msvideo >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/mpeg >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/flac >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/ogg >/dev/null 2>&1 || true; " +
                "xdg-mime default vlc-droiddesk.desktop audio/x-wav >/dev/null 2>&1 || true",
"""
if old not in text:
    raise SystemExit("VLC MIME block changed")
text = text.replace(old, new, 1)

runtime.write_text(text, encoding="utf-8")

print("Applied v2.0.6 final runtime hardening.")
