from __future__ import annotations

import heapq
import math
from collections import deque
from pathlib import Path

import numpy as np
import vtk
from scipy.ndimage import distance_transform_edt

from .config import (
    FILES_DIR,
    PATH_MESH_FILENAME,
    PATH_OUTPUT_FILENAME,
    PATH_POINTS_FILENAME,
    SIZE,
    SKELETON_VOLUME_FILENAME,
    VOLUME_FILENAME,
)


class PathNotFound(Exception):
    pass


def get_mesh_bounds() -> tuple[float, float, float, float, float, float]:
    mesh_path = Path(FILES_DIR) / PATH_MESH_FILENAME

    reader = vtk.vtkPLYReader()
    reader.SetFileName(str(mesh_path))
    reader.Update()

    mesh = reader.GetOutput()
    if mesh is None or mesh.GetNumberOfPoints() == 0:
        raise RuntimeError(f"Could not read mesh for bounds: {mesh_path}")

    return mesh.GetBounds()


def world_to_voxel(
    x: float,
    y: float,
    z: float,
    bounds: tuple[float, float, float, float, float, float],
    target_size: int = SIZE,
) -> tuple[int, int, int]:
    xmin, xmax, ymin, ymax, zmin, zmax = bounds

    x_range = xmax - xmin
    y_range = ymax - ymin
    z_range = zmax - zmin
    max_dim = max(x_range, y_range, z_range)

    if max_dim == 0:
        raise RuntimeError("Mesh has invalid bounds with zero size")

    scale_factor = (target_size - 2) / max_dim

    center_x = (xmin + xmax) / 2.0
    center_y = (ymin + ymax) / 2.0
    center_z = (zmin + zmax) / 2.0

    vx = int(round((x - center_x) * scale_factor + target_size / 2))
    vy = int(round((y - center_y) * scale_factor + target_size / 2))
    vz = int(round((z - center_z) * scale_factor + target_size / 2))

    return vx, vy, vz


def voxel_to_world(
    vx: int,
    vy: int,
    vz: int,
    bounds: tuple[float, float, float, float, float, float],
    target_size: int = SIZE,
) -> tuple[float, float, float]:
    xmin, xmax, ymin, ymax, zmin, zmax = bounds

    x_range = xmax - xmin
    y_range = ymax - ymin
    z_range = zmax - zmin
    max_dim = max(x_range, y_range, z_range)

    if max_dim == 0:
        raise RuntimeError("Mesh has invalid bounds with zero size")

    scale_factor = (target_size - 2) / max_dim

    center_x = (xmin + xmax) / 2.0
    center_y = (ymin + ymax) / 2.0
    center_z = (zmin + zmax) / 2.0

    x = (vx - target_size / 2) / scale_factor + center_x
    y = (vy - target_size / 2) / scale_factor + center_y
    z = (vz - target_size / 2) / scale_factor + center_z

    return x, y, z


def read_points() -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    path = Path(FILES_DIR) / PATH_POINTS_FILENAME

    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    if len(lines) < 2:
        raise RuntimeError("path_points.csv must contain a header and one data row")

    values = list(map(float, lines[1].strip().split(",")))
    if len(values) != 6:
        raise RuntimeError("path_points.csv must contain 6 numeric values")

    start_x, start_y, start_z, end_x, end_y, end_z = values
    bounds = get_mesh_bounds()

    start_vx, start_vy, start_vz = world_to_voxel(start_x, start_y, start_z, bounds)
    end_vx, end_vy, end_vz = world_to_voxel(end_x, end_y, end_z, bounds)

    print(f"MeshLab start: {(start_x, start_y, start_z)} -> voxel: {(start_vx, start_vy, start_vz)}")
    print(f"MeshLab end: {(end_x, end_y, end_z)} -> voxel: {(end_vx, end_vy, end_vz)}")

    start = (start_vz, start_vy, start_vx)
    end = (end_vz, end_vy, end_vx)

    return start, end


def build_shifts(connectivity: int) -> list[tuple[int, int, int]]:
    if connectivity not in (6, 18, 26):
        raise ValueError(f"Unsupported connectivity: {connectivity}")

    shifts: list[tuple[int, int, int]] = []

    for dz in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dz == 0 and dy == 0 and dx == 0:
                    continue

                manhattan = abs(dz) + abs(dy) + abs(dx)

                if connectivity == 6 and manhattan == 1:
                    shifts.append((dz, dy, dx))
                elif connectivity == 18 and manhattan <= 2:
                    shifts.append((dz, dy, dx))
                elif connectivity == 26:
                    shifts.append((dz, dy, dx))

    return shifts


