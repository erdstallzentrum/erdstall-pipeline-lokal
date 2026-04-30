from __future__ import annotations
from PySide6.QtCore import QObject, Signal, Slot
from erdstall_pipeline.settings.app_settings import AppSettings
import importlib
import sys
import os


class SetupWorker(QObject):
    finished = Signal()
    log = Signal(str)
    success = Signal(str)
    error = Signal(str)


    def __init__(self) -> None:
        super().__init__()

    @Slot()
    def run(self)-> None:
        try:
            self.log.emit("Starting environment validation...\n")
            self._check_python_modules()
            self._check_fiji()
            self.success.emit("Setup validation completed successfully.")
        except Exception as e: 
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def _check_python_modules(self) -> None:
        required_modules = [
            ("Pillow", "PIL"),
            ("opencv-python", "cv2"),
            ("numpy", "numpy"),
            ("pymeshlab", "pymeshlab"),
            ("vtk", "vtk"),
            ("scyjava", "scyjava"),
            ("imagej", "imagej"),
            ("jpype1", "jpype"),
            ("scipy", "scipy"),
            ("PySide6", "PySide6"),
            ("pyqtdarktheme", "qdarktheme"),
        ]

        self.log.emit("Checking Python modules...")

        missing: list[str] = []

        for package_name, import_name in required_modules:
            try:
                if importlib.util.find_spec(import_name) is not None:
                    self.log.emit(f"[OK] {package_name}")
                else:
                    missing.append(package_name)
                    self.log.emit(f"[MISSING] {package_name}")
            except Exception as e:
                missing.append(package_name)
                self.log.emit(f"[ERROR] {package_name}: {e}")

        if missing:
            raise RuntimeError("Missing Python packages: " + ", ".join(missing))
        
    def _check_fiji(self) -> None:
        self.log.emit("Checking Fiji executable...")

        fiji_exe = AppSettings.get_fiji_exe()
        if fiji_exe is None:
            raise RuntimeError("Fiji executable is not configured.")

        fiji_exe = self._resolve_fiji_executable(fiji_exe)

        if not fiji_exe.exists():
            raise RuntimeError(f"Configured Fiji executable not found: {fiji_exe}")

        if not fiji_exe.is_file():
            raise RuntimeError(f"Configured Fiji path is not a file: {fiji_exe}")

        if not sys.platform.startswith("win") and not os.access(fiji_exe, os.X_OK):
            raise RuntimeError(f"Configured Fiji file is not executable: {fiji_exe}")

        self.log.emit(f"[OK] Fiji found at: {fiji_exe}")

    def _resolve_fiji_executable(self, fiji_path):
        if fiji_path.is_file():
            return fiji_path

        if sys.platform == "darwin" and fiji_path.is_dir() and fiji_path.suffix == ".app":
            mac_exe = fiji_path / "Contents" / "MacOS" / "ImageJ-macosx"
            if mac_exe.exists():
                return mac_exe

        return fiji_path



