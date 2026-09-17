from typing import Any

import cv2
import numpy as np

from aoi_system.algorithms.backend.base import ComputeBackend
from aoi_system.algorithms.backend.numpy_backend import NumPyCpuBackend


class CudaOpenCVBackend(ComputeBackend):
    """OpenCV-CUDA accelerated backend using cv2.cuda.GpuMat and CUDA streams."""

    def __init__(self) -> None:
        self._cpu_fallback = NumPyCpuBackend()
        self._available = False
        self._cuda: Any = getattr(cv2, "cuda", None)
        self._stream: Any = None

        try:
            if self._cuda is not None and self._cuda.getCudaEnabledDeviceCount() > 0:
                self._stream = self._cuda.Stream()
                self._available = True
        except Exception:
            self._available = False

    @property
    def name(self) -> str:
        return "CUDA_CV"

    def is_available(self) -> bool:
        return self._available

    def to_device(self, arr: np.ndarray) -> Any:
        if self._available and self._cuda is not None:
            try:
                gpu_mat = self._cuda.GpuMat()
                gpu_mat.upload(arr)
                return gpu_mat
            except Exception:
                pass
        return arr

    def to_host(self, arr: Any) -> np.ndarray:
        if hasattr(arr, "download"):
            return np.asarray(arr.download())
        return np.asarray(arr)

    def threshold(
        self, image: np.ndarray, thresh: float, maxval: float = 255.0, type: int = cv2.THRESH_BINARY
    ) -> np.ndarray:
        if not self._available or self._cuda is None:
            return self._cpu_fallback.threshold(image, thresh, maxval, type)

        try:
            gpu_img = self._cuda.GpuMat()
            gpu_img.upload(image)
            _, gpu_dst = self._cuda.threshold(gpu_img, thresh, maxval, type)
            return np.asarray(gpu_dst.download())
        except Exception:
            return self._cpu_fallback.threshold(image, thresh, maxval, type)

    def range_threshold(self, image: np.ndarray, lower: int, upper: int) -> np.ndarray:
        if not self._available or self._cuda is None:
            return self._cpu_fallback.range_threshold(image, lower, upper)

        try:
            gpu_img = self._cuda.GpuMat()
            gpu_img.upload(image)
            _, gpu_low = self._cuda.threshold(gpu_img, lower - 0.5, 255, cv2.THRESH_BINARY)
            _, gpu_high = self._cuda.threshold(gpu_img, upper + 0.5, 255, cv2.THRESH_BINARY_INV)
            gpu_dst = self._cuda.bitwise_and(gpu_low, gpu_high)
            return np.asarray(gpu_dst.download())
        except Exception:
            return self._cpu_fallback.range_threshold(image, lower, upper)

    def dual_threshold(
        self, image: np.ndarray, low_min: int, low_max: int, high_min: int, high_max: int
    ) -> np.ndarray:
        if not self._available or self._cuda is None:
            return self._cpu_fallback.dual_threshold(image, low_min, low_max, high_min, high_max)

        try:
            gpu_img = self._cuda.GpuMat()
            gpu_img.upload(image)
            _, l1 = self._cuda.threshold(gpu_img, low_min - 0.5, 255, cv2.THRESH_BINARY)
            _, l2 = self._cuda.threshold(gpu_img, low_max + 0.5, 255, cv2.THRESH_BINARY_INV)
            band1 = self._cuda.bitwise_and(l1, l2)

            _, h1 = self._cuda.threshold(gpu_img, high_min - 0.5, 255, cv2.THRESH_BINARY)
            _, h2 = self._cuda.threshold(gpu_img, high_max + 0.5, 255, cv2.THRESH_BINARY_INV)
            band2 = self._cuda.bitwise_and(h1, h2)

            gpu_dst = self._cuda.bitwise_or(band1, band2)
            return np.asarray(gpu_dst.download())
        except Exception:
            return self._cpu_fallback.dual_threshold(image, low_min, low_max, high_min, high_max)

    def morphology(
        self,
        image: np.ndarray,
        op: str,
        kernel_size: int = 3,
        iterations: int = 1,
    ) -> np.ndarray:
        if not self._available or self._cuda is None or iterations <= 0:
            return self._cpu_fallback.morphology(image, op, kernel_size, iterations)

        try:
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
            op_map = {
                "erode": cv2.MORPH_ERODE,
                "dilate": cv2.MORPH_DILATE,
                "open": cv2.MORPH_OPEN,
                "close": cv2.MORPH_CLOSE,
            }
            morph_op = op_map.get(op.lower())
            if morph_op is None:
                return image

            morph_filter = self._cuda.createMorphologyFilter(
                morph_op, cv2.CV_8UC1, kernel, iterations=iterations
            )
            gpu_img = self._cuda.GpuMat()
            gpu_img.upload(image)
            gpu_dst = morph_filter.apply(gpu_img)
            return np.asarray(gpu_dst.download())
        except Exception:
            return self._cpu_fallback.morphology(image, op, kernel_size, iterations)

    def gaussian_blur(
        self, image: np.ndarray, kernel_size: int = 5, sigma: float = 1.0
    ) -> np.ndarray:
        if not self._available or self._cuda is None:
            return self._cpu_fallback.gaussian_blur(image, kernel_size, sigma)

        try:
            ksize = kernel_size if kernel_size % 2 == 1 else kernel_size + 1
            blur_filter = self._cuda.createGaussianFilter(
                cv2.CV_8UC1, cv2.CV_8UC1, (ksize, ksize), sigma
            )
            gpu_img = self._cuda.GpuMat()
            gpu_img.upload(image)
            gpu_dst = blur_filter.apply(gpu_img)
            return np.asarray(gpu_dst.download())
        except Exception:
            return self._cpu_fallback.gaussian_blur(image, kernel_size, sigma)
