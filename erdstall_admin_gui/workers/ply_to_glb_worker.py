from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import trimesh
from PySide6.QtCore import QObject, Signal, Slot

from erdstall_pipeline.config import FINAL_MESH, PLY_DIR
from erdstall_pipeline.settings.glb_export_settings import GlbExportSettings


class PlyToGlbWorker(QObject):
    finished = Signal()
    error = Signal(str)
    log = Signal(str)
    success = Signal(str)

    def __init__(
        self,
        mesh_id: str,
        settings: GlbExportSettings | None = None,
    ) -> None:
        super().__init__()

        self.mesh_id = mesh_id
        self.settings = settings or GlbExportSettings()

        self.add_human_scale = bool(self.settings.add_human_scale)
        self.human_model_path = Path(self.settings.human_model_path)
        self.human_height = float(self.settings.human_height)
        self.human_floor_offset = float(self.settings.human_floor_offset)
        self.human_up_axis = str(self.settings.human_up_axis)

    def _force_vertex_colors_opaque(self, mesh: trimesh.Trimesh) -> None:
        if not hasattr(mesh.visual, "vertex_colors"):
            return

        vertex_colors = np.asarray(mesh.visual.vertex_colors)

        if vertex_colors.size == 0:
            return

        vertex_colors = vertex_colors.copy()

        if vertex_colors.ndim != 2:
            return

        if vertex_colors.shape[1] == 3:
            alpha = np.full(
                (vertex_colors.shape[0], 1),
                255,
                dtype=vertex_colors.dtype,
            )
            vertex_colors = np.hstack((vertex_colors, alpha))
        elif vertex_colors.shape[1] >= 4:
            vertex_colors[:, 3] = 255

        mesh.visual.vertex_colors = vertex_colors

    def _clean_mesh(self, mesh: trimesh.Trimesh) -> trimesh.Trimesh:
        mesh.remove_unreferenced_vertices()
        mesh.remove_infinite_values()

        unique_face_mask = mesh.unique_faces()
        mesh.update_faces(unique_face_mask)
        mesh.remove_unreferenced_vertices()

        non_degenerate_mask = mesh.area_faces > 0
        mesh.update_faces(non_degenerate_mask)
        mesh.remove_unreferenced_vertices()

        return mesh

    def _combined_bounds(
        self,
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
        loaded = trimesh.load(human_path, process=False, force="scene")

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
            self._force_vertex_colors_opaque(geometry)

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
            getattr(self.settings, "rotation_x_degrees", -90.0)
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

    def _make_double_sided_opaque(self, tree: dict) -> dict:
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

    @Slot()
    def run(self) -> None:
        try:
            self.log.emit("Starting PLY to GLB conversion...")

            input_path = PLY_DIR / self.mesh_id / FINAL_MESH
            output_path = PLY_DIR / self.mesh_id / "mesh.glb"

            output_path.parent.mkdir(parents=True, exist_ok=True)

            if not input_path.exists():
                raise FileNotFoundError(f"File not found at {input_path}")

            self.log.emit(f"Reading PLY file: {input_path}")
            loaded = trimesh.load(input_path, process=False)

            if isinstance(loaded, trimesh.Scene):
                if not loaded.geometry:
                    raise ValueError("Loaded scene has no geometry.")
                mesh = trimesh.util.concatenate(tuple(loaded.geometry.values()))
            else:
                mesh = loaded

            if not isinstance(mesh, trimesh.Trimesh):
                raise ValueError("Loaded file is not a valid mesh.")

            if len(mesh.faces) == 0:
                raise ValueError(
                    "PLY file is only a point cloud. GLB export needs a mesh with faces."
                )

            self.log.emit(
                f"Loaded mesh: {len(mesh.vertices):,} vertices, "
                f"{len(mesh.faces):,} faces."
            )

            self.log.emit("Forcing mesh vertex colors to opaque...")
            self._force_vertex_colors_opaque(mesh)

            self.log.emit("Cleaning mesh...")
            mesh = self._clean_mesh(mesh)
            self.log.emit(
                f"After cleanup: {len(mesh.vertices):,} vertices, "
                f"{len(mesh.faces):,} faces."
            )

            geometries: list[tuple[str, trimesh.Trimesh]] = [("mesh", mesh)]

            if self.add_human_scale:
                if self.human_model_path.exists():
                    self.log.emit(
                        f"Loading human scale model: {self.human_model_path}"
                    )

                    human_geometries = self._load_human_model(
                        human_path=self.human_model_path,
                        target_height=self.human_height,
                        up_axis=self.human_up_axis,
                    )

                    self._place_human_next_to_mesh(
                        human_geometries=human_geometries,
                        mesh=mesh,
                        human_height=self.human_height,
                        floor_offset=self.human_floor_offset,
                    )

                    for index, human_geometry in enumerate(human_geometries):
                        geometries.append((f"human_scale_{index}", human_geometry))

                    self.log.emit("Human scale model added.")
                else:
                    self.log.emit(
                        f"Human scale model not found, skipping: "
                        f"{self.human_model_path}"
                    )
            else:
                self.log.emit("Human scale model disabled.")

            self._apply_export_rotation(geometries)

            self.log.emit("Building GLB scene...")
            scene = trimesh.Scene()

            for name, geometry in geometries:
                scene.add_geometry(geometry, geom_name=name)

            self.log.emit("Saving double-sided opaque GLB file...")
            glb_bytes = trimesh.exchange.gltf.export_glb(
                scene,
                include_normals=True,
                tree_postprocessor=self._make_double_sided_opaque,
            )

            output_path.write_bytes(glb_bytes)

            self.success.emit(f"Successfully saved GLB file to {output_path}")

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()