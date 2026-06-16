from __future__ import annotations

from pathlib import Path

from erdstall_pipeline.config import CONVERTED_MESH
from erdstall_admin_gui.workers.cancelable_worker import (
    CancelableWorker,
    CancellationToken,
)
from erdstall_pipeline.config import ORIGINAL_MESH, REPAIRED_MESH
from erdstall_pipeline.settings.fill_holes_settings import FillHolesSettings


class FillHolesWorker(CancelableWorker):
    def __init__(
        self,
        mesh_id: str,
        settings: FillHolesSettings,
        cancel_token: CancellationToken | None = None,
    ) -> None:
        super().__init__(cancel_token)
        self.mesh_id = mesh_id
        self.settings = settings

    def execute(self) -> str:
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
        converted = base / CONVERTED_MESH
        repaired = base / REPAIRED_MESH

        self.write_log(f"Starting fill holes for project: {self.mesh_id}")

        self.check_cancelled()

        is_point_cloud = is_point_cloud_project(self.mesh_id)

        if is_point_cloud:
            self.write_log("Project type detected: point cloud")
            self.write_log("Using converted mesh as Fill Holes input.")

            if not converted.exists():
                raise PipelineError(
                    "This is a point-cloud project. "
                    "Run Convert Point Cloud to Mesh before Fill Holes."
                )

            input_mesh = converted
            output_mesh = repaired
        else:
            self.write_log("Project type detected: mesh")
            self.write_log("Using original mesh as Fill Holes input.")

            if not original.exists():
                raise PipelineError(f"Missing input mesh: {original}")

            input_mesh = original
            output_mesh = repaired

        self.write_log(f"Fill Holes input: {input_mesh}")
        self.write_log(f"Fill Holes output: {output_mesh}")

        self.check_cancelled()

        fill_holes(
            input_file=str(input_mesh),
            output_file=str(output_mesh),
            settings=self.settings,
            log_callback=self.log.emit,
            cancel_callback=self.check_cancelled,
        )

        self.check_cancelled()

        self.write_log("Running finalize...")
        final_mesh = run_finalize(self.mesh_id)
        self.write_log(f"Final mesh created: {final_mesh}")

        self.check_cancelled()

        if self.settings.reduce_size:
            self.write_log("Creating reduced mobile mesh version...")

            mobile_mesh_path = reduce_file_size(
                str(final_mesh),
                initial_mesh_reduction=False,
                compression_percentage=self.settings.mesh_reduction_percent,
                cancel_callback=self.check_cancelled,
            )

            if mobile_mesh_path is None:
                self.write_log("Mobile mesh reduction did not return file path.")
                return "Mobile mesh reduction did not return file path."

            mobile_mesh = Path(mobile_mesh_path)

            if mobile_mesh.exists():
                self.write_log(f"Mobile mesh created: {mobile_mesh}")
        else:
            self.write_log("Skipping mobile mesh reduction.")

        return f"Final mesh created: {final_mesh}"