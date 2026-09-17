from unittest.mock import MagicMock

import numpy as np
import pytest

from aoi_system.algorithms.backend.base import ComputeBackend
from aoi_system.algorithms.backend.cuda_cv_backend import CudaOpenCVBackend
from aoi_system.algorithms.backend.cupy_backend import CuPyBackend
from aoi_system.algorithms.backend.manager import BackendManager, DeviceBackend
from aoi_system.algorithms.backend.numpy_backend import NumPyCpuBackend
from aoi_system.algorithms.backend.onnx_backend import OnnxInferenceBackend
from aoi_system.algorithms.preprocess.filters import PreprocessPipeline
from aoi_system.core.models.recipe import DualThresholdSnapshot, PreprocessSnapshot


class TestComputeBackends:
    @pytest.fixture
    def sample_gray(self) -> np.ndarray:
        img = np.zeros((100, 100), dtype=np.uint8)
        img[30:70, 30:70] = 180
        img[45:55, 45:55] = 240
        return img

    def test_numpy_backend_operations(self, sample_gray: np.ndarray) -> None:
        backend = NumPyCpuBackend()
        assert backend.name == "NUMPY"
        assert backend.is_available() is True

        # Host/device identity in CPU
        dev = backend.to_device(sample_gray)
        host = backend.to_host(dev)
        assert np.array_equal(sample_gray, host)

        # Threshold
        th = backend.threshold(sample_gray, 100, 255)
        assert th.shape == sample_gray.shape
        assert th[50, 50] == 255
        assert th[10, 10] == 0

        # Range threshold
        rng = backend.range_threshold(sample_gray, 150, 200)
        assert rng[35, 35] == 255
        assert rng[50, 50] == 0  # 240 is out of [150, 200]

        # Dual threshold
        dual = backend.dual_threshold(
            sample_gray, low_min=150, low_max=200, high_min=230, high_max=255
        )
        assert dual[35, 35] == 255
        assert dual[50, 50] == 255
        assert dual[10, 10] == 0

        # Morphology
        eroded = backend.morphology(th, op="erode", kernel_size=3, iterations=1)
        assert eroded.shape == th.shape
        assert np.sum(eroded) <= np.sum(th)

        dilated = backend.morphology(th, op="dilate", kernel_size=3, iterations=1)
        assert dilated.shape == th.shape
        assert np.sum(dilated) >= np.sum(th)

        opened = backend.morphology(th, op="open", kernel_size=3, iterations=1)
        assert opened.shape == th.shape

        closed = backend.morphology(th, op="close", kernel_size=3, iterations=1)
        assert closed.shape == th.shape

        noop = backend.morphology(th, op="erode", iterations=0)
        assert np.array_equal(noop, th)

        # Blur
        blurred = backend.gaussian_blur(sample_gray, kernel_size=5, sigma=1.0)
        assert blurred.shape == sample_gray.shape
        assert blurred.dtype == np.uint8

    def test_cupy_backend_graceful_handling(self, sample_gray: np.ndarray) -> None:
        backend = CuPyBackend()
        assert backend.name == "CUPY"
        avail = backend.is_available()
        assert isinstance(avail, bool)

        # Fallback operations succeed
        res = backend.range_threshold(sample_gray, 150, 200)
        assert res.shape == sample_gray.shape
        assert res[35, 35] == 255

        dual = backend.dual_threshold(sample_gray, 150, 200, 230, 255)
        assert dual.shape == sample_gray.shape

        th = backend.threshold(sample_gray, 100, 255)
        assert th.shape == sample_gray.shape

        morph = backend.morphology(th, op="erode", kernel_size=3, iterations=1)
        assert morph.shape == th.shape

        blur = backend.gaussian_blur(sample_gray, kernel_size=5, sigma=1.0)
        assert blur.shape == sample_gray.shape

        # Test to_host with object having .get()
        class FakeGpuArray:
            def get(self) -> np.ndarray:
                return sample_gray

        assert np.array_equal(backend.to_host(FakeGpuArray()), sample_gray)

    def test_cupy_backend_mock_gpu_path(self, sample_gray: np.ndarray) -> None:
        backend = CuPyBackend()
        backend._available = True
        mock_cp = MagicMock()
        mock_cp.asarray.return_value = sample_gray
        mock_cp.zeros_like.return_value = np.zeros_like(sample_gray)
        mock_cp.where.return_value = sample_gray
        mock_cp.asnumpy.side_effect = lambda x: x
        backend._cupy = mock_cp

        res = backend.range_threshold(sample_gray, 150, 200)
        assert res.shape == sample_gray.shape

        dual = backend.dual_threshold(sample_gray, 150, 200, 230, 255)
        assert dual.shape == sample_gray.shape

        th = backend.threshold(sample_gray, 100, 255)
        assert th.shape == sample_gray.shape

        dev = backend.to_device(sample_gray)
        assert dev is not None

    def test_cuda_cv_backend_graceful_handling(self, sample_gray: np.ndarray) -> None:
        backend = CudaOpenCVBackend()
        assert backend.name == "CUDA_CV"
        avail = backend.is_available()
        assert isinstance(avail, bool)

        th = backend.threshold(sample_gray, 100, 255)
        assert th.shape == sample_gray.shape
        assert th[50, 50] == 255

        rng = backend.range_threshold(sample_gray, 150, 200)
        assert rng.shape == sample_gray.shape

        dual = backend.dual_threshold(sample_gray, 150, 200, 230, 255)
        assert dual.shape == sample_gray.shape

        morph = backend.morphology(th, op="dilate", kernel_size=3, iterations=1)
        assert morph.shape == sample_gray.shape

        blurred = backend.gaussian_blur(sample_gray, kernel_size=5, sigma=1.0)
        assert blurred.shape == sample_gray.shape

        # Test to_host with object having .download()
        class FakeGpuMat:
            def download(self) -> np.ndarray:
                return sample_gray

        assert np.array_equal(backend.to_host(FakeGpuMat()), sample_gray)

    def test_cuda_cv_backend_mock_gpu_path(self, sample_gray: np.ndarray) -> None:
        backend = CudaOpenCVBackend()
        backend._available = True
        mock_cuda = MagicMock()
        fake_gpu_mat = MagicMock()
        fake_gpu_mat.download.return_value = sample_gray
        mock_cuda.GpuMat.return_value = fake_gpu_mat
        mock_cuda.threshold.return_value = (0, fake_gpu_mat)
        mock_cuda.bitwise_and.return_value = fake_gpu_mat
        mock_cuda.bitwise_or.return_value = fake_gpu_mat
        mock_filter = MagicMock()
        mock_filter.apply.return_value = fake_gpu_mat
        mock_cuda.createMorphologyFilter.return_value = mock_filter
        mock_cuda.createGaussianFilter.return_value = mock_filter
        backend._cuda = mock_cuda

        th = backend.threshold(sample_gray, 100, 255)
        assert np.array_equal(th, sample_gray)

        rng = backend.range_threshold(sample_gray, 150, 200)
        assert np.array_equal(rng, sample_gray)

        dual = backend.dual_threshold(sample_gray, 150, 200, 230, 255)
        assert np.array_equal(dual, sample_gray)

        morph = backend.morphology(sample_gray, "erode", kernel_size=3, iterations=1)
        assert np.array_equal(morph, sample_gray)

        blur = backend.gaussian_blur(sample_gray, kernel_size=5, sigma=1.0)
        assert np.array_equal(blur, sample_gray)

        dev = backend.to_device(sample_gray)
        assert dev == fake_gpu_mat

    def test_onnx_backend_providers(self) -> None:
        onnx_backend = OnnxInferenceBackend()
        assert onnx_backend.name == "ONNX"
        providers = onnx_backend.get_available_providers()
        assert isinstance(providers, list)
        assert onnx_backend.is_loaded is False

        # Load non-existent model should gracefully return False
        assert onnx_backend.load_model("non_existent.onnx") is False

        with pytest.raises(RuntimeError):
            onnx_backend.infer(np.zeros((1, 1, 10, 10), dtype=np.float32))

    def test_backend_manager_integration(self, sample_gray: np.ndarray) -> None:
        mgr_cpu = BackendManager(force_cpu=True)
        assert mgr_cpu.current_backend == DeviceBackend.CPU
        assert mgr_cpu.active_backend.name == "NUMPY"

        mgr_auto = BackendManager()
        assert mgr_auto.active_backend is not None
        assert isinstance(mgr_auto.active_backend, ComputeBackend)

        mgr_auto.set_backend("NUMPY")
        assert mgr_auto.active_backend.name == "NUMPY"
        assert mgr_auto.current_backend == DeviceBackend.CPU

        mgr_auto.set_backend("CUDA_CV")
        assert mgr_auto.active_backend.name == "CUDA_CV"
        assert mgr_auto.current_backend == DeviceBackend.CUDA_CV

        mgr_auto.set_backend("CUPY")
        assert mgr_auto.active_backend.name == "CUPY"
        assert mgr_auto.current_backend == DeviceBackend.CUDA

        with pytest.raises(ValueError):
            mgr_auto.set_backend("NON_EXISTENT_BACKEND")

        out = mgr_auto.active_backend.range_threshold(sample_gray, 150, 200)
        assert out[35, 35] == 255

        dev = mgr_auto.to_device(sample_gray)
        host = mgr_auto.to_host(dev)
        assert host.shape == sample_gray.shape

        assert mgr_auto.onnx is not None

    def test_preprocess_pipeline_with_backends(self, sample_gray: np.ndarray) -> None:
        mgr = BackendManager(force_cpu=True)
        pipeline = PreprocessPipeline(backend_manager=mgr)

        cfg_single = PreprocessSnapshot(
            enabled=True,
            threshold=100,
            upper_threshold=255,
            use_dual_threshold=False,
            erode_iterations=1,
            dilate_iterations=1,
        )
        res_single = pipeline.apply_preprocess(sample_gray, cfg_single)
        assert res_single.shape == sample_gray.shape

        cfg_dual = DualThresholdSnapshot(
            enabled=True,
            lower_threshold=150,
            upper_threshold=200,
            open_iterations=1,
            close_iterations=1,
        )
        res_dual = pipeline.apply_dual_threshold(sample_gray, cfg_dual)
        assert res_dual.shape == sample_gray.shape

        # Disabled config returns copy
        cfg_disabled = PreprocessSnapshot(enabled=False)
        res_disabled = pipeline.apply_preprocess(sample_gray, cfg_disabled)
        assert np.array_equal(res_disabled, sample_gray)
