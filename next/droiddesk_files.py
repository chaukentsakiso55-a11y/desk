#!/usr/bin/env python3
from __future__ import annotations
import os
import pathlib
import socket
import subprocess
import sys
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSplitter,
    QToolBar, QVBoxLayout, QWidget
)

BRIDGE = "\0droiddesk.android-app-launcher"
HOME = pathlib.Path.home()
PHONE = pathlib.Path("/storage/emulated/0")
TRASH = HOME / ".local/share/Trash/files"
VIDEO_EXT = {".mp4",".mkv",".avi",".mov",".webm",".m4v",".3gp",".mpeg",".mpg",".ts",".flv"}
AUDIO_EXT = {".mp3",".m4a",".aac",".flac",".wav",".ogg",".opus",".wma"}

def bridge(command: str) -> bool:
    try:
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.connect(BRIDGE)
        s.sendall((command+"\n").encode());s.close();return True
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
    value=str(path)
    if value.startswith("computer:") or value == "/" or value == "file:///":
        return HOME
    if value.startswith("trash:"):
        TRASH.mkdir(parents=True,exist_ok=True);return TRASH
    try:
        p=path.expanduser().resolve()
    except Exception:
        return HOME
    if str(p).startswith("/storage") and not readable(PHONE):
        bridge("storage:request");return HOME
    return p if p.exists() else HOME

class Window(QMainWindow):
    def __init__(self,start: pathlib.Path):
        super().__init__()
        self.setWindowTitle("DroidDesk Files")
        self.resize(1180,760)
        self.current=safe_start(start)
        self.history=[]
        self._build()
        self.open_dir(self.current, push=False)

    def _build(self):
        toolbar=QToolBar();self.addToolBar(toolbar)
        for label,fn in [("←",self.back),("↑",self.up),("⌂",lambda:self.open_dir(HOME)),("Phone",self.phone)]:
            b=QPushButton(label);b.clicked.connect(fn);toolbar.addWidget(b)
        self.path=QLabel();toolbar.addWidget(self.path)

        root=QWidget();layout=QHBoxLayout(root);split=QSplitter();layout.addWidget(split);self.setCentralWidget(root)
        self.side=QListWidget();self.side.setMaximumWidth(250)
        places=[
            ("Linux Home",HOME),("Desktop",HOME/"Desktop"),("Phone Storage",PHONE),
            ("Downloads",PHONE/"Download"),("Camera",PHONE/"DCIM/Camera"),("Pictures",PHONE/"Pictures"),
            ("Movies",PHONE/"Movies"),("Music",PHONE/"Music"),("Documents",PHONE/"Documents"),
        ]
        for name,path in places:
            item=QListWidgetItem(name);item.setData(Qt.ItemDataRole.UserRole,str(path));self.side.addItem(item)
        self.side.itemActivated.connect(lambda i:self.open_dir(pathlib.Path(i.data(Qt.ItemDataRole.UserRole))))
        split.addWidget(self.side)

        right=QWidget();rv=QVBoxLayout(right);self.list=QListWidget();rv.addWidget(self.list)
        self.list.itemActivated.connect(self.activate)
        split.addWidget(right);split.setStretchFactor(1,1)

    def phone(self):
        if not readable(PHONE):
            bridge("storage:request")
            QMessageBox.information(self,"Phone Storage","Android opened the all-files access screen. Grant DroidDesk access, then tap Phone again.")
            return
        self.open_dir(PHONE)

    def open_dir(self,path: pathlib.Path,push=True):
        path=safe_start(path)
        if not path.is_dir():
            return
        if push and self.current != path:self.history.append(self.current)
        self.current=path;self.path.setText(str(path));self.list.clear()
        try:
            entries=sorted(path.iterdir(),key=lambda p:(not p.is_dir(),p.name.lower()))
        except Exception as e:
            QMessageBox.warning(self,"Files",str(e));return
        for p in entries:
            item=QListWidgetItem(("📁 " if p.is_dir() else "📄 ")+p.name)
            item.setData(Qt.ItemDataRole.UserRole,str(p));self.list.addItem(item)

    def back(self):
        if self.history:self.open_dir(self.history.pop(),push=False)

    def up(self):
        parent=self.current.parent
        if str(parent) in ("/","/data","/storage") and self.current != PHONE:
            parent=HOME
        self.open_dir(parent)

    def activate(self,item):
        p=pathlib.Path(item.data(Qt.ItemDataRole.UserRole))
        if p.is_dir():self.open_dir(p);return
        ext=p.suffix.lower()
        try:
            if ext in VIDEO_EXT or ext in AUDIO_EXT:
                vlc=os.environ.get("PREFIX","/data/data/com.termux/files/usr")+"/bin/vlc"
                subprocess.Popen([vlc,str(p)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(["xdg-open",str(p)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except Exception as e:
            QMessageBox.warning(self,"Open file",str(e))

def main():
    app=QApplication(sys.argv)
    raw=sys.argv[1] if len(sys.argv)>1 else str(HOME)
    w=Window(pathlib.Path(raw));w.show()
    raise SystemExit(app.exec())

if __name__=="__main__":main()
