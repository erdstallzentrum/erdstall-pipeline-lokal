from __future__ import annotations

from collections.abc import Callable

import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree

from .settings.point_cloud_settings import PointCloudSettings


LogCallback = Callable[[str], None] | None


def _query_tree(
    tree: cKDTree,
    points: np.ndarray,
    k: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    try:
        return tree.query(points, k=k, workers=-1)
    except TypeError:
        return tree.query(points, k=k)


def _estimate_average_spacing(
    points: np.ndarray,
    tree: cKDTree,
    log: Callable[[str], None],
    sample_size: int,
) -> float:
    point_count = points.shape[0]

    if point_count > sample_size:
        log(
            f"Estimating average spacing from {sample_size:,} / "
            f"{point_count:,} points..."
        )

        rng = np.random.default_rng(seed=42)
        sample_indices = rng.choice(point_count, size=sample_size, replace=False)
        sample_points = points[sample_indices]
    else:
        log(f"Estimating average spacing from all {point_count:,} points...")
        sample_points = points

    nearest_distances, _ = _query_tree(tree, sample_points, k=2)

    return float(np.mean(nearest_distances[:, 1]))


def _transfer_colors_to_vertices(
    mesh: o3d.geometry.TriangleMesh,
    points: np.ndarray,
    colors: np.ndarray,
    log: Callable[[str], None],
    chunk_size: int,
) -> None:
    verts = np.asarray(mesh.vertices, dtype=np.float64)

    if verts.size == 0:
        log("Color transfer skipped: mesh has no vertices.")
        return

    tree = cKDTree(points)
    vertex_count = verts.shape[0]
    vertex_colors = np.empty((vertex_count, 3), dtype=np.float64)

    log(f"Transferring colors to {vertex_count:,} mesh vertices...")

    for start in range(0, vertex_count, chunk_size):
        end = min(start + chunk_size, vertex_count)

        _, nearest_indices = _query_tree(tree, verts[start:end], k=1)
        vertex_colors[start:end] = colors[nearest_indices]

        percent = end / vertex_count * 100.0
        log(
            f"Color transfer progress: {end:,} / {vertex_count:,} "
            f"({percent:.1f}%)"
        )

    mesh.vertex_colors = o3d.utility.Vector3dVector(vertex_colors)
    log("Color transfer done.")


def _clean_mesh(
    mesh: o3d.geometry.TriangleMesh,
    log: Callable[[str], None],
) -> o3d.geometry.TriangleMesh:
    log("Cleaning Open3D mesh...")

    mesh.remove_degenerate_triangles()
    mesh.remove_duplicated_triangles()
    mesh.remove_duplicated_vertices()
    mesh.remove_unreferenced_vertices()
    mesh.remove_non_manifold_edges()

    log("Open3D mesh cleanup done.")
    return mesh


def point_cloud_to_mesh(
    pcd: o3d.geometry.PointCloud,
    settings: PointCloudSettings | None = None,
    log_callback: LogCallback = None,
) -> o3d.geometry.TriangleMesh:
    if settings is None:
        settings = PointCloudSettings()

    def log(message: str) -> None:
        if log_callback is not None:
            log_callback(message)
        else:
            print(message)

    if pcd.is_empty():
        raise ValueError("Point cloud is empty.")

    downsample_size = float(settings.downsample_size)

    if downsample_size > 0:
        log(f"Downsampling point cloud with voxel size {downsample_size}...")
        pcd = pcd.voxel_down_sample(voxel_size=downsample_size)
        log(f"After downsampling: {len(pcd.points):,} points.")
    else:
        log("Skipping downsampling. Using full point cloud resolution.")

    points = np.asarray(pcd.points, dtype=np.float64)

    if points.size == 0:
        raise ValueError("Point cloud has no points.")

    has_colors = pcd.has_colors()
    colors = np.asarray(pcd.colors, dtype=np.float64) if has_colors else None

    log(f"Point count used for Poisson: {points.shape[0]:,}")
    log(f"Has colors: {has_colors}")

    log("Creating KDTree for spacing estimation...")
    tree = cKDTree(points)

    avg_spacing = _estimate_average_spacing(
        points=points,
        tree=tree,
        log=log,
        sample_size=settings.spacing_sample_size,
    )

    normal_radius = avg_spacing * settings.normal_radius_factor

    log(f"Average point spacing: {avg_spacing:.6f}")
    log(f"Normal radius: {normal_radius:.6f}")

    log("Estimating point-cloud normals...")
    pcd.estimate_normals(
        search_param=o3d.geometry.KDTreeSearchParamHybrid(
            radius=normal_radius,
            max_nn=settings.normal_max_nn,
        )
    )

    try:
        pcd.normalize_normals()
    except Exception:
        pass

    if settings.orient_normals:
        log(
            "Orienting normals consistently, "
            f"k={settings.orient_normals_k}..."
        )

        try:
            pcd.orient_normals_consistent_tangent_plane(
                settings.orient_normals_k
            )
            log("Normal orientation done.")
        except Exception as e:
            log(f"Normal orientation failed, continuing anyway: {e}")

    log(
        "Running Open3D Poisson reconstruction: "
        f"depth={settings.poisson_depth}, "
        f"scale={settings.poisson_scale}, "
        f"linear_fit={settings.poisson_linear_fit}"
    )

    try:
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd,
            depth=settings.poisson_depth,
            scale=settings.poisson_scale,
            linear_fit=settings.poisson_linear_fit,
            n_threads=-1,
        )
    except TypeError:
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd,
            depth=settings.poisson_depth,
            scale=settings.poisson_scale,
            linear_fit=settings.poisson_linear_fit,
        )

    log(
        f"Poisson created {len(mesh.vertices):,} vertices "
        f"and {len(mesh.triangles):,} faces."
    )

    density_values = np.asarray(densities)
    density_quantile = float(settings.poisson_density_quantile)

    if density_quantile > 0:
        threshold = float(np.quantile(density_values, density_quantile))

        log(
            f"Removing low-density Poisson vertices below quantile "
            f"{density_quantile:.3f}, threshold={threshold:.6f}..."
        )

        vertices_to_remove = density_values < threshold
        mesh.remove_vertices_by_mask(vertices_to_remove)

        log(
            f"After density trim: {len(mesh.vertices):,} vertices, "
            f"{len(mesh.triangles):,} faces."
        )
    else:
        log("Skipping Poisson density trim.")

    mesh = _clean_mesh(mesh, log)

    if settings.smoothing_iterations > 0:
        log(
            f"Applying light Taubin smoothing, "
            f"iterations={settings.smoothing_iterations}..."
        )

        mesh = mesh.filter_smooth_taubin(
            number_of_iterations=settings.smoothing_iterations,
            lambda_filter=0.5,
            mu=-0.53,
        )

        log("Taubin smoothing done.")
        mesh = _clean_mesh(mesh, log)
    else:
        log("Skipping smoothing.")

    if has_colors and colors is not None:
        _transfer_colors_to_vertices(
            mesh=mesh,
            points=points,
            colors=colors,
            log=log,
            chunk_size=max(10_000, int(settings.color_transfer_chunk_size)),
        )
    else:
        log("Skipping color transfer: point cloud has no colors.")

    log("Computing vertex normals...")
    mesh.compute_vertex_normals()
    log("Vertex normals computed.")

    return mesh