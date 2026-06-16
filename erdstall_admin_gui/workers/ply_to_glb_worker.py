from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import math
import shutil
import subprocess
import time

import numpy as np
import trimesh
from trimesh.exchange.gltf import export_glb

from erdstall_admin_gui.workers.cancelable_worker import (
    CancelableWorker,
    CancellationToken,
)
from erdstall_pipeline.config import FINAL_MESH, PLY_DIR, BASE_DIR, MESH_GLB, MESH_MOBILE_GLB
from erdstall_pipeline.settings.glb_export_settings import GlbExportSettings


CancelCallback = Callable[[], None] | None


def _check_cancelled(cancel_callback: CancelCallback) -> None:
    if cancel_callback is not None:
        cancel_callback()


class PlyToGlbWorker(CancelableWorker):
    def __init__(
        self,
        mesh_id: str,
        settings: GlbExportSettings | None = None,
        cancel_token: CancellationToken | None = None,
    ) -> None:
        super().__init__(cancel_token)

        self.mesh_id = mesh_id
        self.settings = settings or GlbExportSettings()

        self.add_human_scale = bool(getattr(self.settings, "add_human_scale", False))
        self.create_mobile_glb = bool(getattr(self.settings, "create_mobile_glb", True))

        self.human_model_path = Path(
            getattr(self.settings, "human_model_path", "public/person.glb")
        ).expanduser()

        if not self.human_model_path.is_absolute():
            self.human_model_path = Path(BASE_DIR) / self.human_model_path

        self.human_height = float(getattr(self.settings, "human_height", 1.75))
        self.human_floor_offset = float(
            getattr(self.settings, "human_floor_offset", 0.02)
        )
        self.human_up_axis = str(getattr(self.settings, "human_up_axis", "y"))

        self.add_human_to_mobile = bool(
            getattr(self.settings, "add_human_to_mobile", False)
        )

        self.optimize_glb = bool(getattr(self.settings, "optimize_glb", True))

        self.glb_compression = str(
            getattr(self.settings, "glb_compression", "meshopt")
        ).lower().strip()

        self.main_include_normals = bool(
            getattr(self.settings, "main_include_normals", True)
        )

        self.mobile_include_normals = bool(
            getattr(self.settings, "mobile_include_normals", False)
        )

    def _export_glb(
        self,
        input_path: Path,
        output_path: Path,
        label: str,
        cancel_callback: CancelCallback = None,
    ) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if not input_path.exists():
            raise FileNotFoundError(f"{label} input file not found at {input_path}")

        self.log.emit(f"Reading {label} PLY file: {input_path}")

        loaded = trimesh.load_mesh(str(input_path), process=False)

        _check_cancelled(cancel_callback)

        if isinstance(loaded, trimesh.Scene):
            if not loaded.geometry:
                raise ValueError(f"Loaded {label} scene has no geometry.")

            mesh = trimesh.util.concatenate(tuple(loaded.geometry.values()))
        else:
            mesh = loaded

        if not isinstance(mesh, trimesh.Trimesh):
            raise ValueError(f"Loaded {label} file is not a valid mesh.")

        _check_cancelled(cancel_callback)

        if len(mesh.faces) == 0:
            raise ValueError(
                f"{label} PLY file is only a point cloud. "
                "GLB export needs a mesh with faces."
            )

        self.log.emit(
            f"Loaded {label} mesh: {len(mesh.vertices):,} vertices, "
            f"{len(mesh.faces):,} faces."
        )

        _check_cancelled(cancel_callback)

        self.log.emit(f"Forcing {label} mesh vertex colors to opaque...")
        self._force_vertex_colors_opaque(
            mesh,
            cancel_callback=cancel_callback,
        )

        self.log.emit(f"Cleaning {label} mesh...")
        mesh = self._clean_mesh(mesh)

        self.log.emit(
            f"After {label} cleanup: {len(mesh.vertices):,} vertices, "
            f"{len(mesh.faces):,} faces."
        )

        geometries: list[tuple[str, trimesh.Trimesh]] = [(label, mesh)]

        _check_cancelled(cancel_callback)

        should_add_human = self.add_human_scale and (
            label == "main" or self.add_human_to_mobile
        )

        if should_add_human:
            if self.human_model_path.exists():
                self.log.emit(
                    f"Loading human scale model for {label}: {self.human_model_path}"
                )

                _check_cancelled(cancel_callback)

                human_geometries = self._load_human_model(
                    human_path=self.human_model_path,
                    target_height=self.human_height,
                    up_axis=self.human_up_axis,
                )

                _check_cancelled(cancel_callback)

                self._place_human_next_to_mesh(
                    human_geometries=human_geometries,
                    mesh=mesh,
                    human_height=self.human_height,
                    floor_offset=self.human_floor_offset,
                )

                for index, human_geometry in enumerate(human_geometries):
                    geometries.append(
                        (f"{label}_human_scale_{index}", human_geometry)
                    )

                self.log.emit(f"Human scale model added to {label}.")
            else:
                self.log.emit(
                    f"Human scale model not found, skipping for {label}: "
                    f"{self.human_model_path}"
                )
        else:
            self.log.emit(f"Human scale model disabled for {label}.")

        _check_cancelled(cancel_callback)

        self._apply_export_rotation(geometries)

        self.log.emit(f"Building {label} GLB scene...")

        scene = trimesh.Scene()

        for name, geometry in geometries:
            scene.add_geometry(geometry, geom_name=name)

        _check_cancelled(cancel_callback)

        include_normals = self._should_include_normals(label)

        self.log.emit(
            f"Saving {label} GLB file: {output_path} "
            f"(include_normals={include_normals})"
        )

        glb_bytes = export_glb(
            scene,
            include_normals=include_normals,
            tree_postprocessor=self._make_double_sided_opaque,
        )

        _check_cancelled(cancel_callback)

        output_path.write_bytes(glb_bytes)

        raw_size_mb = self._file_size_mb(output_path)

        self.log.emit(
            f"{label} raw GLB saved: {output_path} "
            f"({raw_size_mb:.2f} MB)"
        )

        if self.optimize_glb:
            self._optimize_glb_with_gltf_transform(
                input_path=output_path,
                output_path=output_path,
                label=label,
                cancel_callback=cancel_callback,
            )
        else:
            self.log.emit(f"GLB optimization disabled for {label}.")

    def _should_include_normals(self, label: str) -> bool:
        if label == "mobile":
            return self.mobile_include_normals

        return self.main_include_normals

    @staticmethod
    def _find_gltf_transform_executable() -> str | None:
        roots = [
            Path(BASE_DIR),
            Path.cwd(),
        ]

        for root in roots:
            local_windows = root / "node_modules" / ".bin" / "gltf-transform.cmd"
            local_unix = root / "node_modules" / ".bin" / "gltf-transform"

            if local_windows.exists():
                return str(local_windows)

            if local_unix.exists():
                return str(local_unix)

        cmd: str = "gltf-transform"
        return shutil.which(cmd)

    def _build_gltf_transform_command(
        self,
        executable: str,
        input_path: Path,
        output_path: Path,
    ) -> list[str]:
        if executable.lower().endswith(".cmd"):
            command = [
                "cmd",
                "/c",
                executable,
                "optimize",
                str(input_path),
                str(output_path),
            ]
        else:
            command = [
                executable,
                "optimize",
                str(input_path),
                str(output_path),
            ]

        if self.glb_compression in {"meshopt", "draco"}:
            command.extend(["--compress", self.glb_compression])
        elif self.glb_compression in {"none", "", "false"}:
            command.extend(["--compress", "false"])
        else:
            self.log.emit(
                f"Unknown GLB compression '{self.glb_compression}', using meshopt."
            )
            command.extend(["--compress", "meshopt"])

        return command

    def _optimize_glb_with_gltf_transform(
        self,
        input_path: Path,
        output_path: Path,
        label: str,
        cancel_callback: CancelCallback = None,
    ) -> None:
        executable = self._find_gltf_transform_executable()

        if executable is None:
            self.log.emit(
                "gltf-transform not found. Skipping GLB optimization. "
                "Run 'npm install' in the project root first."
            )
            return

        if not input_path.exists():
            raise FileNotFoundError(f"Cannot optimize missing GLB: {input_path}")

        original_size_mb = self._file_size_mb(input_path)

        temp_output_path = output_path.with_name(
            f"{output_path.stem}_optimized_tmp{output_path.suffix}"
        )

        if temp_output_path.exists():
            temp_output_path.unlink()

        command = self._build_gltf_transform_command(
            executable=executable,
            input_path=input_path,
            output_path=temp_output_path,
        )

        self.log.emit(
            f"Optimizing {label} GLB with gltf-transform "
            f"(compression={self.glb_compression})..."
        )
        self.log.emit(" ".join(command))

        _check_cancelled(cancel_callback)

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            while process.poll() is None:
                _check_cancelled(cancel_callback)
                time.sleep(0.2)

            stdout, stderr = process.communicate()
        except BaseException:
            process.terminate()

            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()

            raise

        if stdout.strip():
            self.log.emit(stdout.strip())

        if stderr.strip():
            self.log.emit(stderr.strip())

        if process.returncode != 0:
            if temp_output_path.exists():
                temp_output_path.unlink()

            self.log.emit(
                f"gltf-transform failed for {label}. "
                "Keeping raw GLB instead."
            )
            return

        if not temp_output_path.exists():
            self.log.emit(
                f"gltf-transform did not create output for {label}. "
                "Keeping raw GLB instead."
            )
            return

        optimized_size_mb = self._file_size_mb(temp_output_path)

        temp_output_path.replace(output_path)

        reduction_percent = 0.0

        if original_size_mb > 0:
            reduction_percent = (
                (original_size_mb - optimized_size_mb) / original_size_mb
            ) * 100.0

        self.log.emit(
            f"{label} GLB optimized: "
            f"{original_size_mb:.2f} MB -> {optimized_size_mb:.2f} MB "
            f"({reduction_percent:.1f}% smaller)"
        )
    @staticmethod
    def _force_vertex_colors_opaque(
        mesh: trimesh.Trimesh,
        cancel_callback: CancelCallback = None,
    ) -> None:
        if not hasattr(mesh.visual, "vertex_colors"):
            return

        _check_cancelled(cancel_callback)

        vertex_colors = np.asarray(mesh.visual.vertex_colors)

        if vertex_colors.size == 0:
            return

        if vertex_colors.ndim != 2:
            return

        if vertex_colors.shape[1] >= 4:
            vertex_colors = vertex_colors.copy()
            vertex_colors[:, 3] = 255
            mesh.visual.vertex_colors = vertex_colors

    @staticmethod
    def _clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        mesh.remove_unreferenced_vertices()
        mesh.remove_infinite_values()

        unique_face_mask = mesh.unique_faces()
        mesh.update_faces(unique_face_mask)
        mesh.remove_unreferenced_vertices()

        non_degenerate_mask = mesh.area_faces > 0
        mesh.update_faces(non_degenerate_mask)
        mesh.remove_unreferenced_vertices()

        return mesh

    @staticmethod
    def _combined_bounds(
        geometries: list[trimesh.Trimesh],
    ) -> tuple[np.ndarray, np.ndarray]:
        if not geometries:
            raise ValueError("No geometries available for bounds calculation.")

        mins = []
        maxs = []

        for geometry in geometries:
            if geometry.bounds is None:
                continue

            mins.append(geometry.bounds[0])
            maxs.append(geometry.bounds[1])

        if not mins or not maxs:
            raise ValueError("Could not calculate geometry bounds.")

        return np.min(np.vstack(mins), axis=0), np.max(np.vstack(maxs), axis=0)

    def _load_human_model(
        self,
        human_path: Path,
        target_height: float,
        up_axis: str,
    ) -> list[trimesh.Trimesh]:
        loaded = trimesh.load(str(human_path), process=False, force="scene")

        if isinstance(loaded, trimesh.Scene):
            geometries = list(loaded.dump(concatenate=False))
        elif isinstance(loaded, trimesh.Trimesh):
            geometries = [loaded]
        else:
            raise ValueError("Human model is not a valid mesh or scene.")

        geometries = [
            geometry.copy()
            for geometry in geometries
            if isinstance(geometry, trimesh.Trimesh) and len(geometry.faces) > 0
        ]

        if not geometries:
            raise ValueError("Human model contains no valid mesh geometry.")

        up_axis = up_axis.lower().strip()

        if up_axis == "y":
            y_to_z = trimesh.transformations.rotation_matrix(
                math.radians(90.0),
                [1, 0, 0],
            )

            for geometry in geometries:
                geometry.apply_transform(y_to_z)

        elif up_axis == "x":
            x_to_z = trimesh.transformations.rotation_matrix(
                math.radians(-90.0),
                [0, 1, 0],
            )

            for geometry in geometries:
                geometry.apply_transform(x_to_z)

        elif up_axis == "z":
            pass

        else:
            raise ValueError("human_up_axis must be 'x', 'y', or 'z'.")

        human_min, human_max = self._combined_bounds(geometries)
        current_height = float(human_max[2] - human_min[2])

        if current_height <= 0:
            raise ValueError("Human model has invalid height.")

        scale = target_height / current_height

        for geometry in geometries:
            geometry.apply_scale(scale)
            self._force_vertex_colors_opaque(
                geometry,
                cancel_callback=self.check_cancelled,
            )

        return geometries

    def _place_human_next_to_mesh(
        self,
        human_geometries: list[trimesh.Trimesh],
        mesh: trimesh.Trimesh,
        human_height: float,
        floor_offset: float,
    ) -> None:
        mesh_min, mesh_max = mesh.bounds
        mesh_size = mesh_max - mesh_min

        human_min, human_max = self._combined_bounds(human_geometries)
        human_center = (human_min + human_max) * 0.5

        target_x = mesh_min[0] + mesh_size[0] * 0.05
        target_y = mesh_min[1] - human_height * 0.05
        target_z = mesh_min[2] + floor_offset

        translation = np.array(
            [
                target_x - human_center[0],
                target_y - human_center[1],
                target_z - human_min[2],
            ],
            dtype=float,
        )

        for geometry in human_geometries:
            geometry.apply_translation(translation)

        self.log.emit(
            "Human model placed at "
            f"x={target_x:.3f}, y={target_y:.3f}, z={target_z:.3f}"
        )

    def _apply_export_rotation(
        self,
        geometries: list[tuple[str, trimesh.Trimesh]],
    ) -> None:
        rotation_x_degrees = float(
            getattr(self.settings, "rotation_x_degrees", 0.0)
        )
        rotation_y_degrees = float(
            getattr(self.settings, "rotation_y_degrees", 0.0)
        )
        rotation_z_degrees = float(
            getattr(self.settings, "rotation_z_degrees", 0.0)
        )

        if (
            rotation_x_degrees == 0.0
            and rotation_y_degrees == 0.0
            and rotation_z_degrees == 0.0
        ):
            self.log.emit("Export rotation skipped.")
            return

        self.log.emit(
            "Applying export rotation: "
            f"x={rotation_x_degrees:.2f}, "
            f"y={rotation_y_degrees:.2f}, "
            f"z={rotation_z_degrees:.2f}"
        )

        rx = math.radians(rotation_x_degrees)
        ry = math.radians(rotation_y_degrees)
        rz = math.radians(rotation_z_degrees)

        rotation = trimesh.transformations.euler_matrix(
            rx,
            ry,
            rz,
            axes="sxyz",
        )

        for _, geometry in geometries:
            geometry.apply_transform(rotation)

        self.log.emit("Export rotation done.")
    @staticmethod
    def _make_double_sided_opaque(tree: dict) -> dict:
        materials = tree.setdefault("materials", [])

        default_material_index = len(materials)

        materials.append(
            {
                "name": "Default_VertexColor_White_DoubleSided_Opaque",
                "doubleSided": True,
                "alphaMode": "OPAQUE",
                "pbrMetallicRoughness": {
                    "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                    "metallicFactor": 0.0,
                    "roughnessFactor": 1.0,
                },
            }
        )

        for material in materials:
            material["doubleSided"] = True
            material["alphaMode"] = "OPAQUE"

            if "alphaCutoff" in material:
                del material["alphaCutoff"]

            pbr = material.setdefault("pbrMetallicRoughness", {})
            base_color = pbr.setdefault(
                "baseColorFactor",
                [1.0, 1.0, 1.0, 1.0],
            )

            while len(base_color) < 4:
                base_color.append(1.0)

            base_color[3] = 1.0

        for mesh_data in tree.get("meshes", []):
            for primitive in mesh_data.get("primitives", []):
                if "material" not in primitive:
                    primitive["material"] = default_material_index

        return tree
    @staticmethod
    def _file_size_mb(path: Path) -> float:
        if not path.exists():
            return 0.0

        return path.stat().st_size / 1024 / 1024

    def execute(self) -> str:
        self.write_log("Starting PLY to GLB conversion...")

        project_dir = Path(PLY_DIR) / self.mesh_id

        final_input_path = project_dir / FINAL_MESH
        final_output_path = project_dir / MESH_GLB

        self.check_cancelled()

        self._export_glb(
            input_path=final_input_path,
            output_path=final_output_path,
            label="main",
            cancel_callback=self.check_cancelled,
        )

        success_message = f"Successfully saved GLB file to {final_output_path}"

        self.check_cancelled()

        if self.create_mobile_glb:
            mobile_input_path = final_input_path.with_name(
                f"{final_input_path.stem}_mobile{final_input_path.suffix}"
            )
            mobile_output_path = project_dir / MESH_MOBILE_GLB

            self.write_log("Mobile GLB export enabled.")

            if not mobile_input_path.exists():
                self.write_log(
                    f"Mobile mesh not found, skipping mobile GLB: {mobile_input_path}"
                )
            else:
                self._export_glb(
                    input_path=mobile_input_path,
                    output_path=mobile_output_path,
                    label="mobile",
                    cancel_callback=self.check_cancelled,
                )

                success_message += (
                    f"\nSuccessfully saved mobile GLB file to {mobile_output_path}"
                )
        else:
            self.write_log("Mobile GLB export disabled.")

        self.check_cancelled()

        return success_message