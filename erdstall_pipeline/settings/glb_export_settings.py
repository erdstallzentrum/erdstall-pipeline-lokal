from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


GlbCompression = Literal["meshopt", "draco", "none"]

@dataclass
class GlbExportSettings:
    add_human_scale: bool = False
    human_model_path: str | Path = "public/person.glb"
    human_height: float = 1.75
    human_floor_offset: float = 0.02
    human_up_axis: str = "y"

    add_human_to_mobile: bool = False

    rotation_x_degrees: float = 0.0
    rotation_y_degrees: float = 0.0
    rotation_z_degrees: float = 0.0
    create_mobile_glb: bool = True
    optimize_glb: bool = True
    glb_compression: GlbCompression = "meshopt"

    main_include_normals: bool = True

    mobile_include_normals: bool = True
