from typing import Any

import numpy as np

from aoi_system.algorithms.backend.base import ComputeBackend
from aoi_system.algorithms.backend.numpy_backend import NumPyCpuBackend


class CuPyBackend(ComputeBackend):
    """GPU-accelerated backend using CuPy array operations."""

    def __init__(self) -> None:
        self._cpu_fallback = NumPyCpuBackend()
        self._cupy: Any = None
        self._available = False

        try:
            import cupy as cp

            if cp.cuda.is_available():
                self._cupy = cp
                self._available = True
        except (ImportError, Exception):
            self._cupy = None
            self._available = False

    @property
    def name(self) -> str:
        return "CUPY"

    def is_available(self) -> bool:
        return self._available

    def to_device(self, arr: np.ndarray) -> Any:
        if self._available and self._cupy is not None:
            return self._cupy.asarray(arr)
        return arr

    def to_host(self, arr: Any) -> np.ndarray:
        if hasattr(arr, "get"):
            return np.asarray(arr.get())
        return np.asarray(arr)

    def threshold(
        self, image: np.ndarray, thresh: float, maxval: float = 255.0, type: int = 0
    ) -> np.ndarray:
        if not self._available or self._cupy is None:
            return self._cpu_fallback.threshold(image, thresh, maxval, type)

        cp = self._cupy
        try:
            d_img = cp.asarray(image)
            d_out = cp.where(d_img > thresh, cp.uint8(maxval), cp.uint8(0))
            return np.asarray(cp.asnumpy(d_out))
        except Exception:
            return self._cpu_fallback.threshold(image, thresh, maxval, type)

    def range_threshold(self, image: np.ndarray, lower: int, upper: int) -> np.ndarray:
        if not self._available or self._cupy is None:
            return self._cpu_fallback.range_threshold(image, lower, upper)

        cp = self._cupy
        try:
            d_img = cp.asarray(image)
            d_mask = (d_img >= lower) & (d_img <= upper)
            d_out = cp.zeros_like(d_img, dtype=cp.uint8)
            d_out[d_mask] = 255
            return np.asarray(cp.asnumpy(d_out))
        except Exception:
            return self._cpu_fallback.range_threshold(image, lower, upper)

    def dual_threshold(
        self, image: np.ndarray, low_min: int, low_max: int, high_min: int, high_max: int
    ) -> np.ndarray:
        if not self._available or self._cupy is None:
            return self._cpu_fallback.dual_threshold(image, low_min, low_max, high_min, high_max)

        cp = self._cupy
        try:
            d_img = cp.asarray(image)
            d_mask = ((d_img >= low_min) & (d_img <= low_max)) | (
                (d_img >= high_min) & (d_img <= high_max)
            )
            d_out = cp.zeros_like(d_img, dtype=cp.uint8)
            d_out[d_mask] = 255
            return np.asarray(cp.asnumpy(d_out))
        except Exception:
            return self._cpu_fallback.dual_threshold(image, low_min, low_max, high_min, high_max)

    def morphology(
        self,
        image: np.ndarray,
        op: str,
        kernel_size: int = 3,
        iterations: int = 1,
    ) -> np.ndarray:
        return self._cpu_fallback.morphology(image, op, kernel_size, iterations)

    def gaussian_blur(
        self, image: np.ndarray, kernel_size: int = 5, sigma: float = 1.0
    ) -> np.ndarray:
        return self._cpu_fallback.gaussian_blur(image, kernel_size, sigma)
