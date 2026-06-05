from __future__ import annotations

import subprocess
import sys
import os
import tempfile
from importlib.util import find_spec
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot
from erdstall_pipeline.settings.app_settings import AppSettings
from erdstall_pipeline.utils.fiji_executable import resolve_fiji_executable


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
                if find_spec(import_name) is not None:
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
        self.log.emit("\nChecking Fiji executable...")

        configured = AppSettings.get_fiji_exe()
        if configured is None:
            raise RuntimeError("Fiji executable not configured. \n"
                               "Please select Fiji in the setup window first.")

        fiji_exe = resolve_fiji_executable(configured)

        if not fiji_exe.exists():
            raise RuntimeError(f"Configured Fiji executable not found: {fiji_exe}")

        if not fiji_exe.is_file():
            raise RuntimeError(
                f"Configured Fiji path is not a file: {fiji_exe}\n\n"
                "On macOS you may select Fiji.app, but it must resolve to:\n"
                "Fiji.app/Contents/MacOS/ImageJ-macosx"
            )

        if not sys.platform.startswith("win") and not os.access(fiji_exe, os.X_OK):
            raise RuntimeError(
                f"Configured Fiji file is not executable: {fiji_exe}\n\n"
                "On macOS, fix it with:\n"
                f'chmod +x "{fiji_exe}"'
            )

        self.log.emit(f"[OK] Fiji executable resolved to: {fiji_exe}")

        self._run_fiji_smoke_test(fiji_exe)

    def _run_fiji_smoke_test(self, fiji_exe: Path) -> None:
        self.log.emit("Running Fiji test...")

        with tempfile.NamedTemporaryFile(
                "w",
                suffix=".txt",
                delete=False,
                encoding="utf-8",
        ) as marker_tmp:
            marker_path = Path(marker_tmp.name)

        marker_path.unlink(missing_ok=True)

        marker_ij_path = str(marker_path).replace("\\", "/")

        macro_text = f"""
        print("\\\\Clear");
        File.saveString("SETUP_VALIDATION_OK", "{marker_ij_path}");
        """

        with tempfile.NamedTemporaryFile(
                "w",
                suffix=".ijm",
                delete=False,
                encoding="utf-8",
        ) as tmp:
            tmp.write(macro_text)
            macro_path = Path(tmp.name)

        try:
            cmd = [
                str(fiji_exe),
                "--headless",
                "-macro",
                str(macro_path),
            ]

            self.log.emit(f"Command: {' '.join(cmd)}")

            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
            except subprocess.TimeoutExpired as e:
                raise RuntimeError(
                    "Fiji started but did not finish the validation macro within 120 seconds.\n\n"
                    "Try opening Fiji manually once, then run validation again.\n"
                    f"Executable: {fiji_exe}"
                ) from e
            except OSError as e:
                raise RuntimeError(
                    f"Could not start Fiji executable:\n{fiji_exe}\n\n"
                    f"System error: {e}"
                ) from e

            stdout = result.stdout or ""
            stderr = result.stderr or ""

            if stdout.strip():
                self.log.emit("[Fiji STDOUT]")
                self.log.emit(self._shorten(stdout))

            if stderr.strip():
                self.log.emit("[Fiji STDERR]")
                self.log.emit(self._shorten(stderr))

            if result.returncode != 0:
                raise RuntimeError(
                    f"Fiji validation failed with exit code {result.returncode}.\n\n"
                    f"STDOUT:\n{stdout}\n\n"
                    f"STDERR:\n{stderr}"
                )

            if not marker_path.exists():
                raise RuntimeError(
                    "Fiji exited successfully, but it did not create the validation marker file.\n\n"
                    "This means Fiji started, but the macro may not have executed correctly."
                )

            marker_text = marker_path.read_text(encoding="utf-8", errors="replace").strip()

            if marker_text != "SETUP_VALIDATION_OK":
                raise RuntimeError(
                    "Fiji created the validation marker file, but the content was unexpected.\n\n"
                    f"Expected: SETUP_VALIDATION_OK\n"
                    f"Got: {marker_text}"
                )

            self.log.emit("[OK] Fiji ran the validation macro successfully.")

        finally:
            try:
                macro_path.unlink(missing_ok=True)
            except Exception:
                pass

            try:
                marker_path.unlink(missing_ok=True)
            except Exception:
                pass

    @staticmethod
    def _shorten(text: str, limit: int = 4000) -> str:
        text = text.strip()
        if len(text) <= limit:
            return text
        return text[:limit] + "\n...[output shortened]..."

    @staticmethod
    def resolve_fiji_executable(fiji_path: str | Path) -> Path:
        return resolve_fiji_executable(fiji_path)





