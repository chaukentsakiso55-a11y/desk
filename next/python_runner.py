#!/usr/bin/env python3
from __future__ import annotations
import pathlib
import sys
from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

HOME = pathlib.Path.home()
PHONE = pathlib.Path("/storage/emulated/0")


class Runner(QMainWindow):
    def __init__(self, initial: pathlib.Path | None = None):
        super().__init__()
        self.setWindowTitle("DroidDesk Python")
        self.resize(1100, 760)
        self.path: pathlib.Path | None = None
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read_stdout)
        self.process.readyReadStandardError.connect(self.read_stderr)
        self.process.finished.connect(self.finished)
        self._build()
        if initial and initial.exists():
            self.load(initial)

    def _build(self):
        root = QWidget()
        layout = QVBoxLayout(root)
        self.setCentralWidget(root)
        row = QHBoxLayout()
        for label, fn in [
            ("Open", self.open_file),
            ("Save", self.save),
            ("Save As", self.save_as),
            ("Run", self.run),
            ("Stop", self.stop),
        ]:
            button = QPushButton(label)
            button.clicked.connect(fn)
            row.addWidget(button)
        self.path_label = QLabel("New Python file")
        row.addWidget(self.path_label, 1)
        layout.addLayout(row)

        split = QSplitter()
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("print('Hello from DroidDesk')")
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        split.addWidget(self.editor)
        split.addWidget(self.output)
        split.setSizes([650, 350])
        layout.addWidget(split)

    def load(self, path: pathlib.Path):
        try:
            self.path = path
            self.editor.setPlainText(path.read_text(encoding="utf-8"))
            self.path_label.setText(str(path))
        except Exception as exc:
            QMessageBox.warning(self, "Open", str(exc))

    def open_file(self):
        start = PHONE if PHONE.exists() else HOME
        raw, _ = QFileDialog.getOpenFileName(self, "Open Python file", str(start), "Python (*.py);;All Files (*)")
        if raw:
            self.load(pathlib.Path(raw))

    def save(self) -> bool:
        if self.path is None:
            return self.save_as()
        try:
            self.path.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.path_label.setText(str(self.path))
            return True
        except Exception as exc:
            QMessageBox.warning(self, "Save", str(exc))
            return False

    def save_as(self) -> bool:
        start = PHONE / "Download" if (PHONE / "Download").exists() else HOME
        raw, _ = QFileDialog.getSaveFileName(self, "Save Python file", str(start / "script.py"), "Python (*.py)")
        if not raw:
            return False
        path = pathlib.Path(raw)
        if path.suffix.lower() != ".py":
            path = path.with_suffix(".py")
        self.path = path
        return self.save()

    def run(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        if not self.save():
            return
        assert self.path is not None
        self.output.clear()
        self.output.append(f"$ python3 {self.path}\n")
        self.process.setWorkingDirectory(str(self.path.parent))
        self.process.start(sys.executable, [str(self.path)])

    def stop(self):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.process.kill()

    def read_stdout(self):
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
        self.output.insertPlainText(bytes(self.process.readAllStandardOutput()).decode(errors="replace"))

    def read_stderr(self):
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
        self.output.insertPlainText(bytes(self.process.readAllStandardError()).decode(errors="replace"))

    def finished(self, code: int, _status):
        self.output.append(f"\nProcess finished with exit code {code}.")


def main():
    app = QApplication(sys.argv)
    initial = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else None
    window = Runner(initial)
    window.showMaximized()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
