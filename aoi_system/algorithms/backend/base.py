from abc import ABC, abstractmethod
from typing import Any

import numpy as np


class ComputeBackend(ABC):
    """Abstract interface for image processing compute backends (CPU, CuPy, OpenCV-CUDA)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the backend."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Whether the backend hardware/library dependencies are currently available."""
        pass

    @abstractmethod
    def to_device(self, arr: np.ndarray) -> Any:
        """Transfer numpy host array to backend device memory."""
        pass

    @abstractmethod
    def to_host(self, arr: Any) -> np.ndarray:
        """Transfer backend device memory back to host numpy array."""
        pass

    @abstractmethod
    def threshold(
        self, image: np.ndarray, thresh: float, maxval: float = 255.0, type: int = 0
    ) -> np.ndarray:
        """Binary thresholding."""
        pass

    @abstractmethod
    def range_threshold(self, image: np.ndarray, lower: int, upper: int) -> np.ndarray:
        """In-range binary thresholding ([lower, upper] -> 255, else 0)."""
        pass

    @abstractmethod
    def dual_threshold(
        self, image: np.ndarray, low_min: int, low_max: int, high_min: int, high_max: int
    ) -> np.ndarray:
        """Dual range thresholding (([low_min, low_max] | [high_min, high_max]) -> 255)."""
        pass

    @abstractmethod
    def morphology(
        self,
        image: np.ndarray,
        op: str,
        kernel_size: int = 3,
        iterations: int = 1,
    ) -> np.ndarray:
        """Morphological operation ('erode', 'dilate', 'open', 'close')."""
        pass

    @abstractmethod
    def gaussian_blur(
        self, image: np.ndarray, kernel_size: int = 5, sigma: float = 1.0
    ) -> np.ndarray:
        """Gaussian smoothing blur."""
        pass
