from __future__ import annotations

from collections.abc import Callable
import os

import numpy as np
import open3d as o3d
from scipy.spatial import cKDTree

from .settings.point_cloud_settings import PointCloudSettings


LogCallback = Callable[[str], None] | None


def _query_tree(
    tree: cKDTree,
    points: np.ndarray,
    k: int = 1,
    workers: int = 1,
) -> tuple[np.ndarray, np.ndarray]:
    try:
        return tree.query(points, k=k, workers=max(1, int(workers)))
    except TypeError:
        return tree.query(points, k=k)


def _thread_count(settings: PointCloudSettings) -> int:
    requested = int(getattr(settings, "poisson_threads", 0))

    if requested > 0:
        return requested

    cpu_count = os.cpu_count() or 2
    return max(1, cpu_count - 1)


def _estimate_average_spacing(
    points: np.ndarray,
    tree: cKDTree,
    log: Callable[[str], None],
    sample_size: int,
) -> float:
    point_count = points.shape[0]

    if point_count < 2:
        raise ValueError("Need at least 2 points to estimate spacing.")

    sample_size = int(sample_size)

    if sample_size <= 0:
        sample_size = min(point_count, 20_000)

    sample_size = min(sample_size, point_count)

    if point_count > sample_size:
        log(
            f"Estimating average spacing from {sample_size:,} / "
            f"{point_count:,} points..."
        )

        rng = np.random.default_rng(seed=42)
        sample_indices = rng.integers(
            low=0,
            high=point_count,
            size=sample_size,
            dtype=np.int64,
        )

        sample_points = np.ascontiguousarray(points[sample_indices])
    else:
        log(f"Estimating average spacing from all {point_count:,} points...")
        sample_points = np.ascontiguousarray(points)

    nearest_distances, _ = _query_tree(tree, sample_points, k=2, workers=1)
    nearest_distances = np.asarray(nearest_distances)

    if nearest_distances.ndim != 2 or nearest_distances.shape[1] < 2:
        raise ValueError("KDTree spacing query failed.")

    valid_distances = nearest_distances[:, 1]
    valid_distances = valid_distances[np.isfinite(valid_distances)]
    valid_distances = valid_distances[valid_distances > 0]

    if valid_distances.size == 0:
        raise ValueError("Could not estimate point spacing.")

    return float(np.median(valid_distances))

def _clean_point_cloud_before_reconstruction(
    pcd: o3d.geometry.PointCloud,
    log: Callable[[str], None],
) -> o3d.geometry.PointCloud:
    log("Cleaning point cloud before reconstruction...")

    before = len(pcd.points)

    try:
        pcd = pcd.remove_non_finite_points()
        log(f"After removing non-finite points: {len(pcd.points):,}")
    except Exception as e:
        log(f"Removing non-finite points skipped: {e}")

    try:
        pcd = pcd.remove_duplicated_points()
        log(f"After removing duplicated points: {len(pcd.points):,}")
    except Exception as e:
        log(f"Removing duplicated points skipped: {e}")

    try:
        pcd, _ = pcd.remove_statistical_outlier(
            nb_neighbors=30,
            std_ratio=1.5,
        )
        log(f"After statistical outlier removal: {len(pcd.points):,}")
    except Exception as e:
        log(f"Statistical outlier removal skipped: {e}")

    after = len(pcd.points)
    removed = before - after

    log(f"Point cloud cleanup removed {removed:,} point(s).")

    if pcd.is_empty():
        raise ValueError("Point cloud became empty after cleanup.")

    return pcd


def _limit_point_count_for_poisson(
    pcd: o3d.geometry.PointCloud,
    max_points: int,
    current_voxel_size: float,
    log: Callable[[str], None],
) -> o3d.geometry.PointCloud:
    if max_points <= 0:
        log("Skipping max point safety limit.")
        return pcd

    point_count = len(pcd.points)

    if point_count <= max_points:
        log(
            f"Point count is within safety limit: "
            f"{point_count:,} / {max_points:,}."
        )
        return pcd

    log(
        f"Point cloud still has {point_count:,} points, "
        f"above safety limit {max_points:,}."
    )

    # Prefer a second voxel pass because it keeps spatial coverage better
    # than random sampling.
    if current_voxel_size > 0:
        factor = (point_count / max_points) ** (1.0 / 3.0)
        safe_voxel_size = current_voxel_size * factor * 1.10

        log(
            f"Applying adaptive extra voxel downsample: "
            f"{safe_voxel_size:.6f}..."
        )

        pcd2 = pcd.voxel_down_sample(voxel_size=safe_voxel_size)

        if not pcd2.is_empty() and len(pcd2.points) < point_count:
            pcd = pcd2
            point_count = len(pcd.points)
            log(f"After adaptive voxel downsample: {point_count:,} points.")

    # Final hard safety fallback.
    if point_count > max_points:
        ratio = max_points / point_count

        log(
            f"Still above safety limit. Randomly reducing with ratio "
            f"{ratio:.4f}..."
        )

        pcd = pcd.random_down_sample(sampling_ratio=ratio)
        log(f"After random safety reduction: {len(pcd.points):,} points.")

    return pcd


