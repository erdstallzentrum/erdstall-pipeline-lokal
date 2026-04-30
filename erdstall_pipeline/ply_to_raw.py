from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import vtk
from scipy.ndimage import binary_fill_holes
from vtkmodules.util import numpy_support

from .config import FILES_DIR, RAW_FROM_PLY_FILENAME, SIZE


def center_and_scale_mesh(mesh, target_size: int = SIZE):
    print("[PLY2RAW] center_and_scale_mesh: start")

    bounds = mesh.GetBounds()
    x_range = bounds[1] - bounds[0]
    y_range = bounds[3] - bounds[2]
    z_range = bounds[5] - bounds[4]

    max_dim = max(x_range, y_range, z_range)
    if max_dim == 0:
        raise ValueError("Mesh has invalid bounds with zero size.")

    scale_factor = (target_size - 2) / max_dim

    center_x = (bounds[0] + bounds[1]) / 2.0
    center_y = (bounds[2] + bounds[3]) / 2.0
    center_z = (bounds[4] + bounds[5]) / 2.0

    points = mesh.GetPoints()
    if points is None:
        raise RuntimeError("Mesh has no points")

    new_points = vtk.vtkPoints()
    new_points.SetNumberOfPoints(points.GetNumberOfPoints())

    half = target_size / 2.0

    for i in range(points.GetNumberOfPoints()):
        x, y, z = points.GetPoint(i)

        nx = (x - center_x) * scale_factor + half
        ny = (y - center_y) * scale_factor + half
        nz = (z - center_z) * scale_factor + half

        new_points.SetPoint(i, nx, ny, nz)

    out_mesh = vtk.vtkPolyData()
    out_mesh.DeepCopy(mesh)
    out_mesh.SetPoints(new_points)

    out_bounds = out_mesh.GetBounds()

    print(f"[PLY2RAW] original bounds: {bounds}")
    print(f"[PLY2RAW] scaled bounds:   {out_bounds}")
    print(f"[PLY2RAW] scale_factor:    {scale_factor}")
    print("[PLY2RAW] center_and_scale_mesh: done")

    return out_mesh


def vtk_image_to_numpy(image) -> np.ndarray:
    dims = image.GetDimensions()
    scalars = image.GetPointData().GetScalars()

    if scalars is None:
        raise RuntimeError("VTK image has no scalar data")

    np_array = numpy_support.vtk_to_numpy(scalars)
    np_array = np_array.reshape((dims[2], dims[1], dims[0]))

    return np_array


def fill_holes_cropped(binary_array: np.ndarray) -> np.ndarray:
    coords = np.argwhere(binary_array)
    if coords.size == 0:
        return binary_array

    zmin, ymin, xmin = coords.min(axis=0)
    zmax, ymax, xmax = coords.max(axis=0)

    pad = 2
    zmin = max(0, zmin - pad)
    ymin = max(0, ymin - pad)
    xmin = max(0, xmin - pad)
    zmax = min(binary_array.shape[0] - 1, zmax + pad)
    ymax = min(binary_array.shape[1] - 1, ymax + pad)
    xmax = min(binary_array.shape[2] - 1, xmax + pad)

    cropped = binary_array[zmin:zmax + 1, ymin:ymax + 1, xmin:xmax + 1]
    filled = binary_fill_holes(cropped).astype(np.uint8)

    result = np.zeros_like(binary_array, dtype=np.uint8)
    result[zmin:zmax + 1, ymin:ymax + 1, xmin:xmax + 1] = filled

    return result


def debug_array_stats(name: str, arr: np.ndarray) -> None:
    nonzero = int(np.count_nonzero(arr))
    total = int(arr.size)

    if total == 0:
        print(f"[PLY2RAW] {name}: empty array")
        return

    arr_min = float(arr.min())
    arr_max = float(arr.max())
    arr_mean = float(arr.mean())

    print(
        f"[PLY2RAW] {name}: "
        f"shape={arr.shape}, dtype={arr.dtype}, "
        f"min={arr_min}, max={arr_max}, mean={arr_mean}, "
        f"nonzero={nonzero}/{total}"
    )


def write_raw_uint8_255(binary_array: np.ndarray) -> None:
    out_path = FILES_DIR / RAW_FROM_PLY_FILENAME
    out_data = (binary_array.astype(np.uint8) * 255).astype(np.uint8)
    out_data.tofile(out_path)

    written_bytes = out_path.stat().st_size
    expected_bytes = SIZE * SIZE * SIZE

    print(f"[PLY2RAW] wrote raw file: {out_path}")
    print(f"[PLY2RAW] raw file size:  {written_bytes} bytes (expected {expected_bytes})")


