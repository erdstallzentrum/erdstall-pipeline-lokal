from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

MAC_EXECUTABLE_NAMES = [
    "ImageJ-macosx",
    "Fiji-macosx",
    "imagej-macosx",
    "fiji-macosx",
    "imagej-macos",
    "fiji-macos",
    "Fiji",
    "ImageJ"
]

WINDOWS_EXECUTABLE_NAMES = [
    "ImageJ-win64.exe",
    "fiji-windows-x64.exe",
    "ImageJ-win32.exe",
]

LINUX_EXECUTABLE_NAMES = [
    "ImageJ-linux64",
    "fiji-linux64",
    "ImageJ-linux32",
    "fiji",
]

def resolve_fiji_executable(fiji_path: str | Path) -> Path:
    path = Path(fiji_path).expanduser()

    if path.is_file():
        return path

    candidates: list[Path] = []

    if path.is_dir():
        if sys.platform == "darwin":
            if path.suffix.lower() == ".app":
                for name in MAC_EXECUTABLE_NAMES:
                    candidates.append(path / "Contents" / "MacOS" / name)

            for name in MAC_EXECUTABLE_NAMES:
                candidates.append(path / "Fiji.app" / "Contents" / "MacOS" / name)

            for name in MAC_EXECUTABLE_NAMES:
                candidates.append(path / name)

        elif sys.platform.startswith("win"):
            for name in WINDOWS_EXECUTABLE_NAMES:
                candidates.append(path / name)

            candidates.extend(
                [
                    path / "Fiji.app" / "ImageJ-win64.exe",
                    path / "Fiji.app" / "fiji-windows-x64.exe"
                ]
            )

        else:
            for name in LINUX_EXECUTABLE_NAMES:
                candidates.append(path / name)

            candidates.extend(
                [
                    path / "Fiji.app" / "ImageJ-linux",
                    path / "Fiji.app" / "fiji-linux-x64"
                ]
            )

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    return path


def find_fiji_executable(configured_path: str | Path | None = None) -> Path:
    raw_candidates: list[str | Path] = []

    env_path = os.environ.get("FIJI_EXE") or os.environ.get("FIJI_PATH")

    if env_path:
        raw_candidates.append(env_path)
    if configured_path:
        raw_candidates.append(configured_path)
    if sys.platform.startswith("win"):
        raw_candidates.extend(
            [
                Path(r"C:\Fiji.app\ImageJ-win64.exe"),
                Path(r"C:\Program Files\Fiji.app\ImageJ-win64.exe"),
                Path(r"C:\Program Files\Fiji.app\fiji-windows-x64.exe"),
                # Downloads folder
                Path.home() / "Downloads" / "Fiji.app" / "ImageJ-win64.exe",
                Path.home() / "Downloads" / "Fiji.app" / "fiji-windows-x64.exe",
                Path.home() / "Downloads" / "Fiji" / "Fiji.app" / "ImageJ-win64.exe",
                Path.home() / "Downloads" / "Fiji" / "Fiji.app" / "fiji-windows-x64.exe",
            ]
        )
    elif sys.platform == "darwin":
        raw_candidates.extend(
            [
                Path("/Applications/Fiji.app"),
                Path("/Applications/Fiji.app/Contents/MacOS/ImageJ-macosx"),

                Path.home() / "Applications/Fiji.app",
                Path.home() / "Applications/Fiji.app/Contents/MacOS/ImageJ-macosx",

                Path.home() / "Downloads/Fiji.app",
                Path.home() / "Downloads/Fiji.app/Contents/MacOS/ImageJ-macosx",

                Path.home() / "Downloads/Fiji/Fiji.app",
                Path.home() / "Downloads/Fiji/Fiji.app/Contents/MacOS/ImageJ-macosx",
            ]
        )
    else:
        raw_candidates.extend(
            [
                Path("/opt/Fiji.app/ImageJ-linux64"),
                Path("/usr/local/Fiji.app/ImageJ-linux64"),
                Path.home() / "Fiji.app/ImageJ-linux64",
            ]
        )

    for raw_candidate in raw_candidates:
        resolved = resolve_fiji_executable(raw_candidate)
        if resolved.exists() and resolved.is_file():
            return resolved

    for executable_name in (
            "ImageJ-win64.exe",
            "fiji-windows-x64.exe",
            "ImageJ-macosx",
            "fiji-macosx",
            "ImageJ-linux64",
            "fiji",
    ):
        found = shutil.which(executable_name)
        if not found:
            continue

        found_path = Path(found)

        lowered_parts = {part.lower() for part in found_path.parts}

        if ".venv" in lowered_parts or ".venv311" in lowered_parts or "scripts" in lowered_parts:
            continue

        return found_path

    raise RuntimeError(
        "Fiji executable not found.\n\n"
        "Please configure Fiji in Setup.\n\n"
        "macOS example:\n"
        "/Applications/Fiji.app\n\n"
        "Resolved executable should become:\n"
        "/Applications/Fiji.app/Contents/MacOS/ImageJ-macosx\n\n"
        "Windows example:\n"
        "C:\\Praktikum_docs\\Fiji\\fiji-windows-x64.exe"
    )