def _safe_normal_settings(
    point_count: int,
    avg_spacing: float,
    settings: PointCloudSettings,
    log: Callable[[str], None],
) -> tuple[float, int]:
    requested_radius = avg_spacing * float(settings.normal_radius_factor)

    min_radius = avg_spacing * 1.5
    max_radius = avg_spacing * 6.0

    normal_radius = float(np.clip(requested_radius, min_radius, max_radius))

    requested_max_nn = int(settings.normal_max_nn)

    if point_count > 1_500_000:
        max_nn_cap = 30
    elif point_count > 750_000:
        max_nn_cap = 35
    elif point_count > 250_000:
        max_nn_cap = 40
    else:
        max_nn_cap = 60

    normal_max_nn = max(8, min(requested_max_nn, max_nn_cap))

    if normal_radius != requested_radius:
        log(
            f"Normal radius clamped from {requested_radius:.6f} "
            f"to {normal_radius:.6f}."
        )

    if normal_max_nn != requested_max_nn:
        log(
            f"Normal max neighbors clamped from {requested_max_nn} "
            f"to {normal_max_nn} for {point_count:,} points."
        )

    return normal_radius, normal_max_nn


def _estimate_normals_safely(
    pcd: o3d.geometry.PointCloud,
    normal_radius: float,
    normal_max_nn: int,
    log: Callable[[str], None],
) -> None:
    point_count = len(pcd.points)

    if point_count < 3:
        raise ValueError("Need at least 3 points to estimate normals.")

    log(
        f"Estimating point-cloud normals: "
        f"points={point_count:,}, "
        f"radius={normal_radius:.6f}, "
        f"max_nn={normal_max_nn}..."
    )

    try:
        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamHybrid(
                radius=float(normal_radius),
                max_nn=int(normal_max_nn),
            )
        )
    except RuntimeError as e:
        log(f"Hybrid normal estimation failed: {e}")
        log("Retrying normal estimation with KNN search...")

        pcd.estimate_normals(
            search_param=o3d.geometry.KDTreeSearchParamKNN(
                knn=int(normal_max_nn),
            )
        )

    try:
        pcd.normalize_normals()
    except Exception:
        pass

    log("Normal estimation done.")


def _orient_normals_safely(
    pcd: o3d.geometry.PointCloud,
    settings: PointCloudSettings,
    log: Callable[[str], None],
) -> None:
    if not settings.orient_normals:
        log("Skipping normal orientation.")
        return

    point_count = len(pcd.points)
    requested_k = int(settings.orient_normals_k)

    if point_count > 1_500_000:
        safe_k = min(requested_k, 12)
    elif point_count > 750_000:
        safe_k = min(requested_k, 16)
    elif point_count > 250_000:
        safe_k = min(requested_k, 20)
    else:
        safe_k = requested_k

    safe_k = max(8, safe_k)

    log(f"Orienting normals consistently, k={safe_k}...")

    try:
        pcd.orient_normals_consistent_tangent_plane(safe_k)
        log("Normal orientation done.")
        return
    except Exception as e:
        log(f"Consistent normal orientation failed: {e}")

    log("Trying fallback normal orientation...")

    try:
        bbox = pcd.get_axis_aligned_bounding_box()
        center = bbox.get_center()
        extent = bbox.get_extent()
        camera_location = center + np.array(
            [0.0, 0.0, float(max(extent)) * 2.0],
            dtype=np.float64,
        )

        pcd.orient_normals_towards_camera_location(camera_location)
        log("Fallback normal orientation done.")
    except Exception as fallback_error:
        raise RuntimeError(
            "Normal orientation failed. Poisson reconstruction would likely "
            "produce a bad/blobby mesh. Try lowering Orient Normals K, cleaning "
            "the point cloud, or using Ball Pivoting."
        ) from fallback_error


