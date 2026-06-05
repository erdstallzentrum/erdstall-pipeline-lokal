import shutil
from pathlib import Path
from erdstall_pipeline.config import CONVERTED_MESH
from erdstall_pipeline.config import FINAL_MESH, ORIGINAL_MESH, PLY_DIR, REPAIRED_MESH, TEXTURE_DIR, BACKUP_TEXTURE_DIR
from erdstall_pipeline.fill_holes import fill_holes
from erdstall_pipeline.settings.fill_holes_settings import FillHolesSettings
from erdstall_pipeline.reduce_meshes import reduce_file_size
from erdstall_pipeline.utils.validations import ensure_dir, validate_mesh_id

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
    ensure_dir(base / TEXTURE_DIR)
    ensure_dir(base / BACKUP_TEXTURE_DIR)
    return base


def ply_face_count(path: str |Path) -> int:
    p = Path(path)

    if not p.exists():
        return 0

    try:
        with p.open("rb") as file:
            for raw_line in file:
                line = raw_line.decode("utf-8", errors="ignore").strip()

                if line.startswith("element face"):
                    parts = line.split()
                    if len(parts) >= 3:
                        return int(parts[2])

                if line == "end_header":
                    break
    except OSError:
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
    active_settings = settings if settings is not None else FillHolesSettings()
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
        settings=active_settings,
        log_callback=log_callback,
    )

    if active_settings.reduce_size:
        reduce_file_size(
            str(output_mesh),
            initial_mesh_reduction=True,
            compression_percentage=active_settings.mesh_reduction_percent,
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



def run_finalize(mesh_id: str) -> Path:
    base = create_project_structure(mesh_id)
    repaired = base / REPAIRED_MESH
    final_mesh = base / FINAL_MESH

    if not repaired.exists():
        raise PipelineError(f"Missing repaired mesh: {repaired}")

    shutil.copy2(repaired, final_mesh)

    return final_mesh