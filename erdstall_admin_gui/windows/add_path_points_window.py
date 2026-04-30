from __future__ import annotations
from pathlib import Path
import xml.etree.ElementTree as ET
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget, QLineEdit, QFileDialog, QMessageBox,
)

class AddPathPointsWindow(QDialog):
    def __init__(self, parent: QWidget | None = None)-> None:
        super().__init__(parent)

        self.setWindowTitle("Add Path Points from .pp File")
        self.resize(520, 260)

        self.pp_file_path: Path | None = None
        self._values:  list[float] | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        info_label = QLabel(
            "Select a MeshLab .pp file. The first 3 picked points will be averaged "
            "to create the start point, and the next 3 picked points will be averaged "
            "to create the end point."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        file_group = QGroupBox("Select a .pp file")
        file_layout = QHBoxLayout(file_group)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)

        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self._browse_button_clicked)

        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(self.browse_button)

        layout.addWidget(file_group)

        preview_group = QGroupBox("Calculate Center Points")
        preview_layout = QFormLayout(preview_group)

        self.start_label = QLabel("-")
        self.end_label = QLabel("-")

        preview_layout.addRow("Start point:", self.start_label)
        preview_layout.addRow("End point:", self.end_label)


        layout.addWidget(preview_group)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.save_button = QPushButton("Save")
        self.save_button.setEnabled(False)

        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self._accept_if_valid)

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)

        layout.addLayout(buttons)

    def _browse_button_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a .pp file",
            "",
            "Picked Points Files (*.pp);;XML Files (*.xml);; All Files (*)"
        )

        if not file_path:
            return

        self.file_path_edit.setText(file_path)
        self.pp_file_path = Path(file_path).expanduser()

        try:
            values = self._parse_pp_file(self.pp_file_path)
        except FileNotFoundError as e:
            self._values = None
            self.start_label.setText("-")
            self.end_label.setText("-")
            self.save_button.setEnabled(False)
            QMessageBox.critical(self, "Invalid .pp file", str(e))
            return

        self._values = values
        start_text = f"x={values[0]:.6f}, y={values[1]:.6f}, z={values[2]:.6f}"
        end_text = f"x={values[3]:.6f}, y={values[4]:.6f}, z={values[5]:.6f}"

        self.start_label.setText(start_text)
        self.end_label.setText(end_text)
        self.save_button.setEnabled(True)

    def _accept_if_valid(self) -> None:
        if self._values is None:
            QMessageBox.warning(
                self,
                "No data",
                "Please select a .pp file",
            )
            return
        self.accept()


    def get_values(self)->list[float]:
        if self._values is None:
            return []
        return self._values

    @staticmethod
    def _parse_pp_file(file_path: Path) -> list[float]:
        file_path = Path(file_path).expanduser()

        tree = ET.parse(str(file_path))
        root = tree.getroot()

        points = root.findall("point")
        if len(points) < 6:
            raise ValueError(
                "The .pp file must contain at least 6 points: "
                "first 3 for start and next 3 for end."
            )
        start_points = points[:3]
        end_points = points[3:6]

        start_center = AddPathPointsWindow._average_points(start_points)
        end_center = AddPathPointsWindow._average_points(end_points)

        return [
            start_center[0],
            start_center[1],
            start_center[2],
            end_center[0],
            end_center[1],
            end_center[2],
        ]

    @staticmethod
    def _average_points(points) -> tuple[float, float, float]:
        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []

        for point in points:
            x = point.attrib.get("x")
            y = point.attrib.get("y")
            z = point.attrib.get("z")

            if x is None or y is None or z is None:
                raise ValueError("A point in the .pp file is missing.")

            xs.append(float(x))
            ys.append(float(y))
            zs.append(float(z))

        return(
            sum(xs) / len(xs),
            sum(ys) / len(ys),
            sum(zs) / len(zs)
        )
