#!/usr/bin/env python3
from __future__ import annotations
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import zipfile
from PyQt6.QtWidgets import (
    QApplication,QFileDialog,QHBoxLayout,QLabel,QMainWindow,QMessageBox,
    QPushButton,QTextEdit,QVBoxLayout,QWidget
)

HOME=pathlib.Path.home()
APPS=HOME/"Apps"
DESKTOP=HOME/"Desktop"
LOCAL_APPS=HOME/".local/share/applications"
BRIDGE="\0droiddesk.android-app-launcher"

def bridge(command):
    try:
        s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);s.connect(BRIDGE)
        s.sendall((command+"\n").encode());s.close();return True
    except Exception:return False

def desktop_entry(name,exec_cmd,terminal=False):
    safe="".join(c if c.isalnum() or c in "._-" else "_" for c in name)
    text=f"""[Desktop Entry]
Type=Application
Name={name}
Exec={exec_cmd}
Icon=applications-development
Terminal={'true' if terminal else 'false'}
Categories=Utility;Development;
"""
    LOCAL_APPS.mkdir(parents=True,exist_ok=True);DESKTOP.mkdir(parents=True,exist_ok=True)
    for path in [LOCAL_APPS/f"droiddesk-import-{safe}.desktop",DESKTOP/f"{safe}.desktop"]:
        path.write_text(text);path.chmod(0o755)

def copy_script(src:pathlib.Path):
    APPS.mkdir(parents=True,exist_ok=True)
    target=APPS/src.name;shutil.copy2(src,target);target.chmod(0o755)
    if target.suffix.lower()==".py":
        desktop_entry(target.stem,f"{sys.executable} {target}",False)
    else:
        desktop_entry(target.stem,str(target),True)
    return f"Imported {target.name}"

def safe_extract(z:pathlib.Path,dest:pathlib.Path):
    with zipfile.ZipFile(z) as archive:
        base=dest.resolve()
        for info in archive.infolist():
            out=(dest/info.filename).resolve()
            if base not in out.parents and out!=base:raise RuntimeError("Unsafe ZIP path")
        archive.extractall(dest)

def import_zip(src:pathlib.Path):
    APPS.mkdir(parents=True,exist_ok=True);dest=APPS/src.stem
    if dest.exists():shutil.rmtree(dest)
    dest.mkdir();safe_extract(src,dest)
    candidates=[dest/"main.py",dest/"app.py",dest/"run.py",dest/"run.sh",dest/"start.sh"]
    launch=next((p for p in candidates if p.exists()),None)
    if not launch:return f"Extracted to {dest}. No main.py/app.py/run.py/run.sh/start.sh was found."
    launch.chmod(0o755)
    cmd=f"{sys.executable} {launch}" if launch.suffix==".py" else str(launch)
    desktop_entry(src.stem,cmd,launch.suffix==".sh")
    return f"Imported {src.name}"

def import_folder(src:pathlib.Path):
    APPS.mkdir(parents=True,exist_ok=True);dest=APPS/src.name
    if dest.exists():shutil.rmtree(dest)
    shutil.copytree(src,dest)
    candidates=[dest/"main.py",dest/"app.py",dest/"run.py",dest/"run.sh",dest/"start.sh"]
    launch=next((p for p in candidates if p.exists()),None)
    if launch:
        launch.chmod(0o755)
        if launch.suffix == ".py":
            cmd = f"{sys.executable} {launch}"
        else:
            cmd = str(launch)
        desktop_entry(src.name, cmd, launch.suffix == ".sh")
    return f"Imported folder to {dest}"

class Window(QMainWindow):
    def __init__(self):
        super().__init__();self.setWindowTitle("DroidDesk Import Center");self.resize(800,540)
        w=QWidget();v=QVBoxLayout(w);self.setCentralWidget(w)
        v.addWidget(QLabel("Import Linux apps, scripts, source folders, ZIP projects, or hand APKs to Android."))
        row=QHBoxLayout();v.addLayout(row)
        for title,fn in [("Import File",self.file),("Import Folder",self.folder)]:
            b=QPushButton(title);b.clicked.connect(fn);row.addWidget(b)
        self.log=QTextEdit();self.log.setReadOnly(True);v.addWidget(self.log)
        v.addWidget(QLabel("Supported: .deb, .py, .sh, .zip, source folders, .apk. Windows .exe requires a separate Wine/Box64 layer and is not installed here."))

    def file(self):
        path,_=QFileDialog.getOpenFileName(self,"Import app","","All Files (*)")
        if path:self.handle(pathlib.Path(path))

    def folder(self):
        path=QFileDialog.getExistingDirectory(self,"Import source folder")
        if not path:return
        try:self.log.append(import_folder(pathlib.Path(path)))
        except Exception as e:self.log.append("Error: "+str(e))

    def handle(self,p:pathlib.Path):
        try:
            ext=p.suffix.lower()
            if ext==".deb":
                proc=subprocess.run(["apt-get","install","-y",str(p)],text=True,capture_output=True)
                self.log.append((proc.stdout+"\n"+proc.stderr)[-12000:])
            elif ext in {".py",".sh"}:self.log.append(copy_script(p))
            elif ext==".zip":self.log.append(import_zip(p))
            elif ext==".apk":
                if bridge("install-apk:"+str(p)):self.log.append("Android package installer opened.")
                else:self.log.append("Could not hand APK to Android. Check DroidDesk storage/install permissions.")
            elif ext==".exe":
                self.log.append("Windows .exe is not a native DroidDesk format. A Wine/Box64 compatibility layer is required.")
            else:self.log.append("Unsupported file type: "+ext)
        except Exception as e:self.log.append("Error: "+str(e))

def main():
    app=QApplication(sys.argv);w=Window();w.show();raise SystemExit(app.exec())
if __name__=="__main__":main()
