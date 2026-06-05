from pathlib import Path
import re


def validate_mesh_id(mesh_id: str) -> None:
    if not mesh_id or not isinstance(mesh_id, str):
        raise ValueError('mesh_id must be a non-empty string')
    if not re.fullmatch(r'[A-Za-z0-9_]+', mesh_id):
        raise ValueError('mesh_id contains illegal characters')


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
