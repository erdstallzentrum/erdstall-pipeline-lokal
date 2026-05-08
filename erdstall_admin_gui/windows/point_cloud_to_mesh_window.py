from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget, QComboBox, QScrollArea, QLabel,
)

from erdstall_pipeline.settings.point_cloud_settings import PointCloudSettings


class PointCloudToMeshWindow(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Point Cloud to Mesh Settings")
        self.resize(800, 500)

        self._build_ui()
        self._load_defaults()
        self._connect()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)

        scroll_area.setWidget(scroll_content)

        # ------------------------------------------------------------
        # Reconstruction mode
        # ------------------------------------------------------------
        mode_group = QGroupBox("Reconstruction Mode")
        mode_form = QFormLayout(mode_group)

        self.reconstruction_method = QComboBox()
        self.reconstruction_method.addItem(
            "Ball Pivoting",
            "cave_smooth",
        )
        self.reconstruction_method.addItem(
            "Poisson",
            "poisson",
        )

        mode_form.addRow("Mode:", self.reconstruction_method)

        # ------------------------------------------------------------
        # Cave / Ball Pivoting Reconstruction
        # ------------------------------------------------------------
        self.cave_group = QGroupBox("Cave / Ball Pivoting Options")
        cave_form = QFormLayout(self.cave_group)

        self.ball_radius_1 = self._doublespinbox(0.1, 20.0, 0.1, 2)
        self.ball_radius_2 = self._doublespinbox(0.1, 20.0, 0.1, 2)
        self.ball_radius_3 = self._doublespinbox(0.1, 20.0, 0.1, 2)
        self.ball_radius_4 = self._doublespinbox(0.1, 20.0, 0.1, 2)

        self.remove_small_components = QCheckBox()
        self.min_component_triangle_ratio = self._doublespinbox(0.0, 0.2, 0.001, 4)

        self.fill_small_holes = QCheckBox()
        self.max_hole_size = self._spinbox(1, 100_000)

        cave_form.addRow("Ball radius factor 1:", self.ball_radius_1)
        cave_form.addRow("Ball radius factor 2:", self.ball_radius_2)
        cave_form.addRow("Ball radius factor 3:", self.ball_radius_3)
        cave_form.addRow("Ball radius factor 4:", self.ball_radius_4)
        cave_form.addRow("Remove small components:", self.remove_small_components)
        cave_form.addRow("Min component ratio:", self.min_component_triangle_ratio)
        cave_form.addRow("Fill small holes:", self.fill_small_holes)
        cave_form.addRow("Max hole size:", self.max_hole_size)

        # ------------------------------------------------------------
        # Preprocessing
        # ------------------------------------------------------------
        preprocess_group = QGroupBox("Preprocessing")
        preprocess_form = QFormLayout(preprocess_group)

        self.downsample_size = self._doublespinbox(0.0, 10000.0, 0.005, 4)
        self.max_points_for_poisson_label = QLabel("Max points for Poisson:")
        self.max_points_for_poisson = self._spinbox(0, 30_000_000)
        self.spacing_sample_size = self._spinbox(1_000, 5_000_000)

        preprocess_form.addRow("Downsample voxel size:", self.downsample_size)
        preprocess_form.addRow(
            self.max_points_for_poisson_label,
            self.max_points_for_poisson,
        )
        preprocess_form.addRow("Spacing sample size:", self.spacing_sample_size)

        # ------------------------------------------------------------
        # Densification
        # ------------------------------------------------------------
        self.densify_group = QGroupBox("Point Cloud Densification")
        densify_form = QFormLayout(self.densify_group)

        self.densify_point_cloud = QCheckBox()
        self.densify_factor = self._doublespinbox(0.0, 5.0, 0.1, 2)
        self.densify_k = self._spinbox(3, 100)
        self.densify_max_edge_factor = self._doublespinbox(0.5, 20.0, 0.1, 2)
        self.densify_max_new_points = self._spinbox(0, 20_000_000)

        densify_form.addRow("Densify point cloud:", self.densify_point_cloud)
        densify_form.addRow("Densify factor:", self.densify_factor)
        densify_form.addRow("Densify K neighbors:", self.densify_k)
        densify_form.addRow("Max edge factor:", self.densify_max_edge_factor)
        densify_form.addRow("Max new points:", self.densify_max_new_points)

        # ------------------------------------------------------------
        # Normals
        # ------------------------------------------------------------
        normals_group = QGroupBox("Normals")
        normals_form = QFormLayout(normals_group)

        self.normal_radius_factor = self._doublespinbox(0.5, 20.0, 0.1, 2)
        self.normal_max_nn = self._spinbox(3, 500)

        self.orient_normals = QCheckBox()
        self.orient_normals_k = self._spinbox(3, 500)

        normals_form.addRow("Normal radius factor:", self.normal_radius_factor)
        normals_form.addRow("Normal max neighbors:", self.normal_max_nn)
        normals_form.addRow("Orient normals:", self.orient_normals)
        normals_form.addRow("Orient normals K:", self.orient_normals_k)

        # ------------------------------------------------------------
        # Poisson Reconstruction
        # ------------------------------------------------------------
        self.poisson_group = QGroupBox("Poisson Reconstruction")
        poisson_form = QFormLayout(self.poisson_group)

        self.poisson_depth = self._spinbox(1, 14)
        self.poisson_scale = self._doublespinbox(0.1, 10.0, 0.01, 2)
        self.poisson_linear_fit = QCheckBox()
        self.poisson_density_quantile = self._doublespinbox(0.0, 0.5, 0.01, 3)

        self.poisson_threads = self._spinbox(0, 64)
        self.auto_limit_poisson_depth = QCheckBox()

        poisson_form.addRow("Depth:", self.poisson_depth)
        poisson_form.addRow("Scale:", self.poisson_scale)
        poisson_form.addRow("Linear fit:", self.poisson_linear_fit)
        poisson_form.addRow("Density trim quantile:", self.poisson_density_quantile)
        poisson_form.addRow("Poisson threads:", self.poisson_threads)
        poisson_form.addRow("Auto-limit depth:", self.auto_limit_poisson_depth)

        # ------------------------------------------------------------
        # Output
        # ------------------------------------------------------------
        output_group = QGroupBox("Output")
        output_form = QFormLayout(output_group)

        self.smoothing_iterations = self._spinbox(0, 50)
        self.color_transfer_chunk_size = self._spinbox(10_000, 5_000_000)

        output_form.addRow("Smoothing iterations:", self.smoothing_iterations)
        output_form.addRow("Color transfer chunk size:", self.color_transfer_chunk_size)

        # ------------------------------------------------------------
        # Buttons
        # ------------------------------------------------------------
        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.run_button = QPushButton("Convert")

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.run_button)

        layout.addWidget(mode_group)
        layout.addWidget(preprocess_group)
        layout.addWidget(self.densify_group)
        layout.addWidget(normals_group)
        layout.addWidget(self.cave_group)
        layout.addWidget(self.poisson_group)
        layout.addWidget(output_group)

        main_layout.addWidget(scroll_area)
        main_layout.addLayout(buttons)

    def _connect(self) -> None:
        self.cancel_button.clicked.connect(self.reject)
        self.run_button.clicked.connect(self.accept)
        self.orient_normals.toggled.connect(self.orient_normals_k.setEnabled)
        self.reconstruction_method.currentIndexChanged.connect(self._update_mode_ui)
        self.fill_small_holes.toggled.connect(self.max_hole_size.setEnabled)
        self.remove_small_components.toggled.connect(
            self.min_component_triangle_ratio.setEnabled
        )
        self.densify_point_cloud.toggled.connect(self._update_densify_ui)

    def _update_mode_ui(self) -> None:
        method = self.reconstruction_method.currentData()

        is_poisson = method == "poisson"
        is_cave = method == "cave_smooth"

        self.cave_group.setVisible(is_cave)
        self.poisson_group.setVisible(is_poisson)

        self.max_points_for_poisson_label.setVisible(is_poisson)
        self.max_points_for_poisson.setVisible(is_poisson)

        if is_cave:
            self.fill_small_holes.setChecked(True)
            self.smoothing_iterations.setValue(1)

        elif is_poisson:
            self.smoothing_iterations.setValue(0)

        self.max_hole_size.setEnabled(self.fill_small_holes.isChecked())
        self.min_component_triangle_ratio.setEnabled(
            self.remove_small_components.isChecked()
        )

    def _update_densify_ui(self) -> None:
        enabled = self.densify_point_cloud.isChecked()

        self.densify_factor.setEnabled(enabled)
        self.densify_k.setEnabled(enabled)
        self.densify_max_edge_factor.setEnabled(enabled)
        self.densify_max_new_points.setEnabled(enabled)

    def _load_defaults(self) -> None:
        defaults = PointCloudSettings()

        self.downsample_size.setValue(defaults.downsample_size)
        self.max_points_for_poisson.setValue(
            getattr(defaults, "max_points_for_poisson", 1_500_000)
        )
        self.spacing_sample_size.setValue(defaults.spacing_sample_size)

        self.densify_point_cloud.setChecked(
            getattr(defaults, "densify_point_cloud", False)
        )
        self.densify_factor.setValue(getattr(defaults, "densify_factor", 0.5))
        self.densify_k.setValue(getattr(defaults, "densify_k", 8))
        self.densify_max_edge_factor.setValue(
            getattr(defaults, "densify_max_edge_factor", 2.5)
        )
        self.densify_max_new_points.setValue(
            getattr(defaults, "densify_max_new_points", 500_000)
        )

        self.normal_radius_factor.setValue(defaults.normal_radius_factor)
        self.normal_max_nn.setValue(defaults.normal_max_nn)

        self.orient_normals.setChecked(defaults.orient_normals)
        self.orient_normals_k.setValue(defaults.orient_normals_k)
        self.orient_normals_k.setEnabled(defaults.orient_normals)

        self.poisson_depth.setValue(defaults.poisson_depth)
        self.poisson_scale.setValue(defaults.poisson_scale)
        self.poisson_linear_fit.setChecked(defaults.poisson_linear_fit)
        self.poisson_density_quantile.setValue(defaults.poisson_density_quantile)

        self.poisson_threads.setValue(getattr(defaults, "poisson_threads", 0))
        self.auto_limit_poisson_depth.setChecked(
            getattr(defaults, "auto_limit_poisson_depth", True)
        )

        self.smoothing_iterations.setValue(defaults.smoothing_iterations)
        self.color_transfer_chunk_size.setValue(defaults.color_transfer_chunk_size)

        index = self.reconstruction_method.findData(
            getattr(defaults, "reconstruction_method", "cave_smooth")
        )
        if index >= 0:
            self.reconstruction_method.setCurrentIndex(index)

        self.ball_radius_1.setValue(getattr(defaults, "ball_radius_1", 1.5))
        self.ball_radius_2.setValue(getattr(defaults, "ball_radius_2", 2.5))
        self.ball_radius_3.setValue(getattr(defaults, "ball_radius_3", 4.0))
        self.ball_radius_4.setValue(getattr(defaults, "ball_radius_4", 6.0))

        self.remove_small_components.setChecked(
            getattr(defaults, "remove_small_components", True)
        )
        self.min_component_triangle_ratio.setValue(
            getattr(defaults, "min_component_triangle_ratio", 0.005)
        )

        self.fill_small_holes.setChecked(getattr(defaults, "fill_small_holes", False))
        self.max_hole_size.setValue(getattr(defaults, "max_hole_size", 100))

        self._update_mode_ui()
        self._update_densify_ui()

    def get_settings(self) -> PointCloudSettings:
        return PointCloudSettings(
            reconstruction_method=self.reconstruction_method.currentData(),

            downsample_size=self.downsample_size.value(),
            max_points_for_poisson=self.max_points_for_poisson.value(),
            spacing_sample_size=self.spacing_sample_size.value(),

            densify_point_cloud=self.densify_point_cloud.isChecked(),
            densify_factor=self.densify_factor.value(),
            densify_k=self.densify_k.value(),
            densify_max_edge_factor=self.densify_max_edge_factor.value(),
            densify_max_new_points=self.densify_max_new_points.value(),

            normal_radius_factor=self.normal_radius_factor.value(),
            normal_max_nn=self.normal_max_nn.value(),
            orient_normals=self.orient_normals.isChecked(),
            orient_normals_k=self.orient_normals_k.value(),

            ball_radius_1=self.ball_radius_1.value(),
            ball_radius_2=self.ball_radius_2.value(),
            ball_radius_3=self.ball_radius_3.value(),
            ball_radius_4=self.ball_radius_4.value(),
            remove_small_components=self.remove_small_components.isChecked(),
            min_component_triangle_ratio=self.min_component_triangle_ratio.value(),
            fill_small_holes=self.fill_small_holes.isChecked(),
            max_hole_size=self.max_hole_size.value(),

            poisson_depth=self.poisson_depth.value(),
            poisson_scale=self.poisson_scale.value(),
            poisson_linear_fit=self.poisson_linear_fit.isChecked(),
            poisson_density_quantile=self.poisson_density_quantile.value(),
            poisson_threads=self.poisson_threads.value(),
            auto_limit_poisson_depth=self.auto_limit_poisson_depth.isChecked(),

            smoothing_iterations=self.smoothing_iterations.value(),
            color_transfer_chunk_size=self.color_transfer_chunk_size.value(),
        )

    @staticmethod
    def _spinbox(minimum: int, maximum: int) -> QSpinBox:
        box = QSpinBox()
        box.setRange(minimum, maximum)
        return box

    @staticmethod
    def _doublespinbox(
        minimum: float,
        maximum: float,
        step: float,
        decimals: int,
    ) -> QDoubleSpinBox:
        box = QDoubleSpinBox()
        box.setRange(minimum, maximum)
        box.setSingleStep(step)
        box.setDecimals(decimals)
        return box