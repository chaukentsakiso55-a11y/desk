#!/usr/bin/env python3
import gzip
import io
import json
import re
import urllib.request

SOURCES = [
    [
        "https://packages.termux.dev/apt/termux-main/dists/stable/main/binary-aarch64/Packages.gz",
        "https://packages-cf.termux.dev/apt/termux-main/dists/stable/main/binary-aarch64/Packages.gz",
    ],
    [
        "https://packages.termux.dev/apt/termux-x11/dists/x11/main/binary-aarch64/Packages.gz",
        "https://packages-cf.termux.dev/apt/termux-x11/dists/x11/main/binary-aarch64/Packages.gz",
    ],
]

DESKTOPS = {
    "xfce4": ["xfce4", "xfce4-terminal", "xfce4-whiskermenu-plugin", "xfce4-notifyd", "thunar", "mousepad"],
    "mate": ["mate", "mate-terminal", "gvfs", "mate-applets", "mate-notification-daemon", "thunar"],
    "lxqt": ["lxqt", "qterminal", "pcmanfm-qt", "featherpad"],
    "kde": ["plasma-desktop", "konsole", "dolphin"],
}

COMMON = ["xorg-xrandr", "pulseaudio", "xclip", "xkeyboard-config", "git", "wget", "curl", "openssh", "htop", "python", "clang", "mesa"]
KEY_RUNTIME = {
    "xfce4": ["xfce4-session", "xfce4-panel", "xfdesktop", "xfwm4"],
    "mate": ["mate-session-manager", "mate-panel", "marco", "caja"],
    "lxqt": ["lxqt-session", "lxqt-panel", "pcmanfm-qt"],
    "kde": ["plasma-workspace", "kwin-x11", "plasma-desktop"],
}

def fetch(urls):
    last = None
    for url in urls:
        print("FETCH", url, flush=True)
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "DroidDesk-Audit/2.0.3"},
            )
            with urllib.request.urlopen(request, timeout=60) as r:
                data = r.read()
            return gzip.decompress(data).decode("utf-8", "replace")
        except Exception as error:
            print("FETCH FAILED", type(error).__name__, error, flush=True)
            last = error
    raise last

def parse(text):
    pkgs = {}
    for block in re.split(r"\n\s*\n", text):
        fields = {}
        key = None
        for line in block.splitlines():
            if line.startswith(" ") and key:
                fields[key] = fields.get(key, "") + " " + line.strip()
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key] = value.strip()
        name = fields.get("Package")
        if name:
            pkgs[name] = fields
    return pkgs

def dep_names(expr):
    result = []
    if not expr:
        return result
    for chunk in expr.split(","):
        alt = chunk.split("|", 1)[0].strip()
        alt = re.sub(r"\s*\(.*?\)", "", alt).strip()
        alt = re.sub(r":\w+$", "", alt)
        if alt:
            result.append(alt)
    return result

packages = {}
for urls in SOURCES:
    packages.update(parse(fetch(urls)))

missing = []
for de, roots in DESKTOPS.items():
    for p in roots + COMMON + KEY_RUNTIME[de]:
        if p not in packages:
            missing.append((de, p))

gpu_candidates = sorted(
    p for p in packages
    if "freedreno" in p or "vulkan-loader" in p or p.startswith("mesa-vulkan")
)
print("GPU CANDIDATES:", gpu_candidates)

if missing:
    print("MISSING PACKAGES:", missing)
    raise SystemExit(2)

def closure(roots):
    seen = set()
    stack = list(roots)
    while stack:
        p = stack.pop()
        if p in seen:
            continue
        meta = packages.get(p)
        if not meta:
            continue
        seen.add(p)
        for field in ("Pre-Depends", "Depends"):
            stack.extend(dep_names(meta.get(field, "")))
    return seen

result = {}
for de, roots in DESKTOPS.items():
    all_roots = roots + COMMON
    deps = closure(all_roots)
    dl = sum(int(packages[p].get("Size", "0") or 0) for p in deps if p in packages)
    installed_kib = sum(int(packages[p].get("Installed-Size", "0") or 0) for p in deps if p in packages)
    result[de] = {
        "roots": roots,
        "runtime": KEY_RUNTIME[de],
        "package_count": len(deps),
        "download_bytes": dl,
        "download_mib": round(dl / 1024 / 1024, 1),
        "installed_mib": round(installed_kib / 1024, 1),
        "largest": sorted(
            [
                (p, int(packages[p].get("Size", "0") or 0))
                for p in deps if p in packages
            ],
            key=lambda x: x[1],
            reverse=True,
        )[:10],
    }

print(json.dumps(result, indent=2))
with open("desktop-audit.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)

# Current launch-chain sanity checks based on Termux package layout/dependencies.
assert "xfce4-session" in closure(DESKTOPS["xfce4"] + COMMON)
assert "mate-session-manager" in closure(DESKTOPS["mate"] + COMMON)
assert "lxqt-session" in closure(DESKTOPS["lxqt"] + COMMON)
assert "plasma-workspace" in closure(DESKTOPS["kde"] + COMMON)
assert "kwin-x11" in closure(DESKTOPS["kde"] + COMMON)

print("ALL_DESKTOP_PACKAGE_GRAPHS_OK")


# Verify the exact desktop launch commands against current package archives.
REPO_BASE = {
    "main": "https://packages.termux.dev/apt/termux-main/",
    "x11": "https://packages.termux.dev/apt/termux-x11/",
}
BINARIES = {
    "xfce4-session": ["bin/xfce4-session"],
    "mate-session-manager": ["bin/mate-session"],
    "lxqt-session": ["bin/startlxqt"],
    "plasma-workspace": ["bin/startplasma-x11", "bin/plasmashell"],
    "kwin-x11": ["bin/kwin_x11"],
}

import os
import subprocess
import tempfile

def download_pkg(name):
    meta = packages[name]
    filename = meta.get("Filename")
    if not filename:
        raise RuntimeError(f"No Filename field for {name}")
    repo = "x11" if name in {
        "xfce4-session", "mate-session-manager", "lxqt-session",
        "plasma-workspace", "kwin-x11"
    } else "main"
    url = REPO_BASE[repo] + filename
    request = urllib.request.Request(url, headers={"User-Agent": "DroidDesk-Audit/2.0.3"})
    with urllib.request.urlopen(request, timeout=120) as r:
        data = r.read()
    fd, path = tempfile.mkstemp(suffix=".deb")
    os.close(fd)
    with open(path, "wb") as out:
        out.write(data)
    return path

binary_report = {}
for pkg, expected in BINARIES.items():
    path = download_pkg(pkg)
    try:
        listing = subprocess.check_output(["dpkg-deb", "-c", path], text=True, errors="replace")
    finally:
        os.unlink(path)
    missing_bins = [b for b in expected if f"/{b}" not in listing]
    binary_report[pkg] = {"expected": expected, "missing": missing_bins}
    if missing_bins:
        print("MISSING BINARIES", pkg, missing_bins)
        raise SystemExit(3)

print("BINARY_REPORT", json.dumps(binary_report, indent=2))
print("ALL_DESKTOP_START_COMMANDS_OK")
