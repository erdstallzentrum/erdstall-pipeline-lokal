from dataclasses import dataclass


@dataclass
class PointCloudSettings:
    # Reconstruction mode
    reconstruction_method: str = "cave_smooth"
    # Options:
    # "cave_realistic"
    # "cave_smooth"
    # "poisson"

    # Preprocessing
    # 0.005 keeps high detail but still regularizes the scan slightly.
    # Use 0.0 only if the point cloud is already very clean.
    downsample_size: float = 0.005
    max_points_for_poisson: int = 5_000_000
    spacing_sample_size: int = 300_000

    # Normals
    normal_radius_factor: float = 3.5
    normal_max_nn: int = 120
    orient_normals: bool = True
    orient_normals_k: int = 50

    # Ball Pivoting / Cave mode
    # Good high-detail cave preset.
    ball_radius_1: float = 1.1
    ball_radius_2: float = 1.8
    ball_radius_3: float = 3.0
    ball_radius_4: float = 5.0

    remove_small_components: bool = True
    min_component_triangle_ratio: float = 0.0005

    # Keep OFF unless you actually implemented safe small-hole filling.
    fill_small_holes: bool = False
    max_hole_size: int = 100

    # Poisson fallback settings
    poisson_depth: int = 10
    poisson_scale: float = 1.6
    poisson_linear_fit: bool = False
    poisson_density_quantile: float = 0.01
    poisson_threads: int = 0
    auto_limit_poisson_depth: bool = False

    # Output
    smoothing_iterations: int = 0
    color_transfer_chunk_size: int = 1_000_000

    # Point cloud densification / upsampling
    densify_point_cloud: bool = False
    densify_factor: float = 0.5
    densify_k: int = 8
    densify_max_edge_factor: float = 2.5
    densify_max_new_points: int = 500_000

    NORMAL_CHUNK_SIZE = 50_000