def convert_mesh_to_voxels_via_voxelmodeller(
    mesh,
    image_size: int = SIZE,
    write_raw: bool = True,
):
    print("[PLY2RAW] voxelmodeller fallback: start")

    voxelmodeller = vtk.vtkVoxelModeller()
    voxelmodeller.SetSampleDimensions(image_size, image_size, image_size)
    voxelmodeller.SetModelBounds(0, image_size, 0, image_size, 0, image_size)

    # Use float here. Unsigned char can quantize away useful values.
    voxelmodeller.SetScalarTypeToFloat()

    # 0.1 may be too strict for some meshes; 1.0 is a safer default for debugging.
    voxelmodeller.SetMaximumDistance(1.0)
    voxelmodeller.SetInputData(mesh)
    voxelmodeller.Update()

    np_array = vtk_image_to_numpy(voxelmodeller.GetOutput())
    debug_array_stats("voxelmodeller raw", np_array)

    binary_array = (np_array > 0).astype(np.uint8)
    debug_array_stats("voxelmodeller binary", binary_array)

    t_fill = time.time()
    filled_array = fill_holes_cropped(binary_array)
    print(f"[PLY2RAW] voxelmodeller fill_holes_cropped took {time.time() - t_fill:.2f}s")
    debug_array_stats("voxelmodeller filled", filled_array)

    if np.count_nonzero(filled_array) == 0:
        raise RuntimeError(
            "VoxelModeller fallback produced an empty volume. "
            "Try increasing SetMaximumDistance further or reducing mesh reduction."
        )

    if write_raw:
        write_raw_uint8_255(filled_array)

    print("[PLY2RAW] voxelmodeller fallback: done")
    return filled_array


def mesh_to_image(import_mesh, image_size: int = SIZE, write_raw: bool = True):
    print("[PLY2RAW] mesh_to_image: start")

    extent = (0, image_size - 1, 0, image_size - 1, 0, image_size - 1)
    mesh = center_and_scale_mesh(import_mesh, image_size)

    print("[PLY2RAW] stencil: start")
    stencil = vtk.vtkPolyDataToImageStencil()
    stencil.SetInputData(mesh)
    stencil.SetOutputSpacing(1, 1, 1)
    stencil.SetOutputOrigin(0, 0, 0)
    stencil.SetOutputWholeExtent(*extent)
    stencil.Update()
    print("[PLY2RAW] stencil: done")

    white_image = vtk.vtkImageData()
    white_image.SetSpacing(1, 1, 1)
    white_image.SetOrigin(0, 0, 0)
    white_image.SetExtent(*extent)
    white_image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)

    scalars = white_image.GetPointData().GetScalars()
    if scalars is None:
        raise RuntimeError("white_image has no scalar buffer")

    np_white = numpy_support.vtk_to_numpy(scalars)
    np_white[:] = 255

    print("[PLY2RAW] stencil_to_image: start")
    stencil_to_image = vtk.vtkImageStencil()
    stencil_to_image.SetInputData(white_image)
    stencil_to_image.SetStencilData(stencil.GetOutput())
    stencil_to_image.ReverseStencilOff()
    stencil_to_image.SetBackgroundValue(0)
    stencil_to_image.Update()
    print("[PLY2RAW] stencil_to_image: done")

    np_array = vtk_image_to_numpy(stencil_to_image.GetOutput())
    debug_array_stats("stencil raw", np_array)

    if not np.any(np_array):
        print("[PLY2RAW] stencil result empty, switching to voxelmodeller fallback")
        return convert_mesh_to_voxels_via_voxelmodeller(
            mesh,
            image_size=image_size,
            write_raw=write_raw,
        )

    binary_array = (np_array > 0).astype(np.uint8)
    debug_array_stats("stencil binary", binary_array)

    t_fill = time.time()
    filled_array = fill_holes_cropped(binary_array)
    print(f"[PLY2RAW] fill_holes_cropped took {time.time() - t_fill:.2f}s")
    debug_array_stats("stencil filled", filled_array)

    if np.count_nonzero(filled_array) == 0:
        print("[PLY2RAW] stencil filled volume empty, switching to voxelmodeller fallback")
        return convert_mesh_to_voxels_via_voxelmodeller(
            mesh,
            image_size=image_size,
            write_raw=write_raw,
        )

    if write_raw:
        write_raw_uint8_255(filled_array)

    print("[PLY2RAW] mesh_to_image: done")
    return filled_array


def convert_ply_to_raw(mesh_path: str | Path):

    mesh_path = Path(mesh_path)
    print(f"[PLY2RAW] convert_ply_to_raw: start -> {mesh_path}")
    t0 = time.time()

    reader = vtk.vtkPLYReader()
    reader.SetFileName(str(mesh_path))

    print("[PLY2RAW] reader.Update(): start")
    reader.Update()
    print("[PLY2RAW] reader.Update(): done")

    mesh = reader.GetOutput()
    if mesh is None or mesh.GetNumberOfPoints() == 0:
        raise ValueError(f"Could not read a valid mesh from: {mesh_path}")

    print(f"[PLY2RAW] mesh points: {mesh.GetNumberOfPoints()}")
    print(f"[PLY2RAW] mesh polys:  {mesh.GetNumberOfPolys()}")
    print(f"[PLY2RAW] mesh bounds: {mesh.GetBounds()}")

    result = mesh_to_image(mesh, image_size=SIZE, write_raw=True)

    nonzero = int(np.count_nonzero(result))
    if nonzero == 0:
        raise RuntimeError("PLY to RAW conversion produced an empty volume")

    print(f"[PLY2RAW] final volume nonzero voxels: {nonzero}")
    print(f"[PLY2RAW] convert_ply_to_raw: done in {time.time() - t0:.2f}s")