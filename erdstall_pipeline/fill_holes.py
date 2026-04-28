from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import tempfile

import numpy as np
import open3d as o3d
import pymeshlab
from scipy.spatial import cKDTree

from .convert_point_cloud import point_cloud_to_mesh
from .settings.fill_holes_settings import FillHolesSettings


LogCallback = Callable[[str], None] | None


def _mesh_count(ms: pymeshlab.MeshSet) -> int:
    if hasattr(ms, "mesh_number"):
        return ms.mesh_number()
    return ms.number_meshes()


def _query_tree(
    tree: cKDTree,
    points: np.ndarray,
    k: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    try:
        return tree.query(points, k=k, workers=-1)
    except TypeError:
        return tree.query(points, k=k)


def _transfer_point_cloud_colors_to_open3d_mesh(
    mesh: o3d.geometry.TriangleMesh,
    pcd: o3d.geometry.PointCloud,
    log_callback: Callable[[str], None],
    chunk_size: int = 1_000_000,
) -> o3d.geometry.TriangleMesh:
    if not pcd.has_colors():
        log_callback("Point-cloud color transfer skipped: point cloud has no colors.")
        return mesh

    points = np.asarray(pcd.points, dtype=np.float64)
    colors = np.asarray(pcd.colors, dtype=np.float64)
    vertices = np.asarray(mesh.vertices, dtype=np.float64)

    if points.size == 0 or vertices.size == 0:
        log_callback("Point-cloud color transfer skipped: empty points or vertices.")
        return mesh

    tree = cKDTree(points)
    vertex_count = vertices.shape[0]
    vertex_colors = np.empty((vertex_count, 3), dtype=np.float64)

    log_callback(f"Transferring original point-cloud colors to {vertex_count:,} vertices...")

    for start in range(0, vertex_count, chunk_size):
        end = min(start + chunk_size, vertex_count)

        _, nearest_indices = _query_tree(tree, vertices[start:end], k=1)
        vertex_colors[start:end] = colors[nearest_indices]

        percent = end / vertex_count * 100.0
        log_callback(
            f"Point-cloud color transfer progress: "
            f"{end:,} / {vertex_count:,} ({percent:.1f}%)"
        )

    mesh.vertex_colors = o3d.utility.Vector3dVector(vertex_colors)
    log_callback("Point-cloud color transfer done.")

    return mesh


def _save_current_mesh_with_point_cloud_colors(
    ms: pymeshlab.MeshSet,
    output_file: str,
    pcd: o3d.geometry.PointCloud,
    log_callback: Callable[[str], None],
) -> None:
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / "final_geometry.ply"

        log_callback(f"Saving temporary final geometry: {temp_path}")
        ms.save_current_mesh(
            str(temp_path),
            save_vertex_color=True,
            save_wedge_texcoord=False,
            save_textures=False,
        )

        log_callback("Loading final geometry with Open3D for color transfer...")
        mesh = o3d.io.read_triangle_mesh(str(temp_path))

    if mesh.is_empty():
        raise ValueError("Open3D loaded an empty final mesh.")

    mesh = _transfer_point_cloud_colors_to_open3d_mesh(
        mesh=mesh,
        pcd=pcd,
        log_callback=log_callback,
    )

    log_callback("Computing final Open3D vertex normals...")
    mesh.compute_vertex_normals()

    log_callback(f"Saving repaired mesh with point-cloud colors: {output_file}")
    o3d.io.write_triangle_mesh(
        output_file,
        mesh,
        write_ascii=False,
        compressed=False,
        write_vertex_normals=True,
        write_vertex_colors=True,
    )


def keep_largest_connected_component(
    ms: pymeshlab.MeshSet,
    log_callback: Callable[[str], None] | None = None,
) -> int:
    def log(message: str) -> None:
        if log_callback is not None:
            log_callback(message)
        else:
            print(message)

    mesh = ms.current_mesh()

    vertices = mesh.vertex_matrix()
    faces = mesh.face_matrix()

    if vertices.size == 0:
        log("Largest component cleanup skipped: mesh has no vertices.")
        return _mesh_count(ms) - 1

    if faces.size == 0:
        log("Largest component cleanup skipped: mesh has no faces.")
        return _mesh_count(ms) - 1

    face_count = faces.shape[0]
    vertex_count = vertices.shape[0]

    log(f"Finding connected components in mesh with {face_count:,} faces...")

    vertex_to_faces: list[list[int]] = [[] for _ in range(vertex_count)]

    for face_index, face in enumerate(faces):
        for vertex_index in face:
            vertex_to_faces[int(vertex_index)].append(face_index)

    visited = np.zeros(face_count, dtype=bool)
    components: list[list[int]] = []

    for start_face in range(face_count):
        if visited[start_face]:
            continue

        stack = [start_face]
        visited[start_face] = True
        component_faces: list[int] = []

        while stack:
            face_index = stack.pop()
            component_faces.append(face_index)

            for vertex_index in faces[face_index]:
                for connected_face in vertex_to_faces[int(vertex_index)]:
                    if not visited[connected_face]:
                        visited[connected_face] = True
                        stack.append(connected_face)

        components.append(component_faces)

    if len(components) <= 1:
        log("Mesh has only one connected component. Nothing removed.")
        return _mesh_count(ms) - 1

    largest_component_index = max(
        range(len(components)),
        key=lambda index: len(components[index]),
    )

    largest_component_faces = components[largest_component_index]

    log(f"Found {len(components):,} connected components.")
    log(
        f"Largest component: {largest_component_index}, "
        f"{len(largest_component_faces):,} faces."
    )

    sorted_component_info = sorted(
        ((index, len(component)) for index, component in enumerate(components)),
        key=lambda item: item[1],
        reverse=True,
    )

    max_components_to_log = 30
    for index, face_total in sorted_component_info[:max_components_to_log]:
        label = "KEEP" if index == largest_component_index else "REMOVE"
        log(f"Component {index}: {face_total:,} faces -> {label}")

    if len(components) > max_components_to_log:
        log(
            f"... skipped logging "
            f"{len(components) - max_components_to_log:,} smaller components."
        )

    keep_face_mask = np.zeros(face_count, dtype=bool)
    keep_face_mask[largest_component_faces] = True

    kept_faces = faces[keep_face_mask]
    removed_faces = int(face_count - kept_faces.shape[0])
    removed_percent = removed_faces / face_count * 100.0

    try:
        vertex_colors = mesh.vertex_color_matrix()

        cleaned_mesh = pymeshlab.Mesh(
            vertex_matrix=vertices,
            face_matrix=kept_faces,
            v_color_matrix=vertex_colors,
        )
    except Exception:
        cleaned_mesh = pymeshlab.Mesh(
            vertex_matrix=vertices,
            face_matrix=kept_faces,
        )

    ms.add_mesh(cleaned_mesh, "largest_connected_component_only")

    cleaned_index = _mesh_count(ms) - 1
    ms.set_current_mesh(cleaned_index)

    ms.meshing_remove_unreferenced_vertices()

    log(
        f"Kept largest component with {len(largest_component_faces):,} faces. "
        f"Removed {removed_faces:,} / {face_count:,} disconnected face(s) "
        f"({removed_percent:.2f}%)."
    )

    return cleaned_index


def smooth_current_mesh(
    ms: pymeshlab.MeshSet,
    iterations: int,
    log_callback: Callable[[str], None] | None = None,
) -> None:
    def log(message: str) -> None:
        if log_callback is not None:
            log_callback(message)
        else:
            print(message)

    mesh = ms.current_mesh()

    if mesh.vertex_number() == 0 or mesh.face_number() == 0:
        log("Smoothing skipped: mesh has no vertices or faces.")
        return

    if iterations <= 0:
        log("Smoothing skipped: iterations <= 0.")
        return

    log(f"Applying Taubin smoothing, iterations={iterations}...")

    try:
        ms.apply_coord_taubin_smoothing(
            stepsmoothnum=iterations,
            lambda_=0.5,
            mu=-0.53,
            selected=False,
        )
        log("Taubin smoothing done.")
    except Exception as e:
        log(f"Taubin smoothing failed: {e}")
        log("Trying Laplacian smoothing fallback...")

        ms.apply_coord_laplacian_smoothing(
            stepsmoothnum=max(1, iterations // 2),
            selected=False,
            boundary=True,
        )

        log("Laplacian smoothing fallback done.")

    log("Recomputing normals after smoothing...")
    ms.compute_normal_per_face()
    ms.compute_normal_per_vertex()
    log("Normals recomputed after smoothing.")


def close_holes_aggressively(
    ms: pymeshlab.MeshSet,
    max_hole_size: int,
    log_callback: Callable[[str], None] | None = None,
) -> None:
    def log(message: str) -> None:
        if log_callback is not None:
            log_callback(message)
        else:
            print(message)

    log(f"Closing holes with max size {max_hole_size:,}...")

    try:
        ms.meshing_close_holes(
            maxholesize=max_hole_size,
            selected=False,
            newfaceselected=False,
            selfintersection=True,
        )
        log("Hole closing done.")
    except Exception as e:
        log(f"Hole closing skipped: {e}")


def fill_holes(
    input_file: str,
    output_file: str,
    settings: FillHolesSettings | None = None,
    log_callback: LogCallback = None,
) -> None:
    if settings is None:
        settings = FillHolesSettings()

    def log(message: str) -> None:
        if log_callback is not None:
            log_callback(message)
        else:
            print(message)

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ms = pymeshlab.MeshSet()

    log("Loading mesh...")
    ms.load_new_mesh(input_file)
    log("Loading mesh done.")

    original_index = 0
    original_mesh = ms.mesh(original_index)
    input_is_point_cloud = original_mesh.face_number() == 0

    source_mesh_index: int | None = original_index
    original_pcd: o3d.geometry.PointCloud | None = None

    if input_is_point_cloud:
        log("Detected point cloud input.")

        log("Loading point cloud with Open3D...")
        original_pcd = o3d.io.read_point_cloud(input_file)

        if original_pcd.is_empty():
            raise ValueError("Open3D loaded an empty point cloud.")

        log(f"Point cloud has {len(original_pcd.points):,} points.")

        log("Running Open3D point-cloud reconstruction...")
        o3d_mesh = point_cloud_to_mesh(
            original_pcd,
            settings=settings.point_cloud_settings,
            log_callback=log,
        )
        log("Open3D point-cloud reconstruction done.")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_mesh_path = Path(temp_dir) / "open3d_reconstructed_mesh.ply"

            log(f"Saving temporary Open3D mesh: {temp_mesh_path}")
            o3d.io.write_triangle_mesh(
                str(temp_mesh_path),
                o3d_mesh,
                write_ascii=False,
                compressed=False,
                write_vertex_normals=True,
                write_vertex_colors=True,
            )

            log("Loading reconstructed mesh into PyMeshLab...")
            ms.load_new_mesh(str(temp_mesh_path))

        final_mesh_index = _mesh_count(ms) - 1
        ms.set_current_mesh(final_mesh_index)

        log("Keeping largest component after Open3D reconstruction...")
        final_mesh_index = keep_largest_connected_component(
            ms,
            log_callback=log,
        )
        ms.set_current_mesh(final_mesh_index)
        log("Largest component cleanup done.")

        log("Computing normals before post-Poisson...")
        ms.compute_normal_per_face()
        ms.compute_normal_per_vertex()
        log("Normals computed.")

        log("Running PyMeshLab post-Poisson to close remaining holes...")
        ms.generate_surface_reconstruction_screened_poisson(
            depth=settings.point_cloud_depth,
            fulldepth=settings.point_cloud_fulldepth,
            scale=settings.point_cloud_scale,
            samplespernode=settings.point_cloud_samplespernode,
            pointweight=settings.point_cloud_pointweight,
            iters=settings.point_cloud_iters,
            preclean=settings.point_cloud_preclean,
        )
        log("PyMeshLab post-Poisson done.")

        final_mesh_index = _mesh_count(ms) - 1
        ms.set_current_mesh(final_mesh_index)

        log("Keeping largest component after post-Poisson...")
        final_mesh_index = keep_largest_connected_component(
            ms,
            log_callback=log,
        )
        ms.set_current_mesh(final_mesh_index)
        log("Post-Poisson largest component cleanup done.")

        close_holes_aggressively(
            ms,
            max_hole_size=max(settings.mesh_hole_max_size, 1_000_000),
            log_callback=log,
        )

        if settings.smooth_reconstructed_point_cloud_mesh:
            smooth_current_mesh(
                ms,
                iterations=settings.point_cloud_smoothing_iterations,
                log_callback=log,
            )
        else:
            log("Skipping smoothing for reconstructed point cloud mesh.")

        source_mesh_index = None

        log("Point cloud converted to closed mesh.")

    else:
        log("Detected mesh input.")

        ms.set_current_mesh(original_index)

        log("Cleaning mesh...")
        ms.meshing_remove_unreferenced_vertices()
        ms.meshing_remove_duplicate_faces()
        ms.meshing_remove_duplicate_vertices()
        log("Cleaning mesh done.")

        log("Repairing topology...")
        ms.meshing_repair_non_manifold_edges()
        ms.meshing_repair_non_manifold_vertices()
        log("Repairing topology done.")

        log("Keeping only largest connected component...")
        cleaned_mesh_index = keep_largest_connected_component(
            ms,
            log_callback=log,
        )
        ms.set_current_mesh(cleaned_mesh_index)
        log("Largest connected component cleanup done.")

        log("Computing normals...")
        ms.compute_normal_per_face()
        ms.compute_normal_per_vertex()
        log("Computing normals done.")

        if settings.run_poisson_on_mesh:
            log("Running Poisson reconstruction on mesh input...")
            ms.generate_surface_reconstruction_screened_poisson(
                depth=settings.poisson_depth,
                fulldepth=settings.poisson_fulldepth,
                cgdepth=settings.poisson_cgdepth,
                scale=settings.poisson_scale,
                samplespernode=settings.poisson_samplespernode,
                pointweight=settings.poisson_pointweight,
                iters=settings.poisson_iters,
                preclean=settings.poisson_preclean,
            )
            log("Poisson reconstruction done.")

            final_mesh_index = _mesh_count(ms) - 1
            ms.set_current_mesh(final_mesh_index)

            log("Keeping only largest connected component after Poisson...")
            final_mesh_index = keep_largest_connected_component(
                ms,
                log_callback=log,
            )
            ms.set_current_mesh(final_mesh_index)
            log("Post-Poisson largest component cleanup done.")

        else:
            final_mesh_index = cleaned_mesh_index
            ms.set_current_mesh(final_mesh_index)

        if settings.close_holes_on_mesh_input:
            close_holes_aggressively(
                ms,
                max_hole_size=max(settings.mesh_hole_max_size, 1_000_000),
                log_callback=log,
            )
        else:
            log("Skipping hole closing on mesh input.")

        if settings.smooth_mesh_input:
            smooth_current_mesh(
                ms,
                iterations=settings.mesh_smoothing_iterations,
                log_callback=log,
            )

        source_mesh_index = original_index

    if settings.transfer_texture_to_vertex_colors and source_mesh_index is not None:
        log("Transferring texture/color to vertex colors...")

        try:
            ms.transfer_texture_to_color_per_vertex(
                sourcemesh=source_mesh_index,
                targetmesh=final_mesh_index,
            )
            log("Transferring texture/color to vertex colors done.")
        except Exception as e:
            log(f"Skipping texture/color transfer: {e}")
    else:
        log("Skipping PyMeshLab texture/color transfer.")

    ms.set_current_mesh(final_mesh_index)

    log("Final cleanup...")
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_unreferenced_vertices()
    log("Final cleanup done.")

    if input_is_point_cloud and original_pcd is not None and original_pcd.has_colors():
        _save_current_mesh_with_point_cloud_colors(
            ms=ms,
            output_file=output_file,
            pcd=original_pcd,
            log_callback=log,
        )
        log(f"Saved: {output_file}")
        return

    log("Saving repaired mesh...")
    ms.save_current_mesh(
        output_file,
        save_vertex_color=True,
        save_wedge_texcoord=False,
        save_textures=False,
    )
    log(f"Saved: {output_file}")