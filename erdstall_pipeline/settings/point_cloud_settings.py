from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PointCloudSettings:
    downsample_size: float = 0.0
    poisson_depth: int = 11
    poisson_scale: float = 1.02

    poisson_linear_fit: bool = False
    poisson_density_quantile: float = 0.08
    normal_radius_factor: float = 4.0
    normal_max_nn: int = 40

    orient_normals: bool = True
    orient_normals_k: int = 20
    smoothing_iterations: int = 1
    color_transfer_chunk_size: int = 1_000_000
    spacing_sample_size: int = 300_000