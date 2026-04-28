from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh
from PySide6.QtCore import QObject, Signal, Slot


class PlyToGlbWorker(QObject):
    finished = Signal()
    error = Signal(str)
    log = Signal(str)
    success = Signal(str)

    def __init__(self, mesh_id: str) -> None:
        super().__init__()
        self.mesh_id = mesh_id

    @Slot()
    def run(self) -> None:
        try:
            self.log.emit("Starting PLY TO GLB conversion...")

            input_path = Path("data/ply") / self.mesh_id / "mesh.ply"
            output_path = Path("data/ply") / self.mesh_id / "mesh.glb"

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
                f"Loaded mesh: {len(mesh.vertices):,} vertices, {len(mesh.faces):,} faces."
            )

            self.log.emit("Forcing vertex colors to opaque...")
            if hasattr(mesh.visual, "vertex_colors") and mesh.visual.vertex_colors is not None:
                vertex_colors = np.asarray(mesh.visual.vertex_colors).copy()

                if vertex_colors.size > 0:
                    if vertex_colors.shape[1] == 3:
                        alpha = np.full((vertex_colors.shape[0], 1), 255, dtype=vertex_colors.dtype)
                        vertex_colors = np.hstack((vertex_colors, alpha))
                    elif vertex_colors.shape[1] >= 4:
                        vertex_colors[:, 3] = 255

                    mesh.visual.vertex_colors = vertex_colors

            self.log.emit("Rotating mesh...")
            rotation = trimesh.transformations.rotation_matrix(
                np.radians(-90),
                [1, 0, 0],
            )
            mesh.apply_transform(rotation)
            self.log.emit("Rotating mesh done.")

            self.log.emit("Cleaning mesh...")
            mesh.remove_unreferenced_vertices()
            mesh.remove_infinite_values()

            unique_face_mask = mesh.unique_faces()
            mesh.update_faces(unique_face_mask)
            mesh.remove_unreferenced_vertices()

            non_degenerate_mask = mesh.area_faces > 0
            mesh.update_faces(non_degenerate_mask)
            mesh.remove_unreferenced_vertices()

            self.log.emit(
                f"After cleanup: {len(mesh.vertices):,} vertices, {len(mesh.faces):,} faces."
            )

            self.log.emit("Exporting double-sided opaque GLB...")

            scene = trimesh.Scene(mesh)

            def make_double_sided(tree):
                materials = tree.setdefault("materials", [])

                if not materials:
                    materials.append(
                        {
                            "name": "Default_DoubleSided_Opaque",
                            "doubleSided": True,
                            "alphaMode": "OPAQUE",
                            "pbrMetallicRoughness": {
                                "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
                                "metallicFactor": 0.0,
                                "roughnessFactor": 1.0,
                            },
                        }
                    )

                    for mesh_data in tree.get("meshes", []):
                        for primitive in mesh_data.get("primitives", []):
                            primitive["material"] = 0
                else:
                    for material in materials:
                        material["doubleSided"] = True
                        material["alphaMode"] = "OPAQUE"

                        pbr = material.setdefault("pbrMetallicRoughness", {})
                        base_color = pbr.setdefault(
                            "baseColorFactor",
                            [1.0, 1.0, 1.0, 1.0],
                        )
                        if len(base_color) >= 4:
                            base_color[3] = 1.0

                return tree

            glb_bytes = trimesh.exchange.gltf.export_glb(
                scene,
                include_normals=True,
                tree_postprocessor=make_double_sided,
            )

            output_path.write_bytes(glb_bytes)

            self.success.emit(f"Successfully saved GLB file to {output_path}")

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()