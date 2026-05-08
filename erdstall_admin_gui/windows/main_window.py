from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMainWindow, QStackedWidget
from erdstall_admin_gui.windows.home_page import HomePage
from erdstall_admin_gui.windows.texture_window import TextureWindow
from erdstall_admin_gui.windows.setup_window import SetupWindow
from erdstall_admin_gui.windows.add_project_window import AddProjectWindow
from erdstall_admin_gui.workers.init_worker import ProjectInitWorker
from PySide6.QtCore import Qt,QThread
from erdstall_admin_gui.windows.task_log_window import TaskLogWindow
from erdstall_admin_gui.workers.patch_detection_worker import PatchDetectionWorker
from erdstall_admin_gui.windows.add_path_points_window import AddPathPointsWindow
from erdstall_admin_gui.workers.path_points_worker import PathPointsWorker
from erdstall_admin_gui.windows.fill_holes_window import FillHolesWindow
from erdstall_admin_gui.workers.fill_holes_worker import FillHolesWorker
from erdstall_admin_gui.workers.path_full_pipeline import PathFullPipelineWorker
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QSizePolicy,
    QMessageBox,
    QStyle
)

from erdstall_admin_gui.workers.point_cloud_to_mesh_worker import PointCloudToMeshWorker
from erdstall_pipeline.config import PLY_DIR, FINAL_MESH
from erdstall_admin_gui.widgets.project_list_item_widget import ProjectListItemWidget
import shutil
from erdstall_admin_gui.workers.ply_to_glb_worker import PlyToGlbWorker
from erdstall_admin_gui.windows.point_cloud_to_mesh_window import PointCloudToMeshWindow
from erdstall_admin_gui.windows.glb_export_window import GlbExportWindow

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.current_mesh_id: str | None = None
        self._init_thread: QThread | None  = None
        self._init_worker: ProjectInitWorker | None = None
        self._task_log_window: TaskLogWindow | None = None
        self._patch_thread: QThread | None = None
        self._patch_worker: PatchDetectionWorker | None = None

        self._fill_thread: QThread | None = None
        self._fill_worker: FillHolesWorker | None = None

        self._path_points_thread: QThread | None = None
        self._path_points_worker: PathPointsWorker | None = None

        self._full_pipeline_thread: QThread | None = None
        self._full_pipeline_worker: PathFullPipelineWorker | None = None

        self._glb_thread: QThread | None = None
        self._glb_worker: PlyToGlbWorker | None = None

        self._point_cloud_thread: QThread | None = None
        self._point_cloud_worker: PointCloudToMeshWorker | None = None

        self.setWindowTitle("Erdstall Admin")
        self.resize(1000, 700)

        self.stack = QStackedWidget()

        self.project_list = QListWidget()

        self.add_project_button = QPushButton("Add New")
        self.add_project_button.clicked.connect(self.open_add_project_window)

        self.refresh_projects_button = QPushButton("Refresh")
        self.refresh_projects_button.clicked.connect(self.load_projects)

        self.current_project_label = QLabel("Current project: None")

        projects_header = QHBoxLayout()
        projects_header.addWidget(QLabel("Projects"))
        projects_header.addStretch()
        projects_header.addWidget(self.add_project_button)

        left_layout = QVBoxLayout()
        left_layout.addLayout(projects_header)
        left_layout.addWidget(self.project_list)
        left_layout.addWidget(self.refresh_projects_button)
        left_layout.addWidget(self.current_project_label)

        left_widget = QWidget()
        left_widget.setLayout(left_layout)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(self.stack)

        main_layout = QHBoxLayout()
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 4)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        self.home_page = HomePage()
        self.texture_page = TextureWindow()
        self.setup_page = SetupWindow()

        self.home_page.fill_holes_requested.connect(self.open_fill_holes_window)
        self.home_page.patch_detection_requested.connect(self.start_patch_detection)
        self.home_page.path_points_requested.connect(self.open_path_points_window)
        self.home_page.path_full_pipeline_requested.connect(self.start_full_pipeline)
        self.home_page.point_cloud_to_mesh_requested.connect(
            self.start_point_cloud_to_mesh
        )
        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.texture_page)
        self.stack.addWidget(self.setup_page)

        self.stack.setCurrentWidget(self.home_page)

        self._build_toolbar()
        self.load_projects()

    def _build_toolbar(self) -> None:
        toolbar = self.addToolBar("Navigation")
        toolbar.setMovable(False)

        home_action = QAction("Home", self)
        home_action.triggered.connect(lambda: self.stack.setCurrentWidget(self.home_page))
        toolbar.addAction(home_action)

        texture_action = QAction("Texture Changes", self)
        texture_action.triggered.connect(lambda: self.stack.setCurrentWidget(self.texture_page))
        toolbar.addAction(texture_action)

        glb_action = QAction("Convert GLB", self)
        glb_action.triggered.connect(self.start_ply_to_glb)
        toolbar.addAction(glb_action)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)


        setup_action = QAction("Setup", self)
        setup_action.triggered.connect(lambda: self.stack.setCurrentWidget(self.setup_page) )
        toolbar.addAction(setup_action)

    def load_projects(self) -> None:
        self.project_list.clear()

        projects_dir = Path(PLY_DIR)
        projects_dir.mkdir(parents=True, exist_ok=True)
        for path in sorted(projects_dir.iterdir()):
            if not path.is_dir():
                continue
            item = QListWidgetItem(self.project_list)
            widget = ProjectListItemWidget(path.name)

            trash_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
            widget.delete_button.setIcon(trash_icon)

            widget.selected.connect(self._select_project_by_name)
            widget.delete_requested.connect(self.delete_project)

            item.setSizeHint(widget.sizeHint())
            self.project_list.addItem(item)
            self.project_list.setItemWidget(item, widget)


    def _select_project_by_name(self, project_name: str) -> None:
        self.current_mesh_id = project_name
        self.current_project_label.setText(f"Current project: {self.current_mesh_id}")
        self.home_page.set_project(self.current_mesh_id)

    def delete_project(self, project_name: str) -> None:
        reply = QMessageBox.question(
            self,
            "Delete Project",
            f"Are you sure you want to delete this project: '{project_name}'",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        project_path = Path(PLY_DIR) / project_name

        if not project_path.exists():
            QMessageBox.warning(self, "Not Found", f"Project folder '{project_name}' was not found.")
            self.load_projects()
            return

        try:
            shutil.rmtree(project_path)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Deletion failed",
                f"Could not delete project folder '{project_name}' due to {e}"
            )
            return

        if self.current_mesh_id == project_name:
            self.current_mesh_id = None
            self.home_page.set_project(None)
            self.current_project_label.setText("Current project: None")

        self.load_projects()

    def get_current_mesh_id(self) -> str | None:
        return self.current_mesh_id
    
    def open_add_project_window(self)-> None:
        window = AddProjectWindow(self)

        if window.exec() != AddProjectWindow.Accepted:
            return
        
        self._start_project_init(
            mesh_id=window.mesh_id,
            mesh_file=window.mesh_file,
            texture_dir=window.texture_dir
        )
    def _start_project_init(
            self,
            mesh_id: str,
            mesh_file: str | Path,
            texture_dir: str| Path | None
    ) ->None:
        if self._init_thread is not None:
            QMessageBox.information(self, "Busy", "A project is already being created")
            return
        
        self._init_thread = QThread()
        self._init_worker = ProjectInitWorker(mesh_id, mesh_file, texture_dir)

        self._init_worker.moveToThread(self._init_thread)

        self._init_thread.started.connect(self._init_worker.run)
        self._init_worker.success.connect(self._on_project_init_success)
        self._init_worker.error.connect(self._on_project_init_error)
        self._init_worker.finished.connect(self._init_thread.quit)
        self._init_worker.finished.connect(self._init_worker.deleteLater)
        self._init_thread.finished.connect(self._init_thread.deleteLater)
        self._init_thread.finished.connect(self._on_project_init_finished)

        self.add_project_button.setDisabled(True)
        self.refresh_projects_button.setDisabled(True)

        self._init_thread.start()

    def _on_project_init_success(self, message: str) -> None:
        self.load_projects()

        if self._init_worker is not None:
            mesh_id = self._init_worker.mesh_id
            items = self.project_list.findItems(mesh_id, Qt.MatchFlag.MatchExactly)
            if items:
                self.project_list.setCurrentItem(items[0])
                self.on_project_selected(items[0])


    def _on_project_init_error(self, message: str) -> None:
        QMessageBox.critical(self, "Project creation failed", message)

    def _on_project_init_finished(self)-> None:
        self._init_thread = None
        self._init_worker = None
        self.add_project_button.setDisabled(False)
        self.refresh_projects_button.setDisabled(False)

    def open_fill_holes_window(self) -> None:
        if not self.current_mesh_id:
            QMessageBox.warning(self, "No project selected", "Please select a project first.")
            return

        dialog = FillHolesWindow(self)
        if not dialog.exec():
            return

        settings = dialog.get_settings()
        self._start_fill_holes(settings)
    
    def _start_fill_holes(self, settings) -> None:
        if not self.current_mesh_id:
            QMessageBox.warning(self, "No project selected", "Please select a project first.")
            return

        if self._fill_thread is not None:
            QMessageBox.information(self, "Busy", "Fill holes is already running.")
            return

        self._task_log_window = TaskLogWindow(
            f"Fill Holes - {self.current_mesh_id}",
            self,
        )
        self._task_log_window.set_running("Running Fill Holes...")

        self._fill_thread = QThread()
        self._fill_worker = FillHolesWorker(self.current_mesh_id, settings)

        self._fill_worker.moveToThread(self._fill_thread)

        self._fill_thread.started.connect(self._fill_worker.run)
        self._fill_worker.log.connect(self._task_log_window.append_log)
        self._fill_worker.success.connect(self._on_fill_holes_success)
        self._fill_worker.error.connect(self._on_fill_holes_error)
        self._fill_worker.finished.connect(self._fill_thread.quit)
        self._fill_worker.finished.connect(self._fill_worker.deleteLater)
        self._fill_thread.finished.connect(self._fill_thread.deleteLater)
        self._fill_thread.finished.connect(self._on_fill_holes_finished)

        self._fill_thread.start()
        self._task_log_window.show()

    def _on_fill_holes_success(self, message: str) -> None:
        if self._task_log_window is not None:
            self._task_log_window.append_log(f"[SUCCESS] {message}")
            self._task_log_window.set_success("Fill Holes completed.")
            self._task_log_window.accept()

        self.home_page.refresh_project_info()
        QMessageBox.information(self, "Fill Holes", message)

    def _on_fill_holes_error(self, message: str) -> None:
        if self._task_log_window is not None:
            self._task_log_window.append_log(f"[ERROR] {message}")
            self._task_log_window.set_error("Fill Holes failed.")

        QMessageBox.critical(self, "Fill Holes failed", message)

    def _on_fill_holes_finished(self) -> None:
        self._fill_thread = None
        self._fill_worker = None
    
    def start_patch_detection(self) -> None:
        if not self.current_mesh_id:
            QMessageBox.warning(self, "No project selected", "Please select a project first.")
            return

        if self._patch_thread is not None:
            QMessageBox.information(self, "Busy", "Patch detection is already running.")
            return

        self._task_log_window = TaskLogWindow(
            f"Patch Detection - {self.current_mesh_id}",
            self,
        )
        self._task_log_window.set_running("Running patch detection...")
        self._patch_thread = QThread()
        self._patch_worker = PatchDetectionWorker(self.current_mesh_id)
        self._patch_worker.moveToThread(self._patch_thread)

        self._patch_thread.started.connect(self._patch_worker.run)
        self._patch_worker.log.connect(self._task_log_window.append_log)
        self._patch_worker.success.connect(self._on_patch_detection_success)
        self._patch_worker.error.connect(self._on_patch_detection_error)
        self._patch_worker.finished.connect(self._patch_thread.quit)
        self._patch_worker.finished.connect(self._patch_worker.deleteLater)
        self._patch_thread.finished.connect(self._patch_thread.deleteLater)
        self._patch_thread.finished.connect(self._on_patch_detection_finished)

        self._patch_thread.start()
        self._task_log_window.show()
    
    def _on_patch_detection_success(self, message: str) -> None:
        if self._task_log_window is not None:
            self._task_log_window.append_log(f"[SUCCESS] {message}")
            self._task_log_window.set_success("Patch detection completed.")
            self._task_log_window.accept()

        self.home_page.refresh_project_info()
        QMessageBox.information(self, "Patch Detection", message)

    def _on_patch_detection_error(self, message: str) -> None:
        if self._task_log_window is not None:
            self._task_log_window.append_log(f"[ERROR] {message}")
            self._task_log_window.set_error("Patch detection failed.")

        QMessageBox.critical(self, "Patch detection failed", message)

    def _on_patch_detection_finished(self) -> None:
        self._patch_thread = None
        self._patch_worker = None
        self._task_log_window = None

    def open_path_points_window(self) -> None:
        if not self.current_mesh_id:
            QMessageBox.warning(self, "No project selected", "Please select a project first.")
            return

        dialog = AddPathPointsWindow(self)
        if not dialog.exec():
            return

        values = dialog.get_values()
        self._start_path_points(values)
    
    def _start_path_points(self, values: list[float]) -> None:
        if not self.current_mesh_id:
            QMessageBox.warning(self, "No project selected", "Please select a project first.")
            return

        if self._path_points_thread is not None:
            QMessageBox.information(self, "Busy", "Path points creation is already running.")
            return

        self._path_points_thread = QThread()
        self._path_points_worker = PathPointsWorker(self.current_mesh_id, values)

        self._path_points_worker.moveToThread(self._path_points_thread)

        self._path_points_thread.started.connect(self._path_points_worker.run)
        self._path_points_worker.success.connect(self._on_path_points_success)
        self._path_points_worker.error.connect(self._on_path_points_error)
        self._path_points_worker.finished.connect(self._path_points_thread.quit)
        self._path_points_worker.finished.connect(self._path_points_worker.deleteLater)
        self._path_points_thread.finished.connect(self._path_points_thread.deleteLater)
        self._path_points_thread.finished.connect(self._on_path_points_finished)

        self._path_points_thread.start()
    
    def _on_path_points_success(self, message: str) -> None:
        self.home_page.refresh_project_info()
        QMessageBox.information(self, "Path Points", message)

    def _on_path_points_error(self, message: str) -> None:
        QMessageBox.critical(self, "Path Points failed", message)
    def _on_path_points_finished(self) -> None:
        self._path_points_thread = None
        self._path_points_worker = None

    def start_full_pipeline(self) -> None:
        if not self.current_mesh_id:
            QMessageBox.warning(self, "No project selected", "Please select a project first.")
            return

        if self._full_pipeline_thread is not None:
            QMessageBox.information(self, "Busy", "Full pipeline is already running.")
            return

        self._task_log_window = TaskLogWindow(
            f"Full Pipeline - {self.current_mesh_id}",
            self,
        )
        self._task_log_window.set_running("Running path full pipeline...")
        

        self._full_pipeline_thread = QThread()
        self._full_pipeline_worker = PathFullPipelineWorker(self.current_mesh_id)
        self._full_pipeline_worker.moveToThread(self._full_pipeline_thread)

        self._full_pipeline_thread.started.connect(self._full_pipeline_worker.run)
        self._full_pipeline_worker.log.connect(self._task_log_window.append_log)
        self._full_pipeline_worker.success.connect(self._on_full_pipeline_success)
        self._full_pipeline_worker.error.connect(self._on_full_pipeline_error)
        self._full_pipeline_worker.finished.connect(self._full_pipeline_thread.quit)
        self._full_pipeline_worker.finished.connect(self._full_pipeline_worker.deleteLater)
        self._full_pipeline_thread.finished.connect(self._full_pipeline_thread.deleteLater)
        self._full_pipeline_thread.finished.connect(self._on_full_pipeline_finished)

        self._full_pipeline_thread.start()
        self._task_log_window.show()

    def _on_full_pipeline_success(self, message: str) -> None:
        if self._task_log_window is not None:
            self._task_log_window.append_log(f"[SUCCESS] {message}")
            self._task_log_window.set_success("Full path pipeline completed.")
            self._task_log_window.accept()

        self.home_page.refresh_project_info()
        QMessageBox.information(self, "Full path Pipeline", message)

    def _on_full_pipeline_error(self, message: str) -> None:
        if self._task_log_window is not None:
            self._task_log_window.append_log(f"[ERROR] {message}")
            self._task_log_window.set_error("Full path pipeline failed.")

        QMessageBox.critical(self, "Full path Pipeline failed", message)

    def _on_full_pipeline_finished(self) -> None:
        self._full_pipeline_thread = None
        self._full_pipeline_worker = None
        self._task_log_window = None

    def start_ply_to_glb(self) -> None:
        if not self.current_mesh_id:
            QMessageBox.warning(self, "No project selected", "Please select a project first.")
            return

        if self._glb_thread is not None:
            QMessageBox.information(self, "Busy", "GLB export is already running.")
            return

        mesh_path = Path(PLY_DIR) / self.current_mesh_id / FINAL_MESH

        if not mesh_path.exists():
            QMessageBox.warning(
                self,
                "Missing mesh.ply",
                "mesh.ply does not exist yet.\n\nYou need to run Fill Holes before converting to GLB.",
            )
            return

        dialog = GlbExportWindow(self)
        if not dialog.exec():
            return

        settings = dialog.get_settings()

        reply = QMessageBox.question(
            self,
            "Convert PLY to GLB",
            f"Are you sure you want to convert this PLY: '{self.current_mesh_id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self._task_log_window = TaskLogWindow(
            f"Export GLB - {self.current_mesh_id}",
            self,
        )

        self._task_log_window.set_running("Exporting PLY to GLB...")

        self._glb_thread = QThread()
        self._glb_worker = PlyToGlbWorker(
            self.current_mesh_id,
            settings=settings,
        )

        self._glb_worker.moveToThread(self._glb_thread)

        self._glb_thread.started.connect(self._glb_worker.run)
        self._glb_worker.log.connect(self._task_log_window.append_log)
        self._glb_worker.success.connect(self._on_glb_success)
        self._glb_worker.error.connect(self._on_glb_error)
        self._glb_worker.finished.connect(self._glb_thread.quit)
        self._glb_worker.finished.connect(self._glb_worker.deleteLater)
        self._glb_thread.finished.connect(self._glb_thread.deleteLater)
        self._glb_thread.finished.connect(self._on_glb_finished)

        self._glb_thread.start()
        self._task_log_window.show()

    def _on_glb_success(self, message: str) -> None:
        if self._task_log_window is not None:
            self._task_log_window.append_log(f"[SUCCESS] {message}")
            self._task_log_window.set_success("Export GLB completed.")
            self._task_log_window.accept()

        self.home_page.refresh_project_info()
        QMessageBox.information(self, "Export GLB", message)

    def _on_glb_error(self, message: str) -> None:
        if self._task_log_window is not None:
            self._task_log_window.append_log(f"[ERROR] {message}")
            self._task_log_window.set_error("Export GLB failed.")
        QMessageBox.critical(self, "Export GLB", message)

    def _on_glb_finished(self) -> None:
        self._glb_thread = None
        self._glb_worker = None
        self._task_log_window = None

    def start_point_cloud_to_mesh(self) -> None:
        if not self.current_mesh_id:
            QMessageBox.warning(self, "No project selected", "Please select a project first.")
            return

        if self._point_cloud_thread is not None:
            QMessageBox.information(
                self,
                "Busy",
                "Point cloud conversion is already running.",
            )
            return

        dialog = PointCloudToMeshWindow(self)
        if not dialog.exec():
            return

        settings = dialog.get_settings()

        reply = QMessageBox.question(
            self,
            "Convert Point Cloud to Mesh",
            f"Convert point cloud for project '{self.current_mesh_id}' to mesh?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self._task_log_window = TaskLogWindow(
            f"Point Cloud to Mesh - {self.current_mesh_id}",
            self,
        )
        self._task_log_window.set_running("Converting point cloud to mesh...")

        self._point_cloud_thread = QThread()
        self._point_cloud_worker = PointCloudToMeshWorker(
            self.current_mesh_id,
            settings=settings,
        )

        self._point_cloud_worker.moveToThread(self._point_cloud_thread)

        self._point_cloud_thread.started.connect(self._point_cloud_worker.run)
        self._point_cloud_worker.log.connect(self._task_log_window.append_log)
        self._point_cloud_worker.success.connect(self._on_point_cloud_to_mesh_success)
        self._point_cloud_worker.error.connect(self._on_point_cloud_to_mesh_error)
        self._point_cloud_worker.finished.connect(self._point_cloud_thread.quit)
        self._point_cloud_worker.finished.connect(self._point_cloud_worker.deleteLater)
        self._point_cloud_thread.finished.connect(self._point_cloud_thread.deleteLater)
        self._point_cloud_thread.finished.connect(self._on_point_cloud_to_mesh_finished)

        self._point_cloud_thread.start()
        self._task_log_window.show()

    def _on_point_cloud_to_mesh_success(self, message: str) -> None:
        if self._task_log_window is not None:
            self._task_log_window.append_log(f"[SUCCESS] {message}")
            self._task_log_window.set_success("Point cloud conversion completed.")
            self._task_log_window.accept()

        self.home_page.refresh_project_info()
        QMessageBox.information(self, "Point Cloud to Mesh", message)

    def _on_point_cloud_to_mesh_error(self, message: str) -> None:
        if self._task_log_window is not None:
            self._task_log_window.append_log(f"[ERROR] {message}")
            self._task_log_window.set_error("Point cloud conversion failed.")

        QMessageBox.critical(self, "Point Cloud to Mesh failed", message)

    def _on_point_cloud_to_mesh_finished(self) -> None:
        self._point_cloud_thread = None
        self._point_cloud_worker = None
        self._task_log_window = None