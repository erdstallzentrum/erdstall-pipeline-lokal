from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from erdstall_pipeline.config import ORIGINAL_MESH, REPAIRED_MESH
from erdstall_pipeline.settings.fill_holes_settings import FillHolesSettings


class FillHolesWorker(QObject):
    finished = Signal()
    log = Signal(str)
    success = Signal(str)
    error = Signal(str)

    def __init__(self, mesh_id: str, settings: FillHolesSettings) -> None:
        super().__init__()
        self.mesh_id = mesh_id
        self.settings = settings

    @Slot()
    def run(self) -> None:
        try:
            from erdstall_pipeline.fill_holes import fill_holes
            from erdstall_pipeline.pipeline import (
                PipelineError,
                is_point_cloud_project,
                mesh_base_dir,
                run_finalize,
            )
            from erdstall_pipeline.reduce_meshes import reduce_file_size

            base = mesh_base_dir(self.mesh_id)
            original = base / ORIGINAL_MESH
            repaired = base / REPAIRED_MESH

            self.log.emit(f"Starting fill holes for project: {self.mesh_id}")

            is_point_cloud = is_point_cloud_project(self.mesh_id)

            if is_point_cloud:
                self.log.emit("Project type detected: point cloud")
                self.log.emit("Using converted mesh as Fill Holes input.")

                if not repaired.exists():
                    raise PipelineError(
                        "This is a point-cloud project. "
                        "Run Convert Point Cloud to Mesh before Fill Holes."
                    )

                input_mesh = repaired
                output_mesh = repaired
            else:
                self.log.emit("Project type detected: mesh")
                self.log.emit("Using original mesh as Fill Holes input.")

                if not original.exists():
                    raise PipelineError(f"Missing input mesh: {original}")

                input_mesh = original
                output_mesh = repaired

            self.log.emit(f"Fill Holes input: {input_mesh}")
            self.log.emit(f"Fill Holes output: {output_mesh}")

            fill_holes(
                input_file=str(input_mesh),
                output_file=str(output_mesh),
                settings=self.settings,
                log_callback=self.log.emit,
            )

            if self.settings.reduce_size:
                self.log.emit("Reducing repaired mesh file size...")
                reduce_file_size(
                    str(output_mesh),
                    initial_mesh_reduction=True,
                    compression_percentage=self.settings.mesh_reduction_percent,
                )
                self.log.emit("Mesh reduction done.")
            else:
                self.log.emit("Skipping mesh reduction.")

            self.log.emit("Running finalize...")
            final_mesh = run_finalize(self.mesh_id)
            self.log.emit(f"Final mesh created: {final_mesh}")

            mobile_mesh = final_mesh.with_name(
                final_mesh.stem + "_mobile" + final_mesh.suffix
            )
            if mobile_mesh.exists():
                self.log.emit(f"Mobile mesh created: {mobile_mesh}")

            self.success.emit(
                f"Repaired mesh created: {repaired}\nFinal mesh created: {final_mesh}"
            )

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()