def snap_to_nearest_skeleton(
    mask: np.ndarray,
    point: tuple[int, int, int],
    max_radius: int = 15,
) -> tuple[int, int, int]:
    z0, y0, x0 = point
    best: tuple[int, int, int] | None = None
    best_dist = float("inf")

    z_min = max(0, z0 - max_radius)
    z_max = min(mask.shape[0], z0 + max_radius + 1)
    y_min = max(0, y0 - max_radius)
    y_max = min(mask.shape[1], y0 + max_radius + 1)
    x_min = max(0, x0 - max_radius)
    x_max = min(mask.shape[2], x0 + max_radius + 1)

    for z in range(z_min, z_max):
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                if mask[z, y, x]:
                    dist = (z - z0) ** 2 + (y - y0) ** 2 + (x - x0) ** 2
                    if dist < best_dist:
                        best_dist = dist
                        best = (z, y, x)

    if best is None:
        raise RuntimeError(f"No skeleton voxel found near point {point}")

    print(f"Snapped {point} -> {best} (distance^2={best_dist})")
    return best


def snap_to_nearest_in_component(
    mask: np.ndarray,
    labels: np.ndarray,
    point: tuple[int, int, int],
    component_label: int,
    max_radius: int = 40,
) -> tuple[int, int, int] | None:
    z0, y0, x0 = point
    best: tuple[int, int, int] | None = None
    best_dist = float("inf")

    z_min = max(0, z0 - max_radius)
    z_max = min(mask.shape[0], z0 + max_radius + 1)
    y_min = max(0, y0 - max_radius)
    y_max = min(mask.shape[1], y0 + max_radius + 1)
    x_min = max(0, x0 - max_radius)
    x_max = min(mask.shape[2], x0 + max_radius + 1)

    for z in range(z_min, z_max):
        for y in range(y_min, y_max):
            for x in range(x_min, x_max):
                if mask[z, y, x] and labels[z, y, x] == component_label:
                    dist = (z - z0) ** 2 + (y - y0) ** 2 + (x - x0) ** 2
                    if dist < best_dist:
                        best_dist = dist
                        best = (z, y, x)

    if best is not None:
        print(
            f"Snapped {point} -> {best} inside component {component_label} "
            f"(distance^2={best_dist})"
        )

    return best


def label_connected_components(
    mask: np.ndarray,
    shifts: list[tuple[int, int, int]],
) -> tuple[np.ndarray, list[list[tuple[int, int, int]]]]:
    labels = np.full(mask.shape, -1, dtype=np.int32)
    components: list[list[tuple[int, int, int]]] = []
    current_label = 0
    z_size, y_size, x_size = mask.shape

    def in_bounds(z: int, y: int, x: int) -> bool:
        return 0 <= z < z_size and 0 <= y < y_size and 0 <= x < x_size

    for z0, y0, x0 in np.argwhere(mask):
        if labels[z0, y0, x0] != -1:
            continue

        q = deque([(z0, y0, x0)])
        labels[z0, y0, x0] = current_label
        component_coords: list[tuple[int, int, int]] = []

        while q:
            z, y, x = q.popleft()
            component_coords.append((z, y, x))

            for dz, dy, dx in shifts:
                nz, ny, nx = z + dz, y + dy, x + dx
                if in_bounds(nz, ny, nx) and mask[nz, ny, nx] and labels[nz, ny, nx] == -1:
                    labels[nz, ny, nx] = current_label
                    q.append((nz, ny, nx))

        components.append(component_coords)
        current_label += 1

    return labels, components


def normalize(vec: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2)
    if length == 0:
        return 0.0, 0.0, 0.0
    return vec[0] / length, vec[1] / length, vec[2] / length


