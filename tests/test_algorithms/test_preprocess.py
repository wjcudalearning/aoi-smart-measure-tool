import numpy as np

from aoi_system.algorithms.backend.manager import BackendManager, DeviceBackend
from aoi_system.algorithms.preprocess.filters import PreprocessPipeline
from aoi_system.core.models.recipe import DualThresholdSnapshot, PreprocessSnapshot


def test_backend_manager_initialization():
    backend = BackendManager()
    assert backend.current_backend in (DeviceBackend.CUDA, DeviceBackend.CPU)


def test_single_threshold_binary():
    pipeline = PreprocessPipeline()
    img = np.array([[10, 50, 100], [120, 150, 200], [220, 240, 255]], dtype=np.uint8)

    cfg = PreprocessSnapshot(
        enabled=True,
        threshold=128,
        upper_threshold=255,
        use_dual_threshold=False,
    )
    result = pipeline.apply_preprocess(img, cfg)

    # Values > 128 should be 255, <= 128 should be 0
    expected = np.array([[0, 0, 0], [0, 255, 255], [255, 255, 255]], dtype=np.uint8)

    np.testing.assert_array_equal(result, expected)


def test_dual_threshold_filtering():
    pipeline = PreprocessPipeline()
    img = np.array([[30, 80, 120], [150, 180, 210], [220, 240, 250]], dtype=np.uint8)

    dual_cfg = DualThresholdSnapshot(
        enabled=True,
        lower_threshold=100,
        upper_threshold=200,
    )
    result = pipeline.apply_dual_threshold(img, dual_cfg)

    # Only pixels in range [100, 200] should be 255
    expected = np.array([[0, 0, 255], [255, 255, 0], [0, 0, 0]], dtype=np.uint8)

    np.testing.assert_array_equal(result, expected)


def test_morphology_operations():
    pipeline = PreprocessPipeline()
    img = np.zeros((10, 10), dtype=np.uint8)
    img[3:7, 3:7] = 255  # 4x4 white square

    cfg = PreprocessSnapshot(
        enabled=True,
        threshold=128,
        dilate_iterations=1,
    )
    result = pipeline.apply_preprocess(img, cfg)
    # Dilated image should have white area larger than 4x4
    assert np.count_nonzero(result) > 16
