from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from erdstall_pipeline.config import (
    BACKUP_TEXTURE_DIR,
    FINAL_MESH,
    ORIGINAL_MESH,
    PATCHES_DIR,
    PATH_JSON_FILENAME,
    PATH_POINTS_FILENAME,
    PLY_DIR,
    REPAIRED_MESH,
    TEXTURE_DIR,
)


class HomePage(QWidget):
    fill_holes_requested = Signal()
    patch_detection_requested = Signal()
    path_points_requested = Signal()
    path_full_pipeline_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.current_mesh_id: str | None = None
        self.current_project_dir: Path | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        self.title_label = QLabel("Erdstall Admin")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: 700;")

        self.subtitle_label = QLabel("Project dashboard")
        self.subtitle_label.setStyleSheet("font-size: 14px; color: #aaaaaa;")

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)
        overview_box = QFrame()
        overview_box.setFrameShape(QFrame.StyledPanel)
        overview_layout = QVBoxLayout(overview_box)
        overview_layout.setContentsMargins(16, 16, 16, 16)
        overview_layout.setSpacing(12)

        overview_title = QLabel("Project Overview")
        overview_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        overview_layout.addWidget(overview_title)

        self.status_grid = QGridLayout()
        self.status_grid.setHorizontalSpacing(24)
        self.status_grid.setVerticalSpacing(9)
        overview_layout.addLayout(self.status_grid)

        self.status_labels: dict[str, QLabel] = {}
        self._add_status_row(0, "Original mesh")
        self._add_status_row(1, "Repaired mesh")
        self._add_status_row(2, "Final mesh")
        self._add_status_row(3, "Mobile mesh")
        self._add_status_row(4, "Patches folder")
        self._add_status_row(5, "Textures folder")
        self._add_status_row(6, "Texture backup")
        self._add_status_row(7, "Path JSON")
        self._add_status_row(8, "Path points CSV")

        main_layout.addWidget(overview_box)

        action_box = QFrame()
        action_box.setFrameShape(QFrame.StyledPanel)
        action_layout = QVBoxLayout(action_box)
        action_layout.setContentsMargins(16, 16, 16, 16)
        action_layout.setSpacing(12)

        action_title = QLabel("Quick Actions")
        action_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        action_layout.addWidget(action_title)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        self.fill_holes_button = QPushButton("Fill Holes")
        self.fill_holes_button.clicked.connect(self.fill_holes_requested.emit)

        self.detect_patches_button = QPushButton("Detect Patches")
        self.detect_patches_button.clicked.connect(self.patch_detection_requested.emit)

        self.path_points_button = QPushButton("Add Path Points CSV")
        self.path_points_button.clicked.connect(self.path_points_requested.emit)

        self.path_full_pipeline_button = QPushButton("Calculate Path")
        self.path_full_pipeline_button.clicked.connect(self.path_full_pipeline_requested.emit)
        
        self.open_project_folder_button = QPushButton("Open Project Folder")
        self.open_project_folder_button.clicked.connect(self.open_project_folder)

        self.refresh_button = QPushButton("Refresh Overview")
        self.refresh_button.clicked.connect(self.refresh_project_info)

        button_row.addWidget(self.fill_holes_button)
        button_row.addWidget(self.detect_patches_button)
        button_row.addWidget(self.path_points_button)
        button_row.addWidget(self.path_full_pipeline_button)
        button_row.addWidget(self.open_project_folder_button)
        button_row.addWidget(self.refresh_button)
        button_row.addStretch()

        action_layout.addLayout(button_row)
        main_layout.addWidget(action_box)
        main_layout.addStretch()

        self._set_buttons_enabled(False)
        self.fill_holes_button.setEnabled(False)
        self.detect_patches_button.setEnabled(False)
        self.path_points_button.setEnabled(False)
        self.path_full_pipeline_button.setEnabled(False)
        

    def _add_status_row(self, row: int, label_text: str) -> None:
        name_label = QLabel(label_text)
        value_label = QLabel("-")
        value_label.setStyleSheet("font-weight: 600; color: #aaaaaa;")

        self.status_grid.addWidget(name_label, row, 0)
        self.status_grid.addWidget(value_label, row, 1)

        self.status_labels[label_text] = value_label

    def _set_status(self, key: str, exists: bool) -> None:
        label = self.status_labels[key]
        if exists:
            label.setText("Available")
            label.setStyleSheet("font-weight: 600; color: #7bd88f;")
        else:
            label.setText("Missing")
            label.setStyleSheet("font-weight: 600; color: #ff7b72;")

    def _set_buttons_enabled(self, enabled: bool) -> None:
        self.open_project_folder_button.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)

    def set_project(self, mesh_id: str | None) -> None:
        self.current_mesh_id = mesh_id

        if not mesh_id:
            self.current_project_dir = None
            self.summary_label.setText("Select a project from the left sidebar.")
            for label in self.status_labels.values():
                label.setText("—")
                label.setStyleSheet("font-weight: 600; color: #aaaaaa;")
            self._set_buttons_enabled(False)
            self.fill_holes_button.setEnabled(False)
            self.detect_patches_button.setEnabled(False)
            self.path_points_button.setEnabled(False)
            self.path_full_pipeline_button.setEnabled(False)
            return

        self.current_project_dir = PLY_DIR / mesh_id
        self.refresh_project_info()

    def refresh_project_info(self) -> None:
        if not self.current_mesh_id or not self.current_project_dir:
            self.set_project(None)
            return

        project_dir = self.current_project_dir

        original_mesh = project_dir / ORIGINAL_MESH
        repaired_mesh = project_dir / REPAIRED_MESH
        final_mesh = project_dir / FINAL_MESH
        mobile_mesh = project_dir / "mesh_mobile.ply"
        patches_dir = project_dir / PATCHES_DIR
        textures_dir = project_dir / TEXTURE_DIR
        backup_dir = project_dir / BACKUP_TEXTURE_DIR
        path_json = project_dir / PATH_JSON_FILENAME
        path_points_csv = project_dir / PATH_POINTS_FILENAME

        original_exists = original_mesh.exists()
        repaired_exists = repaired_mesh.exists()
        path_points_exists = path_points_csv.exists()
        final_exists = final_mesh.exists()

        self._set_status("Original mesh", original_exists)
        self._set_status("Repaired mesh", repaired_exists)
        self._set_status("Final mesh", final_exists)
        self._set_status("Mobile mesh", mobile_mesh.exists())
        self._set_status("Patches folder", patches_dir.exists() and patches_dir.is_dir())
        self._set_status("Textures folder", textures_dir.exists() and textures_dir.is_dir())
        self._set_status("Texture backup", backup_dir.exists() and backup_dir.is_dir())
        self._set_status("Path JSON", path_json.exists())
        self._set_status("Path points CSV", path_points_exists)

        available_count = sum([
            original_exists,
            repaired_mesh.exists(),
            final_mesh.exists(),
            mobile_mesh.exists(),
            patches_dir.exists() and patches_dir.is_dir(),
            textures_dir.exists() and textures_dir.is_dir(),
            backup_dir.exists() and backup_dir.is_dir(),
            path_json.exists(),
            path_points_csv.exists(),
        ])

        self._set_buttons_enabled(True)
        self.fill_holes_button.setEnabled(original_exists)
        self.detect_patches_button.setEnabled(repaired_exists)
        self.path_points_button.setEnabled(True)
        self.path_full_pipeline_button.setEnabled(final_exists and path_points_exists)

    def open_project_folder(self) -> None:
        if not self.current_project_dir or not self.current_project_dir.exists():
            return

        import os
        os.startfile(self.current_project_dir)