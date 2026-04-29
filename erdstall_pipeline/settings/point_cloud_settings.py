from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PointCloudSettings:
    # High quality voxel size.
    # If your model units are meters, 0.01 = 1 cm.
    # For even more detail try 0.005, but it can get very heavy.
    downsample_size: float = 0.01

    # High-quality cap. Allows more detail than 1.5M.
    # If your PC has less than 32 GB RAM, use 2_000_000 instead.
    max_points_for_poisson: int = 3_000_000

    # Enough for stable spacing estimation without wasting too much time.
    spacing_sample_size: int = 50_000

    # Smaller radius keeps sharper details.
    # Too high = blobby.
    normal_radius_factor: float = 2.5

    # Good detail/stability balance.
    normal_max_nn: int = 30

    orient_normals: bool = True
    orient_normals_k: int = 16

    # High-quality Poisson.
    # 10 is a strong default.
    # 11 can be very heavy.
    poisson_depth: int = 10

    poisson_scale: float = 1.02

    # Linear fit usually preserves sharper details better.
    poisson_linear_fit: bool = True

    # Low trim so thin boat parts do not disappear.
    # 0.03 or 0.08 is too aggressive for rails/pipes/windows.
    poisson_density_quantile: float = 0.005

    # Smoothing makes hard-surface models look melted.
    smoothing_iterations: int = 0

    color_transfer_chunk_size: int = 100_000

    # Do not use 0 if 0 means auto/all cores.
    # 4 keeps Windows more responsive.
    poisson_threads: int = 4

    # For best quality, do not silently lower depth.
    # If it crashes, set this back to True.
    auto_limit_poisson_depth: bool = False