def dijkstra_path(
    skeleton_mask: np.ndarray,
    volume_mask: np.ndarray,
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    shifts: list[tuple[int, int, int]],
) -> list[tuple[int, int, int]]:
    z_size, y_size, x_size = skeleton_mask.shape

    def in_bounds(z: int, y: int, x: int) -> bool:
        return 0 <= z < z_size and 0 <= y < y_size and 0 <= x < x_size

    def neighbors(z: int, y: int, x: int):
        for dz, dy, dx in shifts:
            nz, ny, nx = z + dz, y + dy, x + dx
            if in_bounds(nz, ny, nx) and skeleton_mask[nz, ny, nx]:
                yield (nz, ny, nx)

    distance_map = distance_transform_edt(volume_mask)

    pq: list[tuple[float, tuple[int, int, int]]] = [(0.0, start)]
    dist: dict[tuple[int, int, int], float] = {start: 0.0}
    prev: dict[tuple[int, int, int], tuple[int, int, int] | None] = {start: None}

    while pq:
        current_cost, current = heapq.heappop(pq)

        if current == end:
            break

        if current_cost > dist[current]:
            continue

        cz, cy, cx = current

        for n in neighbors(*current):
            nz, ny, nx = n
            dz = nz - cz
            dy = ny - cy
            dx = nx - cx

            wall_dist = float(distance_map[nz, ny, nx])

            # Hard reject very thin / wall-touching connections
            if wall_dist < 2.0:
                continue

            changed_axes = int(dz != 0) + int(dy != 0) + int(dx != 0)

            if changed_axes == 1:
                step_cost = 1.0
            elif changed_axes == 2:
                step_cost = 8.0
            else:
                step_cost = 20.0

            direction_penalty = 0.0

            if wall_dist <= 0.0:
                wall_penalty = 1_000_000.0
            else:
                wall_penalty = 40.0 / (wall_dist * wall_dist)

            degree = 0
            for _ in neighbors(nz, ny, nx):
                degree += 1
            branch_penalty = max(0, degree - 2) * 0.3

            new_cost = (
                current_cost
                + step_cost
                + direction_penalty
                + wall_penalty
                + branch_penalty
            )

            if n not in dist or new_cost < dist[n]:
                dist[n] = new_cost
                prev[n] = current
                heapq.heappush(pq, (new_cost, n))

    if end not in prev:
        raise PathNotFound("No path found between start and end")

    path: list[tuple[int, int, int]] = []
    current: tuple[int, int, int] | None = end

    while current is not None:
        path.append(current)
        current = prev[current]

    path.reverse()
    return path


def smooth_path(path: list[tuple[int, int, int]], iterations: int = 2) -> list[tuple[int, int, int]]:
    if len(path) < 3:
        return path

    arr = np.array(path, dtype=np.float64)

    for _ in range(iterations):
        new_arr = arr.copy()
        for i in range(1, len(arr) - 1):
            new_arr[i] = (arr[i - 1] + arr[i] + arr[i + 1]) / 3.0
        arr = new_arr

    smoothed: list[tuple[int, int, int]] = []
    for p in arr:
        smoothed.append((int(round(p[0])), int(round(p[1])), int(round(p[2]))))

    deduped: list[tuple[int, int, int]] = []
    for p in smoothed:
        if not deduped or deduped[-1] != p:
            deduped.append(p)

    return deduped


def try_path_with_connectivity(
    skeleton_mask: np.ndarray,
    volume_mask: np.ndarray,
    requested_start: tuple[int, int, int],
    requested_end: tuple[int, int, int],
    connectivity: int,
) -> list[tuple[int, int, int]] | None:
    print(f"Trying path search with {connectivity}-connectivity")
    shifts = build_shifts(connectivity)

    labels, components = label_connected_components(skeleton_mask, shifts)
    sizes = sorted((len(c) for c in components), reverse=True)
    print(f"Connected components: {len(components)}")
    print(f"Largest components: {sizes[:10]}")

    start = snap_to_nearest_skeleton(skeleton_mask, requested_start, max_radius=15)
    print(f"Snapped start to: {start}")

    start_label = labels[start]
    if start_label < 0:
        print("Start did not land on a valid component")
        return None

    print(f"Start component: {start_label}, size={len(components[start_label])}")

    end_same_component = snap_to_nearest_in_component(
        mask=skeleton_mask,
        labels=labels,
        point=requested_end,
        component_label=start_label,
        max_radius=40,
    )

    if end_same_component is None:
        print(
            f"End point is not near the same component as start "
            f"for {connectivity}-connectivity"
        )
        return None

    end = end_same_component
    print(f"Snapped end to: {end}")

    try:
        path = dijkstra_path(skeleton_mask, volume_mask, start, end, shifts)
        print(f"Weighted path found with {connectivity}-connectivity, length={len(path)}")
        return path
    except PathNotFound:
        print(f"No path found with {connectivity}-connectivity")
        return None


