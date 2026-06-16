from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import MESH_MOBILE, MESH_GLB, MESH_MOBILE_GLB
from erdstall_pipeline.config import (
    FINAL_MESH,
    ORIGINAL_MESH,
    PATH_JSON_FILENAME,
    PATH_POINTS_FILENAME,
    PLY_DIR,
    REPAIRED_MESH,
     CONVERTED_MESH,
    XML_FILENAME
)

from erdstall_admin_gui.widgets.flow_layout import FlowLayout

class HomePage(QWidget):
    fill_holes_requested = Signal()
    path_points_requested = Signal()
    path_full_pipeline_requested = Signal()
    point_cloud_to_mesh_requested = Signal()

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

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)
        overview_box = QFrame()
        overview_box.setFrameShape(QFrame.Shape.StyledPanel)
        overview_layout = QVBoxLayout(overview_box)
        overview_layout.setContentsMargins(16, 16, 16, 16)
        overview_layout.setSpacing(12)

        overview_title = QLabel("Project Overview")
        overview_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        overview_layout.addWidget(overview_title)

        self.status_grid = QGridLayout()
        self.status_grid.setHorizontalSpacing(24)
        self.status_grid.setVerticalSpacing(10)
        overview_layout.addLayout(self.status_grid)

        self.status_labels: dict[str, QLabel] = {}
        self._add_status_row(0, "Original mesh")
        self._add_status_row(1, "Converted mesh")
        self._add_status_row(2, "Final mesh")
        self._add_status_row(3, "Mobile mesh")
        self._add_status_row(4, "Glb")
        self._add_status_row(5, "Glb mobile")
        self._add_status_row(6, "Path JSON")
        self._add_status_row(7, "Path points CSV")
        self._add_status_row(8, "XML metadata")

        main_layout.addWidget(overview_box)

        action_box = QFrame()
        action_box.setFrameShape(QFrame.Shape.StyledPanel)
        action_layout = QVBoxLayout(action_box)
        action_layout.setContentsMargins(16, 16, 16, 16)
        action_layout.setSpacing(12)

        action_title = QLabel("Actions")
        action_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        action_layout.addWidget(action_title)

        button_row = FlowLayout(spacing=12)

        self.convert_point_cloud_button = QPushButton("Convert Point Cloud to Mesh")
        self.convert_point_cloud_button.clicked.connect(
            self.point_cloud_to_mesh_requested.emit
        )

        self.fill_holes_button = QPushButton("Fill Holes")
        self.fill_holes_button.clicked.connect(self.fill_holes_requested.emit)

        self.path_points_button = QPushButton("Add Path Points")
        self.path_points_button.clicked.connect(self.path_points_requested.emit)

        self.path_full_pipeline_button = QPushButton("Calculate Path")
        self.path_full_pipeline_button.clicked.connect(self.path_full_pipeline_requested.emit)
        
        self.open_project_folder_button = QPushButton("Open Project Folder")
        self.open_project_folder_button.clicked.connect(self.open_project_folder)

        self.refresh_button = QPushButton("Refresh Overview")
        self.refresh_button.clicked.connect(self.refresh_project_info)

        button_row.addWidget(self.convert_point_cloud_button)
        button_row.addWidget(self.fill_holes_button)
        button_row.addWidget(self.path_points_button)
        button_row.addWidget(self.path_full_pipeline_button)
        button_row.addWidget(self.open_project_folder_button)
        button_row.addWidget(self.refresh_button)

        action_layout.addLayout(button_row)
        main_layout.addWidget(action_box)
        main_layout.addStretch()

        self._set_buttons_enabled(False)
        self.fill_holes_button.setEnabled(False)
        self.path_points_button.setEnabled(False)
        self.path_full_pipeline_button.setEnabled(False)
        self.convert_point_cloud_button.setEnabled(False)
        self.convert_point_cloud_button.setVisible(False)
        

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
            for label in self.status_labels.values():
                label.setText("—")
                label.setStyleSheet("font-weight: 600; color: #aaaaaa;")
            self._set_buttons_enabled(False)
            self.fill_holes_button.setEnabled(False)
            self.path_points_button.setEnabled(False)
            self.path_full_pipeline_button.setEnabled(False)
            self.convert_point_cloud_button.setEnabled(False)
            self.convert_point_cloud_button.setVisible(False)
            return

        self.current_project_dir = Path(PLY_DIR) / mesh_id
        self.refresh_project_info()

    def refresh_project_info(self) -> None:

        from erdstall_pipeline.pipeline import is_point_cloud_project

        if not self.current_mesh_id or not self.current_project_dir:
            self.set_project(None)
            return



        project_dir = self.current_project_dir

        original_mesh = project_dir / ORIGINAL_MESH
        converted_mesh = project_dir / CONVERTED_MESH
        repaired_mesh = project_dir / REPAIRED_MESH
        final_mesh = project_dir / FINAL_MESH
        mobile_mesh = project_dir / MESH_MOBILE
        glb = project_dir / MESH_GLB
        glb_mobile = project_dir / MESH_MOBILE_GLB
        path_json = project_dir / PATH_JSON_FILENAME
        path_points_csv = project_dir / PATH_POINTS_FILENAME
        xml_metadata = project_dir / XML_FILENAME

        original_exists = original_mesh.exists()
        converted_exists = converted_mesh.exists()
        path_points_exists = path_points_csv.exists()
        final_exists = final_mesh.exists()

        self._set_status("Original mesh", original_exists)
        is_point_cloud = is_point_cloud_project(self.current_mesh_id)

        item = self.status_grid.itemAtPosition(1,0)

        if item is not None:
            converted_name_label = item.widget()
            converted_value_label = self.status_labels["Converted mesh"]
            if converted_name_label is not None:
                converted_name_label.setVisible(is_point_cloud)
                converted_value_label.setVisible(is_point_cloud)

        if is_point_cloud:
            self._set_status("Converted mesh", converted_exists)
        self._set_status("Final mesh", final_exists)
        self._set_status("Mobile mesh", mobile_mesh.exists())
        self._set_status("Glb", glb.exists() and glb.is_file())
        self._set_status("Glb mobile", glb_mobile.exists() and glb_mobile.is_file())
        self._set_status("Path JSON", path_json.exists())
        self._set_status("Path points CSV", path_points_exists)
        self._set_status("XML metadata", xml_metadata.exists() and xml_metadata.is_file())


        self._set_buttons_enabled(True)
        self.convert_point_cloud_button.setVisible(is_point_cloud)
        self.convert_point_cloud_button.setEnabled(is_point_cloud and original_exists)

        if is_point_cloud:
            self.fill_holes_button.setEnabled(converted_exists)
        else:
            self.fill_holes_button.setEnabled(original_exists)

        self.path_points_button.setEnabled(True)
        self.path_full_pipeline_button.setEnabled(final_exists and path_points_exists)

    def open_project_folder(self) -> None:
        if not self.current_project_dir or not self.current_project_dir.exists():
            return

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self.current_project_dir))
        )