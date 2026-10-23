#!/usr/bin/env python3
from __future__ import annotations
import os
import pathlib
import shutil
import socket
import subprocess
import sys
from PyQt6.QtCore import QFileInfo, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFileIconProvider,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

BRIDGE = "\0droiddesk.android-app-launcher"
HOME = pathlib.Path.home()
PHONE = pathlib.Path("/storage/emulated/0")
TRASH = HOME / ".local/share/Trash/files"
VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".3gp", ".mpeg", ".mpg", ".ts", ".flv"}
AUDIO_EXT = {".mp3", ".m4a", ".aac", ".flac", ".wav", ".ogg", ".opus", ".wma"}


def bridge(command: str) -> bool:
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(BRIDGE)
        s.sendall((command + "\n").encode())
        s.close()
        return True
    except Exception:
        return False


def readable(path: pathlib.Path) -> bool:
    try:
        next(path.iterdir(), None)
        return True
    except StopIteration:
        return path.exists()
    except Exception:
        return False


def safe_start(path: pathlib.Path) -> pathlib.Path:
    value = str(path)
    if value.startswith("computer:") or value == "/" or value == "file:///":
        return HOME
    if value.startswith("trash:"):
        TRASH.mkdir(parents=True, exist_ok=True)
        return TRASH
    try:
        p = path.expanduser().resolve()
    except Exception:
        return HOME
    if str(p).startswith("/storage") and not readable(PHONE):
        bridge("storage:request")
        return HOME
    return p if p.exists() else HOME


