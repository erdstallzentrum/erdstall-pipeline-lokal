from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pymeshlab

from .settings.fill_holes_settings import FillHolesSettings


LogCallback = Callable[[str], None] | None


def _mesh_count(ms: pymeshlab.MeshSet) -> int:
    if hasattr(ms, "mesh_number"):
        return ms.mesh_number()
    return ms.number_meshes()


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


def close_mesh_holes_below_top_percent(
    ms: pymeshlab.MeshSet,
    top_ignore_percent: float,
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

    if vertices.size == 0 or faces.size == 0:
        log("Selective hole closing skipped: mesh has no vertices or faces.")
        return _mesh_count(ms) - 1

    top_ignore_percent = max(0.0, min(1.0, float(top_ignore_percent)))

    min_z = float(vertices[:, 2].min())
    max_z = float(vertices[:, 2].max())
    height = max_z - min_z

    if height <= 0:
        log("Selective hole closing skipped: invalid model height.")
        return _mesh_count(ms) - 1

    z_cutoff = max_z - height * top_ignore_percent

    log(
        f"Selective mesh hole closing. "
        f"Ignoring top {top_ignore_percent * 100:.1f}% of model. "
        f"min_z={min_z:.6f}, max_z={max_z:.6f}, cutoff_z={z_cutoff:.6f}"
    )

    edge_count: dict[tuple[int, int], int] = {}

    for face in faces:
        a = int(face[0])
        b = int(face[1])
        c = int(face[2])

        for u, v in ((a, b), (b, c), (c, a)):
            edge = (min(u, v), max(u, v))
            edge_count[edge] = edge_count.get(edge, 0) + 1

    boundary_edges = [edge for edge, count in edge_count.items() if count == 1]

    if not boundary_edges:
        log("No boundary edges found. No holes to close.")
        return _mesh_count(ms) - 1

    adjacency: dict[int, list[int]] = {}

    for u, v in boundary_edges:
        adjacency.setdefault(u, []).append(v)
        adjacency.setdefault(v, []).append(u)

    visited_edges: set[tuple[int, int]] = set()
    loops: list[list[int]] = []

    for start_u, start_v in boundary_edges:
        start_edge = (min(start_u, start_v), max(start_u, start_v))

        if start_edge in visited_edges:
            continue

        loop = [start_u]
        prev = start_u
        current = start_v

        visited_edges.add(start_edge)

        for _ in range(len(boundary_edges) + 10):
            loop.append(current)

            if current == start_u:
                break

            next_vertex = None

            for candidate in adjacency.get(current, []):
                if candidate == prev:
                    continue

                candidate_edge = (min(current, candidate), max(current, candidate))

                if candidate_edge not in visited_edges:
                    next_vertex = candidate
                    break

            if next_vertex is None:
                break

            visited_edges.add((min(current, next_vertex), max(current, next_vertex)))
            prev, current = current, next_vertex

        if len(loop) >= 4 and loop[0] == loop[-1]:
            loops.append(loop[:-1])

    if not loops:
        log("No valid closed boundary loops found.")
        return _mesh_count(ms) - 1

    center_vertices: list[np.ndarray] = []
    new_faces: list[list[int]] = []
    center_colors: list[np.ndarray] = []

    use_colors = False
    vertex_colors = None

    try:
        vertex_colors = mesh.vertex_color_matrix()
        if vertex_colors is not None and len(vertex_colors) == len(vertices):
            use_colors = True
    except Exception:
        use_colors = False
        vertex_colors = None

    closed_count = 0
    skipped_top_count = 0
    skipped_invalid_count = 0
    created_faces = 0

    for loop in loops:
        if len(loop) < 3:
            skipped_invalid_count += 1
            continue

        loop_array = np.asarray(loop, dtype=np.int64)
        loop_vertices = vertices[loop_array]

        hole_max_z = float(loop_vertices[:, 2].max())

        if hole_max_z > z_cutoff:
            skipped_top_count += 1
            continue

        center = loop_vertices.mean(axis=0)
        center_index = len(vertices) + len(center_vertices)
        center_vertices.append(center)

        if use_colors and vertex_colors is not None:
            center_colors.append(vertex_colors[loop_array].mean(axis=0))

        for index in range(len(loop)):
            a = int(loop[index])
            b = int(loop[(index + 1) % len(loop)])
            new_faces.append([center_index, a, b])
            created_faces += 1

        closed_count += 1

    if closed_count == 0:
        log(
            f"No holes closed. Found {len(loops):,} boundary loop(s). "
            f"Skipped top-zone holes: {skipped_top_count:,}. "
            f"Skipped invalid holes: {skipped_invalid_count:,}."
        )
        return _mesh_count(ms) - 1

    center_vertices_array = np.asarray(center_vertices, dtype=vertices.dtype)
    new_faces_array = np.asarray(new_faces, dtype=faces.dtype)

    final_vertices = np.vstack((vertices, center_vertices_array))
    final_faces = np.vstack((faces, new_faces_array))

    if use_colors and vertex_colors is not None:
        center_colors_array = np.asarray(center_colors, dtype=vertex_colors.dtype)
        final_colors = np.vstack((vertex_colors, center_colors_array))

        closed_mesh = pymeshlab.Mesh(
            vertex_matrix=final_vertices,
            face_matrix=final_faces,
            v_color_matrix=final_colors,
        )
    else:
        closed_mesh = pymeshlab.Mesh(
            vertex_matrix=final_vertices,
            face_matrix=final_faces,
        )

    ms.add_mesh(closed_mesh, "mesh_holes_closed_below_top_percent")

    closed_index = _mesh_count(ms) - 1
    ms.set_current_mesh(closed_index)

    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_unreferenced_vertices()

    try:
        ms.compute_normal_per_face()
        ms.compute_normal_per_vertex()
    except Exception as e:
        log(f"Normal recompute after selective hole closing skipped: {e}")

    log(
        f"Closed {closed_count:,} hole(s) below cutoff. "
        f"Skipped {skipped_top_count:,} hole(s) in top zone. "
        f"Created {created_faces:,} face(s)."
    )

    return closed_index


def fill_holes(
    input_file: str | Path,
    output_file: str | Path,
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

    input_path = Path(input_file)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if input_path.resolve() == output_path.resolve():
        temp_output_path = output_path.with_name(output_path.stem + "_tmp_fill.ply")
    else:
        temp_output_path = output_path

    ms = pymeshlab.MeshSet()

    log("Loading mesh...")
    ms.load_new_mesh(str(input_path))
    log("Loading mesh done.")

    original_index = 0
    original_mesh = ms.mesh(original_index)

    if original_mesh.face_number() == 0:
        raise ValueError(
            "Fill Holes received a point cloud, not a mesh. "
            "Run Convert Point Cloud to Mesh first."
        )

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
    final_mesh_index = keep_largest_connected_component(
        ms,
        log_callback=log,
    )
    ms.set_current_mesh(final_mesh_index)
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

    if settings.close_holes_on_mesh_input:
        final_mesh_index = close_mesh_holes_below_top_percent(
            ms,
            top_ignore_percent=settings.close_hole_under_percent,
            log_callback=log,
        )
        ms.set_current_mesh(final_mesh_index)
    else:
        log("Skipping hole closing on mesh input.")

    if settings.smooth_mesh_input:
        smooth_current_mesh(
            ms,
            iterations=settings.mesh_smoothing_iterations,
            log_callback=log,
        )

    if settings.transfer_texture_to_vertex_colors:
        log("Transferring texture/color to vertex colors...")

        try:
            ms.transfer_texture_to_color_per_vertex(
                sourcemesh=original_index,
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

    log("Saving repaired mesh...")
    ms.save_current_mesh(
        str(temp_output_path),
        save_vertex_color=True,
        save_wedge_texcoord=False,
        save_textures=False,
    )

    if temp_output_path != output_path:
        temp_output_path.replace(output_path)

    log(f"Saved: {output_path}")