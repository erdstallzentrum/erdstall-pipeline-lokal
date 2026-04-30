from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot


class ProjectInitWorker(QObject):
    finished = Signal()
    success = Signal(str)
    error = Signal(str)
    log = Signal(str)

    def __init__(self, mesh_id: str, mesh_file: str | Path, texture_dir: str | Path | None)-> None:
        super().__init__()
        self.mesh_id = mesh_id
        self.mesh_file = Path(mesh_file)
        self.texture_dir = Path(texture_dir) if texture_dir else None

    @Slot()
    def run(self)-> None:
        try:
            
            from erdstall_pipeline.pipeline import initialize_project, is_point_cloud_project

            self.log.emit(f"Creating project: {self.mesh_id}")
            self.log.emit(f"Input mesh: {self.mesh_file}")

            if self.texture_dir:
                self.log.emit(f"texture folder: {self.texture_dir}")
            else:
                self.log.emit("No texture folder selected.")

            base = initialize_project(
                mesh_id=self.mesh_id,
                input_mesh=self.mesh_file,
                textures_dir=self.texture_dir
            )

            if is_point_cloud_project(self.mesh_id):
                self.log.emit("Detected project type: point cloud")
            else:
                self.log.emit("Detected project type: mesh")

            self.success.emit(f"Project created successfully: {base}")

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()