class Window(QMainWindow):
    def __init__(self, start: pathlib.Path):
        super().__init__()
        self.setWindowTitle("DroidDesk Files")
        self.resize(1180, 760)
        self.current = safe_start(start)
        self.history: list[pathlib.Path] = []
        self.clipboard_paths: list[pathlib.Path] = []
        self.clipboard_cut = False
        self.entries: list[pathlib.Path] = []
        self.icon_provider = QFileIconProvider()
        self._build()
        self.open_dir(self.current, push=False)

    def _build(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        for label, fn in [
            ("←", self.back),
            ("↑", self.up),
            ("⌂", lambda: self.open_dir(HOME)),
            ("Phone", self.phone),
            ("Refresh", self.refresh),
        ]:
            button = QPushButton(label)
            button.clicked.connect(fn)
            toolbar.addWidget(button)
        self.path = QLabel()
        toolbar.addWidget(self.path)

        root = QWidget()
        layout = QHBoxLayout(root)
        split = QSplitter()
        layout.addWidget(split)
        self.setCentralWidget(root)

        self.side = QListWidget()
        self.side.setMaximumWidth(250)
        places = [
            ("Linux Home", HOME),
            ("Desktop", HOME / "Desktop"),
            ("Phone Storage", PHONE),
            ("Downloads", PHONE / "Download"),
            ("Camera", PHONE / "DCIM/Camera"),
            ("Pictures", PHONE / "Pictures"),
            ("Movies", PHONE / "Movies"),
            ("Music", PHONE / "Music"),
            ("Documents", PHONE / "Documents"),
        ]
        for name, path in places:
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.side.addItem(item)
        self.side.itemActivated.connect(
            lambda item: self.open_dir(pathlib.Path(item.data(Qt.ItemDataRole.UserRole)))
        )
        split.addWidget(self.side)

        right = QWidget()
        rv = QVBoxLayout(right)
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Filter"))
        self.filter_box = QLineEdit()
        self.filter_box.setPlaceholderText("Search this folder by name…")
        self.filter_box.textChanged.connect(self.render_entries)
        search_row.addWidget(self.filter_box)
        rv.addLayout(search_row)

        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self.context_menu)
        self.list.itemActivated.connect(self.activate)
        rv.addWidget(self.list)
        split.addWidget(right)
        split.setStretchFactor(1, 1)

    def selected_paths(self) -> list[pathlib.Path]:
        paths = []
        for item in self.list.selectedItems():
            raw = item.data(Qt.ItemDataRole.UserRole)
            if raw:
                paths.append(pathlib.Path(raw))
        return paths

    def phone(self):
        if not readable(PHONE):
            bridge("storage:request")
            QMessageBox.information(
                self,
                "Phone Storage",
                "Android opened the all-files access screen. Grant DroidDesk access, then tap Phone again.",
            )
            return
        self.open_dir(PHONE)

    def open_dir(self, path: pathlib.Path, push: bool = True):
        path = safe_start(path)
        if not path.is_dir():
            return
        if push and self.current != path:
            self.history.append(self.current)
        self.current = path
        self.path.setText(str(path))
        self.filter_box.clear()
        try:
            self.entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except Exception as exc:
            QMessageBox.warning(self, "Files", str(exc))
            return
        self.render_entries()

    def render_entries(self):
        query = self.filter_box.text().strip().lower()
        self.list.clear()
        for path in self.entries:
            if query and query not in path.name.lower():
                continue
            item = QListWidgetItem(path.name)
            item.setIcon(self.icon_provider.icon(QFileInfo(str(path))))
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.list.addItem(item)

    def refresh(self):
        self.open_dir(self.current, push=False)

    def back(self):
        if self.history:
            self.open_dir(self.history.pop(), push=False)

    def up(self):
        parent = self.current.parent
        if str(parent) in ("/", "/data", "/storage") and self.current != PHONE:
            parent = HOME
        self.open_dir(parent)

    def activate(self, item):
        path = pathlib.Path(item.data(Qt.ItemDataRole.UserRole))
        if path.is_dir():
            self.open_dir(path)
            return
        ext = path.suffix.lower()
        local_bin = HOME / ".local/bin"
        try:
            if ext == ".py" and (local_bin / "droiddesk-python-runner").exists():
                subprocess.Popen([str(local_bin / "droiddesk-python-runner"), str(path)])
            elif ext in VIDEO_EXT or ext in AUDIO_EXT:
                wrapper = local_bin / "vlc-droiddesk"
                command = str(wrapper) if wrapper.exists() else os.environ.get("PREFIX", "/data/data/com.termux/files/usr") + "/bin/vlc"
                subprocess.Popen([command, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as exc:
            QMessageBox.warning(self, "Open file", str(exc))

    def context_menu(self, pos):
        menu = QMenu(self)
        selected = self.selected_paths()
        open_action = QAction("Open", self)
        open_action.setEnabled(len(selected) == 1)
        open_action.triggered.connect(lambda: self._open_selected(selected))
        menu.addAction(open_action)
        menu.addSeparator()

        new_folder = menu.addAction("New Folder")
        new_folder.triggered.connect(self.new_folder)
        rename = menu.addAction("Rename")
        rename.setEnabled(len(selected) == 1)
        rename.triggered.connect(lambda: self.rename_path(selected[0]) if selected else None)
        menu.addSeparator()

        copy_action = menu.addAction("Copy")
        copy_action.setEnabled(bool(selected))
        copy_action.triggered.connect(lambda: self.set_clipboard(selected, False))
        cut_action = menu.addAction("Cut")
        cut_action.setEnabled(bool(selected))
        cut_action.triggered.connect(lambda: self.set_clipboard(selected, True))
        paste_action = menu.addAction("Paste")
        paste_action.setEnabled(bool(self.clipboard_paths))
        paste_action.triggered.connect(self.paste)
        menu.addSeparator()

        delete_action = menu.addAction("Delete")
        delete_action.setEnabled(bool(selected))
        delete_action.triggered.connect(lambda: self.delete_paths(selected))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def _open_selected(self, selected: list[pathlib.Path]):
        if not selected:
            return
        for row in range(self.list.count()):
            item = self.list.item(row)
            if pathlib.Path(item.data(Qt.ItemDataRole.UserRole)) == selected[0]:
                self.activate(item)
                return

    def new_folder(self):
        name, ok = QInputDialog.getText(self, "New Folder", "Folder name")
        name = name.strip()
        if not ok or not name:
            return
        try:
            (self.current / name).mkdir()
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "New Folder", str(exc))

    def rename_path(self, path: pathlib.Path):
        name, ok = QInputDialog.getText(self, "Rename", "New name", text=path.name)
        name = name.strip()
        if not ok or not name or name == path.name:
            return
        try:
            path.rename(path.with_name(name))
            self.refresh()
        except Exception as exc:
            QMessageBox.warning(self, "Rename", str(exc))

    def set_clipboard(self, paths: list[pathlib.Path], cut: bool):
        self.clipboard_paths = list(paths)
        self.clipboard_cut = cut

    def unique_destination(self, source: pathlib.Path) -> pathlib.Path:
        target = self.current / source.name
        if not target.exists():
            return target
        stem = source.stem
        suffix = source.suffix
        index = 1
        while True:
            candidate = self.current / f"{stem} ({index}){suffix}"
            if not candidate.exists():
                return candidate
            index += 1

    def paste(self):
        if not self.clipboard_paths:
            return
        failures = []
        for source in list(self.clipboard_paths):
            try:
                if not source.exists():
                    continue
                target = self.unique_destination(source)
                if self.clipboard_cut:
                    shutil.move(str(source), str(target))
                elif source.is_dir():
                    shutil.copytree(source, target)
                else:
                    shutil.copy2(source, target)
            except Exception as exc:
                failures.append(f"{source.name}: {exc}")
        if self.clipboard_cut and not failures:
            self.clipboard_paths = []
            self.clipboard_cut = False
        self.refresh()
        if failures:
            QMessageBox.warning(self, "Paste", "\n".join(failures))

    def delete_paths(self, paths: list[pathlib.Path]):
        if not paths:
            return
        answer = QMessageBox.question(
            self,
            "Delete",
            f"Delete {len(paths)} selected item(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        failures = []
        for path in paths:
            try:
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")
        self.refresh()
        if failures:
            QMessageBox.warning(self, "Delete", "\n".join(failures))


def main():
    app = QApplication(sys.argv)
    raw = sys.argv[1] if len(sys.argv) > 1 else str(HOME)
    window = Window(pathlib.Path(raw))
    window.showMaximized()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