def compute_skeleton_csv() -> str:
    skeleton_raw_path = Path(FILES_DIR) / SKELETON_VOLUME_FILENAME
    volume_raw_path = Path(FILES_DIR) / VOLUME_FILENAME

    skeleton_vol = np.fromfile(str(skeleton_raw_path), dtype=np.uint8)
    volume_vol = np.fromfile(str(volume_raw_path), dtype=np.uint8)

    expected_size = SIZE * SIZE * SIZE

    if skeleton_vol.size != expected_size:
        raise RuntimeError(
            f"Invalid skeleton volume size: got {skeleton_vol.size}, expected {expected_size}"
        )

    if volume_vol.size != expected_size:
        raise RuntimeError(
            f"Invalid volume size: got {volume_vol.size}, expected {expected_size}"
        )

    skeleton_vol = skeleton_vol.reshape((SIZE, SIZE, SIZE))
    volume_vol = volume_vol.reshape((SIZE, SIZE, SIZE))

    skeleton_mask = skeleton_vol == 255
    volume_mask = volume_vol > 0

    distance_map = distance_transform_edt(volume_mask)

    min_radius = 2.0  # try 2.0 first, maybe 2.5 or 3.0 later
    pruned_skeleton_mask = skeleton_mask & (distance_map >= min_radius)

    print(f"Original skeleton voxels: {int(skeleton_mask.sum())}")
    print(f"Pruned skeleton voxels:   {int(pruned_skeleton_mask.sum())}")

    skeleton_mask = pruned_skeleton_mask

    if not np.any(skeleton_mask):
        raise RuntimeError("Skeleton is empty")

    if not np.any(volume_mask):
        raise RuntimeError("Volume is empty")

    requested_start, requested_end = read_points()

    coords = np.argwhere(skeleton_mask)
    zmin, ymin, xmin = coords.min(axis=0)
    zmax, ymax, xmax = coords.max(axis=0)

    print(f"Skeleton bounds z:{zmin}-{zmax}, y:{ymin}-{ymax}, x:{xmin}-{xmax}")
    print(f"Requested start: {requested_start}, end: {requested_end}")
    print(f"Skeleton voxel count: {int(skeleton_mask.sum())}")
    print(f"Volume voxel count: {int(volume_mask.sum())}")

    def in_bounds(z: int, y: int, x: int) -> bool:
        return 0 <= z < SIZE and 0 <= y < SIZE and 0 <= x < SIZE

    if not in_bounds(*requested_start):
        raise RuntimeError(f"Start point out of bounds: {requested_start}")
    if not in_bounds(*requested_end):
        raise RuntimeError(f"End point out of bounds: {requested_end}")

    path: list[tuple[int, int, int]] | None = None
    used_connectivity: int | None = None

    for connectivity in (18, 26):
        path = try_path_with_connectivity(
            skeleton_mask=skeleton_mask,
            volume_mask=volume_mask,
            requested_start=requested_start,
            requested_end=requested_end,
            connectivity=connectivity,
        )
        if path is not None:
            used_connectivity = connectivity
            break

    if path is None or used_connectivity is None:
        raise PathNotFound("No path found between start and end")

     # path = smooth_path(path, iterations=2)

    print(f"Final path found with {used_connectivity}-connectivity, length={len(path)}")

    out_csv = Path(FILES_DIR) / PATH_OUTPUT_FILENAME
    bounds = get_mesh_bounds()

    lines = ["point_id;x;y;z;prev_point_id;next_point_id"]
    for i, (z, y, x) in enumerate(path):
        world_x, world_y, world_z = voxel_to_world(x, y, z, bounds)

        prev_id = str(i - 1) if i > 0 else ""
        next_id = str(i + 1) if i < len(path) - 1 else ""

        lines.append(f"{i};{world_x};{world_y};{world_z};{prev_id};{next_id}")

    with out_csv.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(out_csv)