from enum import StrEnum
from typing import Any

import numpy as np
from loguru import logger


class DeviceBackend(StrEnum):
    CPU = "CPU"
    CUDA = "CUDA"


class BackendManager:
    """Manages computation backend (GPU CuPy / CUDA vs CPU NumPy)."""

    def __init__(self, force_cpu: bool = False):
        self._backend = DeviceBackend.CPU
        self._cupy = None

        if not force_cpu:
            try:
                import cupy as cp

                if cp.cuda.is_available():
                    self._cupy = cp
                    self._backend = DeviceBackend.CUDA
                    logger.info("GPU backend initialized with CUDA / CuPy.")
            except ImportError:
                logger.info("CuPy not detected. Falling back to CPU NumPy backend.")
            except Exception as e:
                logger.warning(f"Failed to initialize CUDA backend: {e}. Falling back to CPU.")

    @property
    def current_backend(self) -> DeviceBackend:
        return self._backend

    @property
    def is_gpu_available(self) -> bool:
        return self._backend == DeviceBackend.CUDA

    def to_device(self, arr: np.ndarray) -> Any:
        if self._backend == DeviceBackend.CUDA and self._cupy is not None:
            return self._cupy.asarray(arr)
        return arr

    def to_host(self, arr: Any) -> np.ndarray[Any, Any]:
        if self._backend == DeviceBackend.CUDA and self._cupy is not None:
            if hasattr(arr, "get"):
                res: np.ndarray[Any, Any] = arr.get()
                return res
        return np.asarray(arr)
