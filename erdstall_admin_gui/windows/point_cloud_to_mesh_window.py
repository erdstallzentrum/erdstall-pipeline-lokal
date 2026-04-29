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
    QWidget,
)

from erdstall_pipeline.settings.point_cloud_settings import PointCloudSettings


class PointCloudToMeshWindow(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Point Cloud to Mesh Settings")
        self.resize(560, 520)

        self._build_ui()
        self._load_defaults()
        self._connect()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ------------------------------------------------------------
        # Preprocessing
        # ------------------------------------------------------------
        preprocess_group = QGroupBox("Preprocessing")
        preprocess_form = QFormLayout(preprocess_group)

        self.downsample_size = self._doublespinbox(0.0, 10000.0, 0.005, 4)
        self.max_points_for_poisson = self._spinbox(0, 20_000_000)
        self.spacing_sample_size = self._spinbox(1_000, 5_000_000)

        preprocess_form.addRow("Downsample voxel size:", self.downsample_size)
        preprocess_form.addRow("Max points for Poisson:", self.max_points_for_poisson)
        preprocess_form.addRow("Spacing sample size:", self.spacing_sample_size)

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
        poisson_group = QGroupBox("Poisson Reconstruction")
        poisson_form = QFormLayout(poisson_group)

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

        layout.addWidget(preprocess_group)
        layout.addWidget(normals_group)
        layout.addWidget(poisson_group)
        layout.addWidget(output_group)
        layout.addLayout(buttons)

    def _connect(self) -> None:
        self.cancel_button.clicked.connect(self.reject)
        self.run_button.clicked.connect(self.accept)
        self.orient_normals.toggled.connect(self.orient_normals_k.setEnabled)

    def _load_defaults(self) -> None:
        defaults = PointCloudSettings()

        self.downsample_size.setValue(defaults.downsample_size)
        self.max_points_for_poisson.setValue(
            getattr(defaults, "max_points_for_poisson", 1_500_000)
        )
        self.spacing_sample_size.setValue(defaults.spacing_sample_size)

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

    def get_settings(self) -> PointCloudSettings:
        return PointCloudSettings(
            downsample_size=self.downsample_size.value(),
            max_points_for_poisson=self.max_points_for_poisson.value(),
            spacing_sample_size=self.spacing_sample_size.value(),
            normal_radius_factor=self.normal_radius_factor.value(),
            normal_max_nn=self.normal_max_nn.value(),
            orient_normals=self.orient_normals.isChecked(),
            orient_normals_k=self.orient_normals_k.value(),
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