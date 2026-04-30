from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class GlbExportSettings:
    add_human_scale: bool = True
    human_model_path: str | Path = "public/person.glb"
    human_height: float = 1.75
    human_floor_offset: float = 0.02
    human_up_axis: str = "y"


    rotation_x_degrees: float = 0.0
    rotation_y_degrees: float = 0.0
    rotation_z_degrees: float = 0.0

