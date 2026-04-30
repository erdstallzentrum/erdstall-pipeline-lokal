from __future__ import annotations
from pathlib import Path
from PySide6.QtCore import QThread, Slot
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from erdstall_pipeline.settings.texture_settings import TextureSettings
from erdstall_admin_gui.workers.texture_worker import TextureWorker

class TextureWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.thread: QThread | None = None
        self.worker: TextureWorker | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        form_layout = QFormLayout()

        self.input_folder_edit = QLineEdit()
        self.output_folder_edit = QLineEdit()

        input_row = QHBoxLayout()
        input_row.addWidget(self.input_folder_edit)

        self.browse_input_button = QPushButton("Browse")
        self.browse_input_button.clicked.connect(self.select_input_folder)
        input_row.addWidget(self.browse_input_button)

        output_row = QHBoxLayout()
        output_row.addWidget(self.output_folder_edit)

        self.browse_output_button = QPushButton("Browse")
        self.browse_output_button.clicked.connect(self.select_output_folder)
        output_row.addWidget(self.browse_output_button)


        self.same_folder_checkbox = QCheckBox("Use input folder as output folder.")
        self.same_folder_checkbox.setChecked(True)
        self.same_folder_checkbox.toggled.connect(self.toggle_same_folder)

        self.brightness_spin = self._create_spinbox()
        self.contrast_spin = self._create_spinbox()
        self.saturation_spin = self._create_spinbox()
        self.sharpness_spin = self._create_spinbox()


        form_layout.addRow("Input texture folder:", self._wrap_layout(input_row))
        form_layout.addRow("", self.same_folder_checkbox)
        form_layout.addRow("Output folder:", self._wrap_layout(output_row))
        form_layout.addRow("Brightness:", self.brightness_spin)
        form_layout.addRow("Contrast:", self.contrast_spin)
        form_layout.addRow("Saturation:", self.saturation_spin)
        form_layout.addRow("Sharpness:", self.sharpness_spin)


        main_layout.addLayout(form_layout)

        button_row = QHBoxLayout()
        self.run_button = QPushButton("Run")
        self.run_button.clicked.connect(self.start_texture_processing)
        button_row.addWidget(self.run_button)

        self.clear_log_button = QPushButton("Clear log")
        self.clear_log_button.clicked.connect(self.clear_log)
        button_row.addWidget(self.clear_log_button)

        main_layout.addLayout(button_row)

        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        main_layout.addWidget(self.log_output)


        self.toggle_same_folder(True)

    def _create_spinbox(self) -> QDoubleSpinBox:
        spinbox = QDoubleSpinBox()
        spinbox.setRange(0.0,5.0)
        spinbox.setDecimals(2)
        spinbox.setSingleStep(0.1)
        spinbox.setValue(1.0)
        return spinbox
    
    def _wrap_layout(self, layout: QHBoxLayout)-> QWidget:
        widget = QWidget()
        widget.setLayout(layout)
        return widget
    
    @Slot()
    def select_input_folder(self)-> None:
        folder = QFileDialog.getExistingDirectory(self, "Select input texture folder")
        if folder:
            self.input_folder_edit.setText(folder)
            if self.same_folder_checkbox.isChecked():
                self.output_folder_edit.setText(folder)
    
    @Slot()
    def select_output_folder(self)-> None:
        if(self.same_folder_checkbox.isChecked()):
            return
        folder = QFileDialog.getExistingDirectory(self, "Select output texture folder")
        if folder: self.output_folder_edit.setText(folder)

    @Slot(bool)
    def toggle_same_folder(self, checked: bool) -> None:
        self.output_folder_edit.setDisabled(checked)
        self.browse_output_button.setDisabled(checked)

        if checked:
            self.output_folder_edit.setText(self.input_folder_edit.text())

    def build_settings(self) -> TextureSettings:
        return TextureSettings(
            brightness=self.brightness_spin.value(),
            contrast=self.contrast_spin.value(),
            saturation=self.saturation_spin.value(),
            sharpness=self.sharpness_spin.value()
        )
    
    def append_log(self, text: str) -> None:
        self.log_output.appendPlainText(text)

    @Slot()
    def clear_log(self) -> None:
        self.log_output.clear()
    
    def validate_inputs(self) -> tuple[Path, Path] | None:
        input_folder_text = self.input_folder_edit.text().strip()
        output_folder_text = self.output_folder_edit.text().strip()

        if not input_folder_text:
            QMessageBox.warning(self, "Missing input", "Please select an input texture folder.")
            return None

        input_folder = Path(input_folder_text)
        
        if not Path(input_folder).exists():
            QMessageBox.warning(self, "Invalid input", "Input folder does not exist.")
            return None
        
        if self.same_folder_checkbox.isChecked():
            output_folder = input_folder
            self.output_folder_edit.setText(str(output_folder))
        else:
            if not output_folder_text:
                QMessageBox.warning(self, "Missing output", "Please select an output folder.")
                return None

            output_folder = Path(output_folder_text)

        output_folder.mkdir(parents=True, exist_ok=True)

        return input_folder, output_folder
    
    @Slot()
    def start_texture_processing(self) -> None:
        validated = self.validate_inputs()
        if not validated:
            return
        
        input_folder, output_folder = validated
        settings = self.build_settings()

        self.run_button.setEnabled(False)
        self.status_label.setText("Processing...")
        self.append_log("Preparing worker...")

        self.thread = QThread()
        self.worker = TextureWorker(
            input_folder=input_folder,
            output_folder=output_folder,
            settings=settings
        )

        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.log.connect(self.append_log)
        self.worker.finished.connect(self.on_processing_finished)
        self.worker.error.connect(self.on_processing_error)

        self.worker.finished.connect(self.thread.quit)
        self.worker.error.connect(self.thread.quit)

        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
    
    @Slot()
    def on_processing_finished(self) -> None:
        self.status_label.setText("Done")
        self.run_button.setEnabled(True)
        QMessageBox.information(self, "Succes","Texture processing finished.")
        self.worker = None
        self.thread = None

    
    @Slot(str)
    def on_processing_error(self, message: str)-> None:
        self.append_log(f"ERROR: {message}")
        self.status_label.setText("Failed")
        self.run_button.setEnabled(True)
        QMessageBox.critical(self, "Error", message)
        self.worker = None
        self.thread = None


        
    
