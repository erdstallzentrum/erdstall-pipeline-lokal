from pathlib import Path
import shutil

from config import CONVERTED_MESH
from .clear_patches import clear_patches
from .config import FINAL_MESH, ORIGINAL_MESH, PATCHES_DIR, PLY_DIR, REPAIRED_MESH, TEXTURE_DIR, BACKUP_TEXTURE_DIR
from .fill_holes import fill_holes
from .settings.fill_holes_settings import FillHolesSettings
from .find_patches import find_patches, get_patches_json
from .reduce_meshes import reduce_file_size
from .utils import ensure_dir, validate_mesh_id

from collections.abc import Callable

LogCallback = Callable[[str], None] | None


class PipelineError(Exception):
    pass


def mesh_base_dir(mesh_id: str) -> Path:
    validate_mesh_id(mesh_id)
    return Path(PLY_DIR) / mesh_id


def create_project_structure(mesh_id: str) -> Path:
    base = mesh_base_dir(mesh_id)
    ensure_dir(base)
    ensure_dir(base / PATCHES_DIR)
    ensure_dir(base / TEXTURE_DIR)
    ensure_dir(base / BACKUP_TEXTURE_DIR)
    return base


def ply_face_count(path: str |Path) -> int:
    path = Path(path)

    if not path.exists():
        return 0

    try:
        with path.open("rb") as file:
            for raw_line in file:
                line = raw_line.decode("utf-8", errors="ignore").strip()

                if line.startswith("element face"):
                    parts = line.split()
                    if len(parts) >= 3:
                        return int(parts[2])

                if line == "end_header":
                    break
    except Exception as e:
        return 0

    return 0

def is_point_cloud_file(path: str | Path) -> bool:
    return ply_face_count(path) == 0

def is_point_cloud_project(mesh_id: str) -> bool:
    base = mesh_base_dir(mesh_id)
    original = base / ORIGINAL_MESH
    return is_point_cloud_file(original)

def run_fill(
    mesh_id: str,
    settings: FillHolesSettings | None = None,
    log_callback: LogCallback = None,
) -> Path:
    if settings is None:
        settings = FillHolesSettings()

    base = create_project_structure(mesh_id)
    original = base / ORIGINAL_MESH
    converted = base / CONVERTED_MESH
    repaired = base / REPAIRED_MESH

    if is_point_cloud_project(mesh_id):
        if not repaired.exists():
            raise PipelineError(
                "This project is a point cloud. "
                "Run Convert Point Cloud to Mesh before Fill Holes."
            )

        input_mesh = converted
        output_mesh = repaired
    else:
        if not original.exists():
            raise PipelineError(f"Missing input mesh: {original}")

        input_mesh = original
        output_mesh = repaired

    fill_holes(
        str(input_mesh),
        str(output_mesh),
        settings=settings,
        log_callback=log_callback,
    )

    if settings.reduce_size:
        reduce_file_size(
            str(output_mesh),
            initial_mesh_reduction=True,
            compression_percentage=settings.mesh_reduction_percent,
        )

    return output_mesh

def initialize_project(
    mesh_id: str,
    input_mesh: str | Path,
    textures_dir: str | Path | None = None,
) -> Path:
    base = create_project_structure(mesh_id)
    target = base / "original.ply"

    src = Path(input_mesh)
    if not src.exists() or not src.is_file():
        raise PipelineError(f"Input mesh not found: {src}")

    target.write_bytes(src.read_bytes())

    if textures_dir:
        src_textures = Path(textures_dir)
        if not src_textures.exists() or not src_textures.is_dir():
            raise PipelineError(f"Texture folder not found: {src_textures}")

        dst_textures = base / "mesh"
        dst_textures.mkdir(parents=True, exist_ok=True)

        for file in src_textures.iterdir():
            if file.is_file():
                shutil.copy2(file, dst_textures / file.name)

    return base


def run_patch_detection(mesh_id: str, log_callback: LogCallback = None) -> dict:
    def log(message: str) -> None:
        if log_callback is not None:
            log_callback(message)
        else:
            print(message)
    
    base = create_project_structure(mesh_id)
    repaired = base / REPAIRED_MESH
    original = base / ORIGINAL_MESH
    patches_dir = base / PATCHES_DIR

    if not repaired.exists():
        raise PipelineError(f"Missing repaired mesh: {repaired}")
    if not original.exists():
        raise PipelineError(f"Missing original mesh: {original}")
    
    log(f"Starting patch detection for: {mesh_id}")
    log(f"Original mesh: {original}")
    log(f"Repaired mesh: {repaired}")

    find_patches(str(repaired), str(original), str(patches_dir),  log_callback=log,)
    data = get_patches_json(str(base))
    result = data or {"total_patches": 0, "patches": []}

    log(f"Total patches found: {result['total_patches']}")
    return result


def run_finalize(mesh_id: str, unused_patches: list[str] | None = None) -> Path:
    base = create_project_structure(mesh_id)
    repaired = base / REPAIRED_MESH
    final_mesh = base / FINAL_MESH

    if not repaired.exists():
        raise PipelineError(f"Missing repaired mesh: {repaired}")

    if unused_patches:
        clear_patches(str(repaired), str(final_mesh), unused_patches)
    else:
        shutil.copy2(repaired, final_mesh)

    return final_mesh