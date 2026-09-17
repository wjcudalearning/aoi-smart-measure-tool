from typing import Any

import cv2
import numpy as np

from aoi_system.algorithms.backend.base import ComputeBackend


class NumPyCpuBackend(ComputeBackend):
    """CPU fallback compute backend powered by NumPy SIMD and OpenCV CPU."""

    @property
    def name(self) -> str:
        return "NUMPY"

    def is_available(self) -> bool:
        return True

    def to_device(self, arr: np.ndarray) -> Any:
        return arr

    def to_host(self, arr: Any) -> np.ndarray:
        return np.asarray(arr)

    def threshold(
        self, image: np.ndarray, thresh: float, maxval: float = 255.0, type: int = cv2.THRESH_BINARY
    ) -> np.ndarray:
        _, binary = cv2.threshold(image, thresh, maxval, type)
        return binary

    def range_threshold(self, image: np.ndarray, lower: int, upper: int) -> np.ndarray:
        mask = (image >= lower) & (image <= upper)
        out = np.zeros_like(image, dtype=np.uint8)
        out[mask] = 255
        return out

    def dual_threshold(
        self, image: np.ndarray, low_min: int, low_max: int, high_min: int, high_max: int
    ) -> np.ndarray:
        mask = ((image >= low_min) & (image <= low_max)) | (
            (image >= high_min) & (image <= high_max)
        )
        out = np.zeros_like(image, dtype=np.uint8)
        out[mask] = 255
        return out

    def morphology(
        self,
        image: np.ndarray,
        op: str,
        kernel_size: int = 3,
        iterations: int = 1,
    ) -> np.ndarray:
        if iterations <= 0:
            return image

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        op_lower = op.lower()
        if op_lower == "erode":
            return cv2.erode(image, kernel, iterations=iterations)
        elif op_lower == "dilate":
            return cv2.dilate(image, kernel, iterations=iterations)
        elif op_lower == "open":
            return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel, iterations=iterations)
        elif op_lower == "close":
            return cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel, iterations=iterations)
        return image

    def gaussian_blur(
        self, image: np.ndarray, kernel_size: int = 5, sigma: float = 1.0
    ) -> np.ndarray:
        ksize = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
        return cv2.GaussianBlur(image, (ksize, ksize), sigma)
