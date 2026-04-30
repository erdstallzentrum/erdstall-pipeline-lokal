from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class AddProjectWindow(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Add New Project")
        self.resize(600,180)

        self.mesh_id_edit = QLineEdit()
        self.mesh_file_edit = QLineEdit()
        self.texture_dir_edit = QLineEdit()

        self.mesh_browse_button = QPushButton("Browse")
        self.texture_browse_button = QPushButton("Browse")

        self.cancel_button = QPushButton("Cancel")
        self.create_button = QPushButton("Create")

        self._build_ui()
        self._connect()


    def _build_ui(self)-> None:
        form = QFormLayout()

        mesh_row = QHBoxLayout()
        mesh_row.addWidget(self.mesh_file_edit)
        mesh_row.addWidget(self.mesh_browse_button)

        texture_row = QHBoxLayout()
        texture_row.addWidget(self.texture_dir_edit)
        texture_row.addWidget(self.texture_browse_button)

        form.addRow("Project name: ", self.mesh_id_edit)
        form.addRow("Mesh / point cloud file (.ply):", self._wrap(mesh_row))
        form.addRow("Texture folder:", self._wrap(texture_row))


        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.create_button)


        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addLayout(buttons)


    def _connect(self) -> None:
        self.mesh_browse_button.clicked.connect(self._browse_mesh)
        self.texture_browse_button.clicked.connect(self._browse_texture_dir)
        self.cancel_button.clicked.connect(self.reject)
        self.create_button.clicked.connect(self._validate_and_accept)


    def _wrap(self, layout: QHBoxLayout) -> QWidget:
        widget = QWidget()
        widget.setLayout(layout)
        return widget

    def _browse_mesh(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select mesh file",
            "",
            "PLY files (*.ply);;All files (*)"
        )
        if path:
            self.mesh_file_edit.setText(path)

    def _browse_texture_dir(self)-> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select texture folder",
            ""
        )
        if path:
            self.texture_dir_edit.setText(path)

    def _validate_and_accept(self) -> None:
        mesh_id = self.mesh_id.strip()
        mesh_file = self.mesh_file

        if not mesh_id:
            QMessageBox.warning(self, "Missing project name", "Please enter a project name.")
            return

        if not mesh_file:
            QMessageBox.warning(self, "Missing mesh file", "Please select a .ply file.")
            return

        if not mesh_file.exists() or not mesh_file.is_file():
            QMessageBox.warning(self, "Invalid mesh file", "Selected mesh file does not exist.")
            return

        self.accept()
    
    @property
    def mesh_id(self) -> str:
        return self.mesh_id_edit.text().strip()

    @property
    def mesh_file(self) -> Path:
        return Path(self.mesh_file_edit.text().strip()).expanduser()
    
    @property
    def texture_dir(self) -> str | None:
        value = self.texture_dir_edit.text().strip()
        return value or None