def _safe_poisson_depth(
    point_count: int,
    requested_depth: int,
    settings: PointCloudSettings,
    log: Callable[[str], None],
) -> int:
    if not getattr(settings, "auto_limit_poisson_depth", True):
        return requested_depth

    if point_count > 1_500_000:
        max_depth = 8
    elif point_count > 750_000:
        max_depth = 9
    elif point_count > 250_000:
        max_depth = 10
    else:
        max_depth = 11

    safe_depth = min(int(requested_depth), max_depth)

    if safe_depth != requested_depth:
        log(
            f"Poisson depth lowered from {requested_depth} to {safe_depth} "
            f"for {point_count:,} points."
        )

    return safe_depth


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

    chunk_size = max(10_000, int(chunk_size))

    log(
        f"Transferring colors to {vertex_count:,} mesh vertices "
        f"in chunks of {chunk_size:,}..."
    )

    for start in range(0, vertex_count, chunk_size):
        end = min(start + chunk_size, vertex_count)

        _, nearest_indices = _query_tree(tree, verts[start:end], k=1, workers=1)
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

    method = getattr(settings, "reconstruction_method", "cave_smooth")

    if method in {"cave_smooth", "cave_realistic"}:
        return _point_cloud_to_mesh_ball_pivoting(
            pcd=pcd,
            settings=settings,
            log_callback=log_callback,
        )

    if method == "poisson":
        return _point_cloud_to_mesh_poisson(
            pcd=pcd,
            settings=settings,
            log_callback=log_callback,
        )

    raise ValueError(f"Unknown reconstruction method: {method}")

def _point_cloud_to_mesh_poisson(
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

    original_count = len(pcd.points)
    log(f"Input point count: {original_count:,}")

    downsample_size = float(settings.downsample_size)

    if downsample_size > 0:
        log(f"Downsampling point cloud with voxel size {downsample_size}...")
        pcd = pcd.voxel_down_sample(voxel_size=downsample_size)
        log(f"After downsampling: {len(pcd.points):,} points.")
    else:
        log("Skipping voxel downsampling. Using full point cloud resolution.")

    pcd = _limit_point_count_for_poisson(
        pcd=pcd,
        max_points=int(getattr(settings, "max_points_for_poisson", 3_000_000)),
        current_voxel_size=downsample_size,
        log=log,
    )

    pcd = _clean_point_cloud_before_reconstruction(pcd, log)

    points = np.asarray(pcd.points, dtype=np.float64)

    if points.size == 0:
        raise ValueError("Point cloud has no points after downsampling.")

    has_colors = pcd.has_colors()
    colors = np.asarray(pcd.colors, dtype=np.float64) if has_colors else None

    point_count = points.shape[0]

    log(f"Point count used for Poisson: {point_count:,}")
    log(f"Has colors: {has_colors}")

    log("Creating KDTree for spacing estimation...")
    tree = cKDTree(points)

    avg_spacing = _estimate_average_spacing(
        points=points,
        tree=tree,
        log=log,
        sample_size=int(settings.spacing_sample_size),
    )

    normal_radius, normal_max_nn = _safe_normal_settings(
        point_count=point_count,
        avg_spacing=avg_spacing,
        settings=settings,
        log=log,
    )

    log(f"Average point spacing: {avg_spacing:.6f}")
    log(f"Normal radius: {normal_radius:.6f}")

    _estimate_normals_safely(
        pcd=pcd,
        normal_radius=normal_radius,
        normal_max_nn=normal_max_nn,
        log=log,
    )

    _orient_normals_safely(
        pcd=pcd,
        settings=settings,
        log=log,
    )

    poisson_depth = _safe_poisson_depth(
        point_count=point_count,
        requested_depth=int(settings.poisson_depth),
        settings=settings,
        log=log,
    )

    thread_count = _thread_count(settings)

    log(
        "Running Open3D Poisson reconstruction: "
        f"depth={poisson_depth}, "
        f"scale={settings.poisson_scale}, "
        f"linear_fit={settings.poisson_linear_fit}, "
        f"threads={thread_count}"
    )

    try:
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd,
            depth=poisson_depth,
            scale=float(settings.poisson_scale),
            linear_fit=bool(settings.poisson_linear_fit),
            n_threads=thread_count,
        )
    except TypeError:
        mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(
            pcd,
            depth=poisson_depth,
            scale=float(settings.poisson_scale),
            linear_fit=bool(settings.poisson_linear_fit),
        )

    log(
        f"Poisson created {len(mesh.vertices):,} vertices "
        f"and {len(mesh.triangles):,} faces."
    )

    density_values = np.asarray(densities)
    density_quantile = float(settings.poisson_density_quantile)

    if density_quantile > 0 and density_values.size > 0:
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

    try:
        log("Cropping Poisson mesh to point cloud bounds...")
        bbox = pcd.get_axis_aligned_bounding_box()
        bbox = bbox.scale(1.02, bbox.get_center())
        mesh = mesh.crop(bbox)
        log(
            f"After bounds crop: {len(mesh.vertices):,} vertices, "
            f"{len(mesh.triangles):,} faces."
        )
    except Exception as e:
        log(f"Bounds crop skipped: {e}")

    mesh = _clean_mesh(mesh, log)

    if int(settings.smoothing_iterations) > 0:
        log(
            f"Applying light Taubin smoothing, "
            f"iterations={settings.smoothing_iterations}..."
        )

        mesh = mesh.filter_smooth_taubin(
            number_of_iterations=int(settings.smoothing_iterations),
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
            chunk_size=int(settings.color_transfer_chunk_size),
        )
    else:
        log("Skipping color transfer: point cloud has no colors.")

    log("Computing vertex normals...")
    mesh.compute_vertex_normals()
    log("Vertex normals computed.")

    return mesh

