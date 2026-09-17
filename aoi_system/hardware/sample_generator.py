"""Industrial AOI Test Sample Image Generator.

Synthesizes realistic industrial workpiece images with reference corners,
precision dimension boundaries, circular holes, and surface defects.
"""

from pathlib import Path

import cv2
import numpy as np


def generate_sample_ok(width: int = 800, height: int = 600) -> np.ndarray:
    """Generate a standard OK workpiece (Grade A).

    Features:
    - Base canvas: Dark background (industrial conveyor / backdrop).
    - Workpiece: Rectangular metallic part at (150, 120), size 500x320.
    - Reference corner: Top-left sharp corner at (150, 120).
    - Precision circular hole: Center (400, 280), Radius 45.
    - Clean surface, crisp edges.
    """
    canvas = np.full((height, width), 30, dtype=np.uint8)

    # Workpiece body (gray: ~210)
    wx, wy, ww, wh = 150, 120, 500, 320
    canvas[wy : wy + wh, wx : wx + ww] = 210

    # Chamfer bottom-right corner to make reference corner (top-left) distinct
    pts = np.array([[wx + ww - 40, wy + wh], [wx + ww, wy + wh - 40], [wx + ww, wy + wh]])
    cv2.fillPoly(canvas, [pts], 30)

    # Center circular hole (drilled hole, dark)
    cv2.circle(canvas, (wx + 250, wy + 160), 45, 35, -1)

    # Inner alignment notch near top edge
    canvas[wy : wy + 15, wx + 180 : wx + 200] = 30

    # Add realistic subtle sensor noise
    noise = np.random.normal(0, 1.5, canvas.shape).astype(np.int16)
    noisy: np.ndarray = np.asarray(np.clip(canvas.astype(np.int16) + noise, 0, 255), dtype=np.uint8)
    return noisy


def generate_sample_dimension_ng(width: int = 800, height: int = 600) -> np.ndarray:
    """Generate an oversized workpiece exceeding tolerance limits (Grade NG).

    Features:
    - Same base as OK, but width stretched by +35px (535px) and hole enlarged (Radius 58px).
    """
    canvas = np.full((height, width), 30, dtype=np.uint8)
    wx, wy, ww, wh = 150, 120, 535, 320
    canvas[wy : wy + wh, wx : wx + ww] = 210

    pts = np.array([[wx + ww - 40, wy + wh], [wx + ww, wy + wh - 40], [wx + ww, wy + wh]])
    cv2.fillPoly(canvas, [pts], 30)

    # Oversized hole (58px instead of 45px)
    cv2.circle(canvas, (wx + 250, wy + 160), 58, 35, -1)
    canvas[wy : wy + 15, wx + 180 : wx + 200] = 30

    noise = np.random.normal(0, 1.5, canvas.shape).astype(np.int16)
    noisy: np.ndarray = np.asarray(np.clip(canvas.astype(np.int16) + noise, 0, 255), dtype=np.uint8)
    return noisy


def generate_sample_defect(width: int = 800, height: int = 600) -> np.ndarray:
    """Generate a workpiece with surface scratches, stains, and blob defects (Grade NG)."""
    img = generate_sample_ok(width, height)

    # Add dark scratches across the surface
    cv2.line(img, (220, 180), (320, 240), 50, 3)
    cv2.line(img, (480, 210), (530, 290), 40, 2)

    # Add dark oil spot blob
    cv2.circle(img, (320, 340), 16, 60, -1)
    cv2.ellipse(img, (520, 160), (22, 10), 30, 0, 360, 55, -1)

    return img


def generate_sample_rotated(
    angle_deg: float = 6.0,
    dx: int = 25,
    dy: int = 15,
    width: int = 800,
    height: int = 600,
) -> np.ndarray:
    """Generate a rotated and translated workpiece to test alignment coordinate transformation."""
    base = generate_sample_ok(width, height)
    center = (width // 2, height // 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    rot_mat[0, 2] += dx
    rot_mat[1, 2] += dy

    rotated = cv2.warpAffine(base, rot_mat, (width, height), borderValue=30)
    return rotated


def generate_standard_dataset(output_dir: str | Path = "sample_data/images") -> dict[str, Path]:
    """Generate the 4 standard golden sample images and save to output directory."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    samples = {
        "sample_01_standard_ok.png": generate_sample_ok(),
        "sample_02_dimension_large_ng.png": generate_sample_dimension_ng(),
        "sample_03_surface_scratch_defect.png": generate_sample_defect(),
        "sample_04_rotated_alignment.png": generate_sample_rotated(),
    }

    results: dict[str, Path] = {}
    for filename, img in samples.items():
        file_path = out_path / filename
        cv2.imwrite(str(file_path), img)
        results[filename] = file_path

    return results


if __name__ == "__main__":
    generated = generate_standard_dataset()
    for name, path in generated.items():
        print(f"Generated test image: {name} -> {path}")
