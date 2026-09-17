from enum import StrEnum
from typing import Any

import numpy as np
from loguru import logger

from aoi_system.algorithms.backend.base import ComputeBackend
from aoi_system.algorithms.backend.cuda_cv_backend import CudaOpenCVBackend
from aoi_system.algorithms.backend.cupy_backend import CuPyBackend
from aoi_system.algorithms.backend.numpy_backend import NumPyCpuBackend
from aoi_system.algorithms.backend.onnx_backend import OnnxInferenceBackend


class DeviceBackend(StrEnum):
    CPU = "CPU"
    CUDA = "CUDA"
    CUDA_CV = "CUDA_CV"
    CUPY = "CUPY"
    NUMPY = "NUMPY"


class BackendManager:
    """Manages computation backends (GPU CuPy / OpenCV-CUDA vs CPU NumPy) and AI inference."""

    def __init__(self, force_cpu: bool = False):
        self._numpy_backend = NumPyCpuBackend()
        self._cupy_backend = CuPyBackend()
        self._cuda_cv_backend = CudaOpenCVBackend()
        self._onnx_backend = OnnxInferenceBackend()

        self._backends: dict[str, ComputeBackend] = {
            "NUMPY": self._numpy_backend,
            "CPU": self._numpy_backend,
            "CUPY": self._cupy_backend,
            "CUDA": self._cupy_backend,
            "CUDA_CV": self._cuda_cv_backend,
        }

        if force_cpu:
            self._active_backend: ComputeBackend = self._numpy_backend
            self._backend_type = DeviceBackend.CPU
            logger.info("BackendManager initialized with forced CPU mode.")
        elif self._cuda_cv_backend.is_available():
            self._active_backend = self._cuda_cv_backend
            self._backend_type = DeviceBackend.CUDA_CV
            logger.info("BackendManager initialized with OpenCV-CUDA acceleration.")
        elif self._cupy_backend.is_available():
            self._active_backend = self._cupy_backend
            self._backend_type = DeviceBackend.CUDA
            logger.info("BackendManager initialized with CuPy GPU acceleration.")
        else:
            self._active_backend = self._numpy_backend
            self._backend_type = DeviceBackend.CPU
            logger.info("No GPU backends detected. Falling back to CPU NumPy backend.")

    @property
    def active_backend(self) -> ComputeBackend:
        return self._active_backend

    @property
    def current_backend(self) -> DeviceBackend:
        return self._backend_type

    @property
    def is_gpu_available(self) -> bool:
        return self._cuda_cv_backend.is_available() or self._cupy_backend.is_available()

    @property
    def onnx(self) -> OnnxInferenceBackend:
        return self._onnx_backend

    def set_backend(self, name: str) -> None:
        key = name.upper()
        if key not in self._backends:
            raise ValueError(f"Unknown backend '{name}'. Available: {list(self._backends.keys())}")
        self._active_backend = self._backends[key]
        if key in ("NUMPY", "CPU"):
            self._backend_type = DeviceBackend.CPU
        elif key == "CUDA_CV":
            self._backend_type = DeviceBackend.CUDA_CV
        else:
            self._backend_type = DeviceBackend.CUDA
        logger.info(f"Switched active backend to {self._active_backend.name}")

    def to_device(self, arr: np.ndarray) -> Any:
        return self._active_backend.to_device(arr)

    def to_host(self, arr: Any) -> np.ndarray:
        return self._active_backend.to_host(arr)