def _remove_small_mesh_components(
    mesh: o3d.geometry.TriangleMesh,
    log: Callable[[str], None],
    min_triangle_ratio: float = 0.005,
) -> o3d.geometry.TriangleMesh:
    if mesh.is_empty() or len(mesh.triangles) == 0:
        return mesh

    log("Removing small disconnected mesh components...")

    triangle_clusters, cluster_n_triangles, _ = mesh.cluster_connected_triangles()

    triangle_clusters = np.asarray(triangle_clusters)
    cluster_n_triangles = np.asarray(cluster_n_triangles)

    if cluster_n_triangles.size == 0:
        return mesh

    largest_component_size = int(cluster_n_triangles.max())
    min_triangles = max(20, int(largest_component_size * min_triangle_ratio))

    triangles_to_remove = np.zeros(len(mesh.triangles), dtype=bool)

    for cluster_id, triangle_count in enumerate(cluster_n_triangles):
        if triangle_count < min_triangles:
            triangles_to_remove[triangle_clusters == cluster_id] = True

    removed_count = int(np.count_nonzero(triangles_to_remove))

    if removed_count > 0:
        mesh.remove_triangles_by_mask(triangles_to_remove)
        mesh.remove_unreferenced_vertices()

    log(f"Removed {removed_count:,} triangle(s) from small components.")

    return mesh


