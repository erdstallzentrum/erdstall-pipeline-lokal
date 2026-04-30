from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

from ..config import IMAGE_DEFAULT_FACTOR


@dataclass(slots = True)
class TextureSettings:
    brightness: float = IMAGE_DEFAULT_FACTOR
    contrast: float = IMAGE_DEFAULT_FACTOR
    saturation: float = IMAGE_DEFAULT_FACTOR
    sharpness: float = IMAGE_DEFAULT_FACTOR


@dataclass(slots = True)
class TextureJob: 
    input_folder: str | Path
    output_folder: str | Path
    settings: TextureSettings