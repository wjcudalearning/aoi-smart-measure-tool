import cv2
import numpy as np

from aoi_system.algorithms.backend.manager import BackendManager, DeviceBackend
from aoi_system.core.models.recipe import DualThresholdSnapshot, PreprocessSnapshot


class PreprocessPipeline:
    """High-speed image preprocessing pipeline supporting both CPU and GPU backends."""

    def __init__(self, backend_manager: BackendManager | None = None):
        self.backend = backend_manager or BackendManager()

    def apply_preprocess(self, image: np.ndarray, config: PreprocessSnapshot) -> np.ndarray:
        if not config.enabled:
            return image.copy()

        # Ensure grayscale
        gray = self._to_grayscale(image)

        # 1. Thresholding
        if config.use_dual_threshold:
            binary = self._apply_range_threshold(gray, config.threshold, config.upper_threshold)
        else:
            _, binary = cv2.threshold(
                gray,
                config.threshold,
                config.upper_threshold,
                cv2.THRESH_BINARY,
            )

        # 2. Morphology operations
        processed = self._apply_morphology(
            binary,
            erode_iter=config.erode_iterations,
            dilate_iter=config.dilate_iterations,
            open_iter=config.open_iterations,
            close_iter=config.close_iterations,
        )
        return processed

    def apply_dual_threshold(self, image: np.ndarray, config: DualThresholdSnapshot) -> np.ndarray:
        if not config.enabled:
            return image.copy()

        gray = self._to_grayscale(image)
        binary = self._apply_range_threshold(gray, config.lower_threshold, config.upper_threshold)

        processed = self._apply_morphology(
            binary,
            erode_iter=config.erode_iterations,
            dilate_iter=config.dilate_iterations,
            open_iter=config.open_iterations,
            close_iter=config.close_iterations,
        )
        return processed

    def _to_grayscale(self, img: np.ndarray) -> np.ndarray:
        if img.ndim == 3 and img.shape[2] == 3:
            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    def _apply_range_threshold(self, gray: np.ndarray, lower: int, upper: int) -> np.ndarray:
        # GPU accelerated path if available
        if self.backend.current_backend == DeviceBackend.CUDA:
            try:
                cp = self.backend._cupy
                if cp is not None:
                    d_gray = self.backend.to_device(gray)
                    d_mask = (d_gray >= lower) & (d_gray <= upper)
                    d_out = cp.zeros_like(d_gray)
                    d_out[d_mask] = 255
                    return np.asarray(self.backend.to_host(d_out))
            except Exception:
                pass

        # CPU Fallback
        mask = (gray >= lower) & (gray <= upper)
        out = np.zeros_like(gray, dtype=np.uint8)
        out[mask] = 255
        return out

    def _apply_morphology(
        self,
        binary: np.ndarray,
        erode_iter: int = 0,
        dilate_iter: int = 0,
        open_iter: int = 0,
        close_iter: int = 0,
    ) -> np.ndarray:
        result = binary
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))

        if erode_iter > 0:
            result = cv2.erode(result, kernel, iterations=erode_iter)
        if dilate_iter > 0:
            result = cv2.dilate(result, kernel, iterations=dilate_iter)
        if open_iter > 0:
            result = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel, iterations=open_iter)
        if close_iter > 0:
            result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel, iterations=close_iter)

        return result
