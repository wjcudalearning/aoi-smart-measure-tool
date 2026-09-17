"""Standalone executable packaging script using PyInstaller."""

import subprocess
import sys


def build() -> None:
    print("[INFO] Building AOI Standalone Executable with PyInstaller...")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name",
        "AOISmartMeasureTool",
        "--collect-all",
        "aoi_system",
        "--collect-all",
        "PySide6",
        "--hidden-import",
        "cv2",
        "--hidden-import",
        "numpy",
        "--hidden-import",
        "pydantic",
        "--hidden-import",
        "loguru",
        "main.py",
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode == 0:
        print("[SUCCESS] Build completed! Binary output at dist/AOISmartMeasureTool/")
    else:
        print(f"[ERROR] Build failed with returncode {result.returncode}")


if __name__ == "__main__":
    build()
