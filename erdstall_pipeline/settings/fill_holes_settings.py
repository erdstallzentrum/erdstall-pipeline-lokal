from __future__ import annotations

from dataclasses import dataclass

from config import INITIAL_MESH_REDUCTION_FACTOR


@dataclass
class FillHolesSettings:
    run_poisson_on_mesh: bool = False

    close_holes_on_mesh_input: bool = True
    close_hole_under_percent: float = 0.10

    poisson_depth: int = 10
    poisson_fulldepth: int = 5
    poisson_cgdepth: int = 0
    poisson_scale: float = 1.02
    poisson_samplespernode: float = 1.5
    poisson_pointweight: float = 8.0
    poisson_iters: int = 8
    poisson_preclean: bool = True

    transfer_texture_to_vertex_colors: bool = True

    smooth_mesh_input: bool = False
    mesh_smoothing_iterations: int = 3

    reduce_size: bool = False
    mesh_reduction_percent: float = INITIAL_MESH_REDUCTION_FACTOR