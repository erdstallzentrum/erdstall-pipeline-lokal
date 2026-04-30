import numpy as np

from .config import (
    FILES_DIR,
    VOLUME_FILENAME,
    SKELETON_FILENAME,
    SKELETON_VOLUME_FILENAME,
    SIZE,
)

def merge_raws():
    volume_path = FILES_DIR / VOLUME_FILENAME
    skeleton_path = FILES_DIR / SKELETON_FILENAME
    out = FILES_DIR / SKELETON_VOLUME_FILENAME

    vol = np.fromfile(str(volume_path), dtype=np.uint8).reshape((SIZE, SIZE, SIZE))
    skel = np.fromfile(str(skeleton_path), dtype=np.uint8).reshape((SIZE, SIZE, SIZE))

    merged = ((vol > 0) & (skel > 0)).astype(np.uint8) * 255
    merged.tofile(str(out))

    return str(out)