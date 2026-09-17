import cv2
import numpy as np

from aoi_system.algorithms.backend.manager import BackendManager
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
            binary = self.backend.active_backend.range_threshold(
                gray, int(config.threshold), int(config.upper_threshold)
            )
        else:
            binary = self.backend.active_backend.threshold(
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
        binary = self.backend.active_backend.range_threshold(
            gray, config.lower_threshold, config.upper_threshold
        )

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
        return self.backend.active_backend.range_threshold(gray, lower, upper)

    def _apply_morphology(
        self,
        binary: np.ndarray,
        erode_iter: int = 0,
        dilate_iter: int = 0,
        open_iter: int = 0,
        close_iter: int = 0,
    ) -> np.ndarray:
        result = binary
        if erode_iter > 0:
            result = self.backend.active_backend.morphology(result, "erode", iterations=erode_iter)
        if dilate_iter > 0:
            result = self.backend.active_backend.morphology(
                result, "dilate", iterations=dilate_iter
            )
        if open_iter > 0:
            result = self.backend.active_backend.morphology(result, "open", iterations=open_iter)
        if close_iter > 0:
            result = self.backend.active_backend.morphology(result, "close", iterations=close_iter)
        return result