def _point_cloud_to_mesh_ball_pivoting(
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

    log("Running Cave / Ball Pivoting reconstruction...")
    log(f"Input point count: {len(pcd.points):,}")

    # ------------------------------------------------------------
    # Basic cleanup
    # ------------------------------------------------------------
    try:
        pcd = pcd.remove_non_finite_points()
        log(f"After removing non-finite points: {len(pcd.points):,}")
    except Exception as e:
        log(f"Removing non-finite points skipped: {e}")

    try:
        pcd = pcd.remove_duplicated_points()
        log(f"After removing duplicated points: {len(pcd.points):,}")
    except Exception as e:
        log(f"Removing duplicated points skipped: {e}")

    if pcd.is_empty():
        raise ValueError("Point cloud became empty after basic cleanup.")

    # ------------------------------------------------------------
    # Downsample
    # ------------------------------------------------------------
    downsample_size = float(settings.downsample_size)

    if downsample_size > 0:
        log(f"Downsampling point cloud with voxel size {downsample_size:.6f}...")
        pcd = pcd.voxel_down_sample(voxel_size=downsample_size)
        log(f"After downsampling: {len(pcd.points):,} points.")
    else:
        log("Skipping voxel downsampling.")

    if pcd.is_empty():
        raise ValueError("Point cloud became empty after downsampling.")

    # ------------------------------------------------------------
    # Estimate spacing
    # ------------------------------------------------------------
    points = np.asarray(pcd.points, dtype=np.float64)

    if points.shape[0] < 3:
        raise ValueError("Need at least 3 points for Ball Pivoting.")

    log("Creating KDTree for spacing estimation...")
    tree = cKDTree(points)

    avg_spacing = _estimate_average_spacing(
        points=points,
        tree=tree,
        log=log,
        sample_size=int(settings.spacing_sample_size),
    )

    log(f"Average point spacing: {avg_spacing:.6f}")

    # ------------------------------------------------------------
    # Gentle outlier removal
    # ------------------------------------------------------------
    try:
        radius = avg_spacing * 4.0
        min_neighbors = 6

        log(
            f"Removing radius outliers: "
            f"radius={radius:.6f}, min_neighbors={min_neighbors}..."
        )

        pcd, _ = pcd.remove_radius_outlier(
            nb_points=min_neighbors,
            radius=radius,
        )

        log(f"After radius outlier removal: {len(pcd.points):,}")
    except Exception as e:
        log(f"Radius outlier removal skipped: {e}")

    if pcd.is_empty():
        raise ValueError("Point cloud became empty after outlier removal.")

    points = np.asarray(pcd.points, dtype=np.float64)

    # ------------------------------------------------------------
    # Normals
    # ------------------------------------------------------------
    normal_radius, normal_max_nn = _safe_normal_settings(
        point_count=len(pcd.points),
        avg_spacing=avg_spacing,
        settings=settings,
        log=log,
    )

    _estimate_normals_safely(
        pcd=pcd,
        normal_radius=normal_radius,
        normal_max_nn=normal_max_nn,
        log=log,
    )

    _orient_normals_safely(
        pcd=pcd,
        settings=settings,
        log=log,
    )

    # ------------------------------------------------------------
    # Ball Pivoting
    # ------------------------------------------------------------
    radius_factors = [
        float(getattr(settings, "ball_radius_1", 1.5)),
        float(getattr(settings, "ball_radius_2", 2.5)),
        float(getattr(settings, "ball_radius_3", 4.0)),
        float(getattr(settings, "ball_radius_4", 6.0)),
    ]

    radii = [avg_spacing * factor for factor in radius_factors if factor > 0]

    if not radii:
        raise ValueError("No valid Ball Pivoting radii configured.")

    log(
        "Running Ball Pivoting with radii: "
        + ", ".join(f"{radius:.6f}" for radius in radii)
    )

    mesh = o3d.geometry.TriangleMesh.create_from_point_cloud_ball_pivoting(
        pcd,
        o3d.utility.DoubleVector(radii),
    )

    log(
        f"Ball Pivoting created {len(mesh.vertices):,} vertices "
        f"and {len(mesh.triangles):,} faces."
    )

    if mesh.is_empty():
        raise ValueError("Ball Pivoting produced an empty mesh.")

    mesh = _clean_mesh(mesh, log)

    # ------------------------------------------------------------
    # Remove tiny floating islands
    # ------------------------------------------------------------
    if bool(getattr(settings, "remove_small_components", True)):
        mesh = _remove_small_mesh_components(
            mesh=mesh,
            log=log,
            min_triangle_ratio=float(
                getattr(settings, "min_component_triangle_ratio", 0.005)
            ),
        )
    else:
        log("Skipping small component removal.")

    # ------------------------------------------------------------
    # Optional smoothing
    # ------------------------------------------------------------
    smoothing_iterations = int(getattr(settings, "smoothing_iterations", 0))

    if smoothing_iterations > 0:
        log(f"Applying Taubin smoothing, iterations={smoothing_iterations}...")

        mesh = mesh.filter_smooth_taubin(
            number_of_iterations=smoothing_iterations,
            lambda_filter=0.5,
            mu=-0.53,
        )

        mesh = _clean_mesh(mesh, log)
        log("Taubin smoothing done.")
    else:
        log("Skipping smoothing.")

    # ------------------------------------------------------------
    # Colors
    # ------------------------------------------------------------
    if pcd.has_colors():
        log("Transferring point colors to mesh...")

        points = np.asarray(pcd.points, dtype=np.float64)
        colors = np.asarray(pcd.colors, dtype=np.float64)

        if len(mesh.vertices) == len(points):
            mesh.vertex_colors = o3d.utility.Vector3dVector(colors)
            log("Color transfer done by direct vertex assignment.")
        else:
            _transfer_colors_to_vertices(
                mesh=mesh,
                points=points,
                colors=colors,
                log=log,
                chunk_size=int(settings.color_transfer_chunk_size),
            )
    else:
        log("Skipping color transfer: point cloud has no colors.")

    log("Computing vertex normals...")
    mesh.compute_vertex_normals()
    log("Vertex normals computed.")

    return mesh