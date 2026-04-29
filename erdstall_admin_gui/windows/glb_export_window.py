from __future__ import annotations

from PySide6.QtWidgets import QDialog, QWidget, QVBoxLayout, QGroupBox, QFormLayout, QCheckBox, QLineEdit, QPushButton, \
    QHBoxLayout, QComboBox, QFileDialog, QDoubleSpinBox

from erdstall_pipeline.settings.glb_export_settings import GlbExportSettings



class GlbExportWindow(QDialog):
    def __init__(self, parent: QWidget |None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("GLB Export Settings")
        self.resize(560, 320)

        self._build_ui()
        self._load_defaults()
        self._connect()


    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        human_group = QGroupBox("Human Scale Reference")
        human_form = QFormLayout(human_group)

        self.add_human_scale = QCheckBox("Add human scale model")

        self.human_model_path = QLineEdit()
        self.human_browse_button = QPushButton("Browse")

        human_path_row = QHBoxLayout()
        human_path_row.addWidget(self.human_model_path)
        human_path_row.addWidget(self.human_browse_button)

        self.human_height = self._doublespinbox(0.1, 10.0, 0.05, 2)
        self.human_floor_offset = self._doublespinbox(-10.0, 10.0, 0.01, 3)

        self.human_up_axis = QComboBox()
        self.human_up_axis.addItems(["x", "y", "z"])

        human_form.addRow("", self.add_human_scale)
        human_form.addRow("Human model:", self._wrap(human_path_row))
        human_form.addRow("Human height:", self.human_height)
        human_form.addRow("Floor offset:", self.human_floor_offset)
        human_form.addRow("Human up axis:", self.human_up_axis)

        rotation_group = QGroupBox("Export Rotation")
        rotation_form = QFormLayout(rotation_group)

        self.rotation_x = self._doublespinbox(-360.0, 360.0, 5.0, 2)
        self.rotation_y = self._doublespinbox(-360.0, 360.0, 5.0, 2)
        self.rotation_z = self._doublespinbox(-360.0, 360.0, 5.0, 2)

        rotation_form.addRow("Rotate X degrees:", self.rotation_x)
        rotation_form.addRow("Rotate Y degrees:", self.rotation_y)
        rotation_form.addRow("Rotate Z degrees:", self.rotation_z)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.export_button = QPushButton("Export GLB")

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.export_button)

        layout.addWidget(human_group)
        layout.addWidget(rotation_group)
        layout.addLayout(buttons)

    def _connect(self) -> None:
        self.cancel_button.clicked.connect(self.reject)
        self.export_button.clicked.connect(self.accept)
        self.human_browse_button.clicked.connect(self._browse_human_model)
        self.add_human_scale.toggled.connect(self._set_human_settings_enabled)

    def _load_defaults(self) -> None:
        defaults = GlbExportSettings()

        self.add_human_scale.setChecked(defaults.add_human_scale)
        self.human_model_path.setText(defaults.human_model_path)
        self.human_height.setValue(defaults.human_height)
        self.human_floor_offset.setValue(defaults.human_floor_offset)

        index = self.human_up_axis.findText(defaults.human_up_axis)
        if index >= 0:
            self.human_up_axis.setCurrentIndex(index)

        self.rotation_x.setValue(defaults.rotation_x_degrees)
        self.rotation_y.setValue(defaults.rotation_y_degrees)
        self.rotation_z.setValue(defaults.rotation_z_degrees)

        self._set_human_settings_enabled(defaults.add_human_scale)

    def _set_human_settings_enabled(self, enabled: bool) -> None:
        self.human_model_path.setEnabled(enabled)
        self.human_browse_button.setEnabled(enabled)
        self.human_height.setEnabled(enabled)
        self.human_floor_offset.setEnabled(enabled)
        self.human_up_axis.setEnabled(enabled)

    def _browse_human_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select human GLB model",
            "",
            "GLB files (*.glb);;GLTF files (*.gltf);;All files (*)",
        )

        if path:
            self.human_model_path.setText(path)

    def get_settings(self) -> GlbExportSettings:
        return GlbExportSettings(
            add_human_scale=self.add_human_scale.isChecked(),
            human_model_path=self.human_model_path.text().strip() or "public/person.glb",
            human_height=self.human_height.value(),
            human_floor_offset=self.human_floor_offset.value(),
            human_up_axis=self.human_up_axis.currentText(),
            rotation_x_degrees=self.rotation_x.value(),
            rotation_y_degrees=self.rotation_y.value(),
            rotation_z_degrees=self.rotation_z.value(),
        )

    def _wrap(self, layout: QHBoxLayout) -> QWidget:
        widget = QWidget()
        widget.setLayout(layout)
        return widget

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

