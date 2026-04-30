import logging
import shutil
from pathlib import Path

from .config import PLY_DIR, TEXTURE_DIR, BACKUP_TEXTURE_DIR

logger = logging.getLogger(__name__)


def _save_original_version(mesh_id):
    erdstall_path = Path(PLY_DIR) / mesh_id
    if not erdstall_path.exists():
        raise FileNotFoundError(f"Erdstall directory not found: {mesh_id}")

    backup_path = erdstall_path /  BACKUP_TEXTURE_DIR
    current_path = erdstall_path / TEXTURE_DIR

    if not current_path.exists():
        raise FileNotFoundError(f"Texture directory not found: {current_path}")

    if not backup_path.exists():
        try:
            backup_path.mkdir(parents=True, exist_ok=True)

            for filename in current_path.iterdir():
                src_path =  filename
                dst_path = backup_path /  filename.name
                shutil.copy2(src_path, dst_path)
        except Exception as e:
            logger.error(f"Failed to create backup textures directory: {str(e)}", exc_info=True)
            raise


def get_current_version_path(mesh_id) -> Path:
    _save_original_version(mesh_id)
    return Path(PLY_DIR) / mesh_id / TEXTURE_DIR


def delete_new_version(mesh_id):
    _save_original_version(mesh_id)
    current_path = get_current_version_path(mesh_id)
    backup_path = current_path.parent / BACKUP_TEXTURE_DIR

    try:
        for element in current_path.iterdir():
            if element.is_file():
                element.unlink()
            elif element.is_dir():
                shutil.rmtree(element)

        for filename in backup_path.iterdir():
            src_path = filename
            dst_path = current_path / filename.name
            shutil.copy2(src_path, dst_path)

    except Exception as e:
        logger.error(f"Error deleting version: {str(e)}", exc_info=True)
        raise