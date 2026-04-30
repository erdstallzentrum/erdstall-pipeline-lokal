from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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

from erdstall_pipeline.settings.fill_holes_settings import FillHolesSettings


class FillHolesWindow(QDialog):
    MODE_NO_FILL = "No filling / cleanup only"
    MODE_NORMAL_FILL = "Normal hole filling only"
    MODE_POISSON_ONLY = "Poisson reconstruction only"
    MODE_POISSON_AND_NORMAL = "Poisson + normal hole filling"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Fill Holes Settings")
        self.resize(560, 420)

        self._build_ui()
        self._load_defaults()
        self._connect()
        self._update_mode_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # ------------------------------------------------------------
        # Fill Mode
        # ------------------------------------------------------------
        mode_group = QGroupBox("Fill Mode")
        mode_form = QFormLayout(mode_group)

        self.fill_mode = QComboBox()
        self.fill_mode.addItems(
            [
                self.MODE_NO_FILL,
                self.MODE_NORMAL_FILL,
                self.MODE_POISSON_ONLY,
                self.MODE_POISSON_AND_NORMAL,
            ]
        )

        mode_form.addRow("Mode:", self.fill_mode)

        # ------------------------------------------------------------
        # Normal Hole Filling
        # ------------------------------------------------------------
        repair_group = QGroupBox("Normal Hole Filling")
        repair_form = QFormLayout(repair_group)
        self.repair_group = repair_group

        self.close_hole_under_percent = self._doublespinbox(0.0, 1.0, 0.01, 2)

        repair_form.addRow(
            "Ignore top percent:",
            self.close_hole_under_percent,
        )

        # ------------------------------------------------------------
        # Optional Mesh Poisson
        # ------------------------------------------------------------
        poisson_group = QGroupBox("Poisson Reconstruction")
        poisson_form = QFormLayout(poisson_group)
        self.poisson_group = poisson_group

        self.poisson_depth = self._spinbox(1, 14)
        self.poisson_fulldepth = self._spinbox(1, 14)
        self.poisson_cgdepth = self._spinbox(0, 14)
        self.poisson_scale = self._doublespinbox(0.1, 10.0, 0.1, 2)
        self.poisson_samplespernode = self._doublespinbox(0.1, 20.0, 0.1, 2)
        self.poisson_pointweight = self._doublespinbox(0.1, 20.0, 0.1, 2)
        self.poisson_iters = self._spinbox(1, 50)
        self.poisson_preclean = QCheckBox()

        poisson_form.addRow("Depth:", self.poisson_depth)
        poisson_form.addRow("Full depth:", self.poisson_fulldepth)
        poisson_form.addRow("CG depth:", self.poisson_cgdepth)
        poisson_form.addRow("Scale:", self.poisson_scale)
        poisson_form.addRow("Samples per node:", self.poisson_samplespernode)
        poisson_form.addRow("Point weight:", self.poisson_pointweight)
        poisson_form.addRow("Iterations:", self.poisson_iters)
        poisson_form.addRow("Preclean:", self.poisson_preclean)

        # ------------------------------------------------------------
        # Output / Cleanup
        # ------------------------------------------------------------
        output_group = QGroupBox("Output / Cleanup")
        output_form = QFormLayout(output_group)

        self.smooth_mesh_input = QCheckBox()
        self.mesh_smoothing_iterations = self._spinbox(0, 50)

        self.transfer_texture = QCheckBox("Transfer texture to vertex colors")
        self.reduce_size = QCheckBox("Reduce file size after repair")
        self.mesh_reduction_percent = self._doublespinbox(0.0, 95.0, 1.0, 5)
        output_form.addRow("Smooth mesh:", self.smooth_mesh_input)
        output_form.addRow(
            "Smoothing iterations:",
            self.mesh_smoothing_iterations,
        )
        output_form.addRow("Mesh reduction percent:", self.mesh_reduction_percent)

        # ------------------------------------------------------------
        # Buttons
        # ------------------------------------------------------------
        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.run_button = QPushButton("Run")

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.run_button)

        layout.addWidget(mode_group)
        layout.addWidget(repair_group)
        layout.addWidget(poisson_group)
        layout.addWidget(output_group)
        layout.addWidget(self.transfer_texture)
        layout.addWidget(self.reduce_size)
        layout.addLayout(buttons)

    def _connect(self) -> None:
        self.cancel_button.clicked.connect(self.reject)
        self.run_button.clicked.connect(self.accept)

        self.fill_mode.currentTextChanged.connect(self._update_mode_ui)
        self.smooth_mesh_input.toggled.connect(
            self.mesh_smoothing_iterations.setEnabled
        )
        self.reduce_size.toggled.connect(self.mesh_reduction_percent.setEnabled)

    def _load_defaults(self) -> None:
        defaults = FillHolesSettings()

        if defaults.run_poisson_on_mesh and defaults.close_holes_on_mesh_input:
            self.fill_mode.setCurrentText(self.MODE_POISSON_AND_NORMAL)
        elif defaults.run_poisson_on_mesh:
            self.fill_mode.setCurrentText(self.MODE_POISSON_ONLY)
        elif defaults.close_holes_on_mesh_input:
            self.fill_mode.setCurrentText(self.MODE_NORMAL_FILL)
        else:
            self.fill_mode.setCurrentText(self.MODE_NO_FILL)

        self.close_hole_under_percent.setValue(defaults.close_hole_under_percent)

        self.poisson_depth.setValue(defaults.poisson_depth)
        self.poisson_fulldepth.setValue(defaults.poisson_fulldepth)
        self.poisson_cgdepth.setValue(defaults.poisson_cgdepth)
        self.poisson_scale.setValue(defaults.poisson_scale)
        self.poisson_samplespernode.setValue(defaults.poisson_samplespernode)
        self.poisson_pointweight.setValue(defaults.poisson_pointweight)
        self.poisson_iters.setValue(defaults.poisson_iters)
        self.poisson_preclean.setChecked(defaults.poisson_preclean)

        self.smooth_mesh_input.setChecked(defaults.smooth_mesh_input)
        self.mesh_smoothing_iterations.setValue(defaults.mesh_smoothing_iterations)
        self.mesh_smoothing_iterations.setEnabled(defaults.smooth_mesh_input)

        self.transfer_texture.setChecked(defaults.transfer_texture_to_vertex_colors)
        self.reduce_size.setChecked(defaults.reduce_size)
        self.mesh_reduction_percent.setValue(
            getattr(defaults, "mesh_reduction_percent", 15.0)
        )
        self.mesh_reduction_percent.setEnabled(defaults.reduce_size)

    def _update_mode_ui(self) -> None:
        mode = self.fill_mode.currentText()

        uses_normal_fill = mode in (
            self.MODE_NORMAL_FILL,
            self.MODE_POISSON_AND_NORMAL,
        )

        uses_poisson = mode in (
            self.MODE_POISSON_ONLY,
            self.MODE_POISSON_AND_NORMAL,
        )

        self.repair_group.setEnabled(uses_normal_fill)
        self.poisson_group.setEnabled(uses_poisson)

        if mode == self.MODE_NO_FILL:
            self.run_button.setText("Run Cleanup")
        else:
            self.run_button.setText("Run Fill Holes")

    def get_settings(self) -> FillHolesSettings:
        mode = self.fill_mode.currentText()

        run_poisson_on_mesh = mode in (
            self.MODE_POISSON_ONLY,
            self.MODE_POISSON_AND_NORMAL,
        )

        close_holes_on_mesh_input = mode in (
            self.MODE_NORMAL_FILL,
            self.MODE_POISSON_AND_NORMAL,
        )

        return FillHolesSettings(
            run_poisson_on_mesh=run_poisson_on_mesh,
            close_holes_on_mesh_input=close_holes_on_mesh_input,
            close_hole_under_percent=self.close_hole_under_percent.value(),
            poisson_depth=self.poisson_depth.value(),
            poisson_fulldepth=self.poisson_fulldepth.value(),
            poisson_cgdepth=self.poisson_cgdepth.value(),
            poisson_scale=self.poisson_scale.value(),
            poisson_samplespernode=self.poisson_samplespernode.value(),
            poisson_pointweight=self.poisson_pointweight.value(),
            poisson_iters=self.poisson_iters.value(),
            poisson_preclean=self.poisson_preclean.isChecked(),
            transfer_texture_to_vertex_colors=self.transfer_texture.isChecked(),
            smooth_mesh_input=self.smooth_mesh_input.isChecked(),
            mesh_smoothing_iterations=self.mesh_smoothing_iterations.value(),
            reduce_size=self.reduce_size.isChecked(),
            mesh_reduction_percent=self.mesh_reduction_percent.value(),
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