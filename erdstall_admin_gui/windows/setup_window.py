
from __future__ import annotations

import sys
from pathlib import Path

from erdstall_pipeline.settings.app_settings import AppSettings
from erdstall_admin_gui.workers.setup_worker import SetupWorker

from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class SetupWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self._thread: QThread | None = None
        self._worker: SetupWorker | None = None

        self.fiji_path_edit = QLineEdit()
        self.browse_button = QPushButton("Browse")
        self.save_button = QPushButton("Save")
        self.validate_button = QPushButton("Validate setup")
        self.clear_button = QPushButton("Clear log")
        self.download_fiji_button = QPushButton("Download Fiji")

        self.status_label = QLabel("Ready")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)

        self._build_ui()
        self._connect()
        self._load_settings()


    def _build_ui(self) -> None:
        grid = QGridLayout()
        grid.addWidget(QLabel("Fiji executable:"), 0, 0)
        grid.addWidget(self.fiji_path_edit, 0, 1)
        grid.addWidget(self.browse_button, 0, 2)

        buttons = QHBoxLayout()
        buttons.addWidget(self.download_fiji_button)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.validate_button)
        buttons.addWidget(self.clear_button)

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_output)

    def _connect(self) -> None:
        self.browse_button.clicked.connect(self._browse)
        self.download_fiji_button.clicked.connect(self._download_fiji)
        self.save_button.clicked.connect(self._save)
        self.validate_button.clicked.connect(self._validate)
        self.clear_button.clicked.connect(self.log_output.clear)

    def _load_settings(self) -> None:
        path = AppSettings.get_fiji_exe()
        if path:
            self.fiji_path_edit.setText(str(path))

    def _browse(self) -> None:
        if sys.platform == "darwin":
            dialog = QFileDialog(self, "Select Fiji.app folder")
            dialog.setDirectory("/Applications")
            dialog.setFileMode(QFileDialog.FileMode.Directory)
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
            dialog.setOption(QFileDialog.Option.ShowDirsOnly, False)

            if dialog.exec():
                selected = dialog.selectedFiles()
                if selected:
                    self.fiji_path_edit.setText(selected[0])

        elif sys.platform.startswith("win"):
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Fiji executable",
                "",
                "Fiji executable (*.exe);;All files (*)",
            )

            if path:
                self.fiji_path_edit.setText(path)

        else:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Fiji executable",
                "",
                "Executable (*) ; All files (*)",
            )

            if path:
                self.fiji_path_edit.setText(path)

    def _download_fiji(self)-> None:
        url = QUrl("https://imagej.net/software/fiji/downloads")
        QDesktopServices.openUrl(url)
        self._log("Opened Fiji download page in browser.")

    def _save(self) -> None:
        path_text = self.fiji_path_edit.text().strip()

        if not path_text:
            self._log("No path selected")
            return

        selected_path = Path(path_text).expanduser()

        try:
            resolved_path = SetupWorker.resolve_fiji_executable(selected_path)
        except Exception as e:
            self._log(f"[ERROR] Could not resolve Fiji path: {e}")
            self.status_label.setText("Failed")
            return

        AppSettings.set_fiji_exe(resolved_path)

        self.fiji_path_edit.setText(str(resolved_path))
        self._log(f"Saved Fiji executable: {resolved_path}")
        self.status_label.setText("Saved")


    def _validate(self) -> None:
        if self._thread:
            return
        
        self._set_busy(True)
        self.status_label.setText("Running...")

        thread = QThread()
        worker = SetupWorker()

        self._thread = thread
        self._worker = worker

        worker.moveToThread(thread)


        thread.started.connect(worker.run)
        worker.log.connect(self._log)
        worker.success.connect(self._success)
        worker.error.connect(self._error)

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._done)

        thread.start()

    def _success(self, msg: str) -> None:
        self._log(f" [SUCCESS] {msg}")
        self.status_label.setText(msg)

    def _error(self, msg: str) -> None:
        self._log(f"[ERROR] {msg}")
        self.status_label.setText("Failed")

    def _done(self) -> None:
        self._thread = None
        self._worker = None
        self._set_busy(False)

    def _log(self, text: str) -> None:
        self.log_output.append(text)

    def _set_busy(self, busy: bool) -> None:
        self.browse_button.setDisabled(busy)
        self.save_button.setDisabled(busy)
        self.validate_button.setDisabled(busy)