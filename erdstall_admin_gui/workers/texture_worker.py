from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from erdstall_pipeline.change_textures import process_model_textures
from erdstall_pipeline.settings.texture_settings import TextureSettings


class TextureWorker(QObject):
    finished = Signal()
    error = Signal(str)
    log = Signal(str)

    def __init__(
        self,
        input_folder: str | Path,
        output_folder: str | Path,
        settings: TextureSettings,
    ) -> None:
        super().__init__()
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.settings = settings


    @Slot()
    def run(self) -> None:
        try:
            self.log.emit("Starting texture processing...")
            self.log.emit(f"Input folder: {self.input_folder}")
            self.log.emit(f"Output_folder: {self.output_folder}")
            self.log.emit(
                f"Brightness: {self.settings.brightness}, "
                f"Contrast: {self.settings.contrast}, "
                f"Saturation: {self.settings.saturation}, "
                f"Sharpness: {self.settings.sharpness}"
            )

            process_model_textures(
                input_folder = self.input_folder,
                output_folder = self.output_folder,
                settings = self.settings,
            )

            self.log.emit("Textures processing done.")
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))