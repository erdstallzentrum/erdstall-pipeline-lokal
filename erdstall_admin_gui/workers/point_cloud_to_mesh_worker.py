from __future__ import annotations

from pathlib import Path

import open3d as o3d
from PySide6.QtCore import QObject, Signal, Slot

from erdstall_pipeline.config import ORIGINAL_MESH, PLY_DIR, REPAIRED_MESH, CONVERTED_MESH
from erdstall_pipeline.convert_point_cloud import point_cloud_to_mesh
from erdstall_pipeline.settings.point_cloud_settings import PointCloudSettings

class PointCloudToMeshWorker(QObject):
    finished = Signal()
    error = Signal(str)
    log = Signal(str)
    success = Signal(str)

    def __init__(self,
                 mesh_id: str,
                 settings: PointCloudSettings | None = None,) -> None:
        super().__init__()
        self.mesh_id = mesh_id
        self.settings = settings or PointCloudSettings()

    def _log(self, message: str) -> None:
        self.log.emit(message)


    @Slot()
    def run(self) -> None:
        try:
            project_dir = Path(PLY_DIR) / self.mesh_id
            input_path = project_dir / ORIGINAL_MESH
            output_path = project_dir / CONVERTED_MESH

            if not input_path.exists():
                raise FileNotFoundError(f"Original point cloud not found: {input_path}")

            self._log(f"Reading point cloud: {input_path}")
            pcd = o3d.io.read_point_cloud(str(input_path))

            if pcd.is_empty():
                raise ValueError("Open3D loaded an empty point cloud.")

            self._log(f"Point cloud has {len(pcd.points)} points.")

            self._log("Converting point cloud to mesh...")
            self._log(
                f"Reconstruction method: "
                f"{getattr(self.settings, 'reconstruction_method', 'poisson')}"
            )

            mesh = point_cloud_to_mesh(
                pcd,
                settings=self.settings,
                log_callback=self._log,
            )

            if mesh.is_empty():
                raise ValueError("Point-cloud conversion produced an empty mesh.")

            self._log("Computing vertex normals...")
            mesh.compute_vertex_normals()


            output_path.parent.mkdir(parents=True, exist_ok=True)

            self._log(f"Saving converted mesh: {output_path}")

            ok = o3d.io.write_triangle_mesh(
                str(output_path),
                mesh,
                write_ascii=False,
                compressed=False,
                write_vertex_normals=True,
                write_vertex_colors=True,
            )

            if not ok:
                raise RuntimeError(f"Failed to write mesh: {output_path}")

            self.success.emit(f"Successfully converted mesh: {output_path}")

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

