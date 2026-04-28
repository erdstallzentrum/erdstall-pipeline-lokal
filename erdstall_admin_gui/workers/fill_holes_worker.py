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
            from erdstall_pipeline.pipeline import PipelineError, mesh_base_dir, run_finalize
            from erdstall_pipeline.reduce_meshes import reduce_file_size

            base = mesh_base_dir(self.mesh_id)
            original = base / ORIGINAL_MESH
            repaired = base / REPAIRED_MESH

            if not original.exists():
                raise PipelineError(f"Missing input mesh: {original}")

            self.log.emit(f"Starting fill holes for project: {self.mesh_id}")

            fill_holes(
                input_file=str(original),
                output_file=str(repaired),
                settings=self.settings,
                log_callback=self.log.emit,
            )

            if self.settings.reduce_size:
                self.log.emit("Reducing repaired mesh file size...")
                reduce_file_size(str(repaired), initial_mesh_reduction=True)
                self.log.emit("Mesh reduction done.")

            self.log.emit("Running finalize...")
            final_mesh = run_finalize(self.mesh_id)
            self.log.emit(f"Final mesh created: {final_mesh}")

            mobile_mesh = final_mesh.with_name(final_mesh.stem + "_mobile" + final_mesh.suffix)
            if mobile_mesh.exists():
                self.log.emit(f"Mobile mesh created: {mobile_mesh}")

            self.success.emit(
                f"Repaired mesh created: {repaired}\nFinal mesh created: {final_mesh}"
            )
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()