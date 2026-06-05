from __future__ import annotations

import asyncio
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from erdstall_pipeline.config import (
    FILES_DIR,
    RAW_FROM_PLY_FILENAME,
    SKELETON_FILENAME,
    SIZE,
)

from erdstall_pipeline.settings.app_settings import AppSettings

def _get_fiji_executable() -> Path:
    from erdstall_pipeline.utils.fiji_executable import find_fiji_executable

    return find_fiji_executable(AppSettings.get_fiji_exe())

def _count_nonzero_raw(path: Path) -> int:
    if not path.exists():
        return -1
    data = np.fromfile(str(path), dtype=np.uint8)
    return int(np.count_nonzero(data))


def _run_fiji_macro_blocking(macro_text: str) -> tuple[str, str]:
    fiji_exe = _get_fiji_executable()

    with tempfile.NamedTemporaryFile("w", suffix=".ijm", delete=False, encoding="utf-8") as tmp:
        tmp.write(macro_text)
        macro_path = Path(tmp.name)

    try:
        cmd = [
            str(fiji_exe),
            "--headless",
            "-macro",
            str(macro_path),
        ]

        print(f"[ImageJ] Running Fiji via: {fiji_exe}")
        print(f"[ImageJ] Macro file: {macro_path}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if stdout:
            print("[ImageJ][STDOUT]")
            print(stdout, end="" if stdout.endswith("\n") else "\n")

        if stderr:
            print("[ImageJ][STDERR]")
            print(stderr, end="" if stderr.endswith("\n") else "\n")

        if result.returncode != 0:
            raise RuntimeError(
                f"Fiji exited with code {result.returncode}\n"
                f"STDOUT:\n{stdout}\n"
                f"STDERR:\n{stderr}"
            )

        return stdout, stderr
    finally:
        try:
            macro_path.unlink(missing_ok=True)
        except Exception:
            pass


async def run_imagej():
    input_raw = FILES_DIR / RAW_FROM_PLY_FILENAME
    output_skel = FILES_DIR / SKELETON_FILENAME
    debug_mask = FILES_DIR / "mask_before_skeleton.raw"

    if not input_raw.exists():
        raise RuntimeError(f"Input raw file not found: {input_raw}")

    expected_bytes = SIZE * SIZE * SIZE
    actual_input_bytes = input_raw.stat().st_size
    if actual_input_bytes != expected_bytes:
        raise RuntimeError(
            f"Input raw file has wrong size: {input_raw} "
            f"(got {actual_input_bytes} bytes, expected {expected_bytes})"
        )

    input_nonzero = _count_nonzero_raw(input_raw)
    print(f"[ImageJ] Input raw: {input_raw}")
    print(f"[ImageJ] Input raw bytes: {actual_input_bytes}")
    print(f"[ImageJ] Input raw nonzero voxels: {input_nonzero}")

    ij_input = str(input_raw).replace("\\", "/")
    ij_out_skel = str(output_skel).replace("\\", "/")
    ij_mask_out = str(debug_mask).replace("\\", "/")

    # This macro saves the binary mask BEFORE skeletonization for debugging.
    macro = f"""
    print("\\\\Clear");
    print("[Macro] Opening raw volume...");
    run("Raw...", "open={ij_input} image=8-bit width={SIZE} height={SIZE} number={SIZE}");

    print("[Macro] Converting to binary mask...");
    setThreshold(1, 255);
    setOption("BlackBackground", false);
    run("Convert to Mask", "method=Default background=Dark black");

    print("[Macro] Saving debug mask...");
    saveAs("Raw Data", "{ij_mask_out}");

    print("[Macro] Running 3D skeletonization...");
    run("Skeletonize (2D/3D)");

    print("[Macro] Saving skeleton...");
    saveAs("Raw Data", "{ij_out_skel}");

    print("[Macro] Closing all windows...");
    close("*");
    """

    await asyncio.to_thread(_run_fiji_macro_blocking, macro)

    if not debug_mask.exists():
        raise RuntimeError(f"ImageJ did not create debug mask file: {debug_mask}")

    debug_mask_bytes = debug_mask.stat().st_size
    if debug_mask_bytes != expected_bytes:
        raise RuntimeError(
            f"ImageJ created invalid debug mask file: {debug_mask} "
            f"(got {debug_mask_bytes} bytes, expected {expected_bytes})"
        )

    debug_mask_nonzero = _count_nonzero_raw(debug_mask)
    print(f"[ImageJ] Debug mask: {debug_mask}")
    print(f"[ImageJ] Debug mask bytes: {debug_mask_bytes}")
    print(f"[ImageJ] Debug mask nonzero voxels: {debug_mask_nonzero}")

    if debug_mask_nonzero == 0:
        raise RuntimeError(
            "ImageJ created an empty binary mask before skeletonization. "
            "Thresholding / mask conversion failed."
        )

    if not output_skel.exists():
        raise RuntimeError(f"ImageJ did not create skeleton file: {output_skel}")

    actual_skel_bytes = output_skel.stat().st_size
    if actual_skel_bytes != expected_bytes:
        raise RuntimeError(
            f"ImageJ created invalid skeleton file: {output_skel} "
            f"(got {actual_skel_bytes} bytes, expected {expected_bytes})"
        )

    skel_nonzero = _count_nonzero_raw(output_skel)
    print(f"[ImageJ] Skeleton raw: {output_skel}")
    print(f"[ImageJ] Skeleton raw bytes: {actual_skel_bytes}")
    print(f"[ImageJ] Skeleton nonzero voxels: {skel_nonzero}")

    if skel_nonzero == 0:
        raise RuntimeError(
            "ImageJ created an empty skeleton. "
            "The binary mask exists, but skeletonization produced no voxels."
        )