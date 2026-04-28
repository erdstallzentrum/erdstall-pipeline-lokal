from __future__ import annotations

from dataclasses import dataclass, field

from .point_cloud_settings import PointCloudSettings


@dataclass
class FillHolesSettings:
    point_cloud_settings: PointCloudSettings = field(
        default_factory=PointCloudSettings
    )

    run_poisson_on_mesh: bool = False

    close_holes_on_mesh_input: bool = False
    mesh_hole_max_size: int = 500

    point_cloud_depth: int = 10
    point_cloud_fulldepth: int = 5
    point_cloud_scale: float = 1.02
    point_cloud_samplespernode: float = 1.5
    point_cloud_pointweight: float = 8.0
    point_cloud_iters: int = 8
    point_cloud_preclean: bool = True

    poisson_depth: int = 12
    poisson_fulldepth: int = 5
    poisson_cgdepth: int = 0
    poisson_scale: float = 1.02
    poisson_samplespernode: float = 1.5
    poisson_pointweight: float = 8.0
    poisson_iters: int = 8
    poisson_preclean: bool = True

    transfer_texture_to_vertex_colors: bool = True
    smooth_reconstructed_point_cloud_mesh: bool = False
    point_cloud_smoothing_iterations: int = 0

    smooth_mesh_input: bool = False
    mesh_smoothing_iterations: int = 3
    reduce_size: bool = False
