import time

import numpy as np

from aoi_system.core.models.geometry import BoundingRect, Point2I
from aoi_system.core.models.measurement import MeasureDirectionMode, MeasureRecord
from aoi_system.core.models.recipe import (
    CameraCalibration,
    InspectionRecipe,
    JudgementCriterionRule,
    PreprocessSnapshot,
    ReferenceCornerPointMode,
    ReferenceCornerSnapshot,
)
from aoi_system.hardware.simulated_camera import SimulatedCamera
from aoi_system.pipeline.orchestrator import ContinuousInspectionOrchestrator


def create_sample_recipe(product_key: str = "SAMPLE_KEY") -> InspectionRecipe:
    recipe = InspectionRecipe(product_key=product_key)
    recipe.preprocess_snapshots[0] = PreprocessSnapshot(
        enabled=True,
        threshold=100,
        upper_threshold=255,
    )
    recipe.reference_corner = ReferenceCornerSnapshot(
        enabled=True,
        point_mode=ReferenceCornerPointMode.CONTOUR_NEAREST,
        roi=BoundingRect(x=10, y=10, width=150, height=150),
    )
    # Measure line
    recipe.measure_records.append(
        MeasureRecord(
            start_point=Point2I(x=20, y=30),
            end_point=Point2I(x=80, y=30),
            source_name="Preprocess 1",
            direction=MeasureDirectionMode.PARALLEL,
        )
    )
    # Judgement rule
    recipe.judgement_rules.append(
        JudgementCriterionRule(
            name="WidthSpec",
            calc_expression="(1)",
            spec_expression="0.25~0.35",  # 60px * 0.005mm = 0.30mm
        )
    )
    recipe.calibration = CameraCalibration(
        ccd_x_precision=0.005,
        ccd_y_precision=0.005,
        measurement_scale_factor=1.0,
    )
    return recipe


def test_simulated_camera():
    cam = SimulatedCamera(width=100, height=100)
    assert cam.connect() is True
    assert cam.is_connected is True

    frame = cam.grab_frame()
    assert frame is not None
    assert frame.shape == (100, 100)

    cam.disconnect()
    assert cam.is_connected is False


def test_continuous_orchestrator_single_slot():
    orchestrator = ContinuousInspectionOrchestrator()
    recipe = create_sample_recipe("PROD_A")
    orchestrator.set_slot_recipe(0, recipe)

    # Synthetic image: 200x200 black with a white rect at (20, 20, 60, 40)
    img = np.zeros((200, 200), dtype=np.uint8)
    img[20:60, 20:80] = 255

    res = orchestrator.load_and_judge(0, img, source_name="TestCam1")
    assert res.slot_index == 0
    assert res.summary == "A"
    assert len(res.rules) == 1
    assert res.rules[0].judgement == "A"

    # Check yield counts
    yield_stats = orchestrator.get_slot_yield(0)
    assert yield_stats["total"] == 1
    assert yield_stats["A"] == 1
    assert yield_stats["NG"] == 0


def test_continuous_orchestrator_multi_slot_concurrency():
    orchestrator = ContinuousInspectionOrchestrator()
    recipe = create_sample_recipe("PROD_B")
    orchestrator.set_slot_recipe(0, recipe)
    orchestrator.set_slot_recipe(1, recipe)
    orchestrator.set_slot_recipe(2, recipe)

    img = np.zeros((200, 200), dtype=np.uint8)
    img[20:60, 20:80] = 255

    # Concurrently execute on all 3 slots
    res0 = orchestrator.load_and_judge(0, img)
    res1 = orchestrator.load_and_judge(1, img)
    res2 = orchestrator.load_and_judge(2, img)

    assert res0.summary == "A"
    assert res1.summary == "A"
    assert res2.summary == "A"

    orchestrator.stop()


def test_continuous_orchestrator_async_queue_and_callbacks(tmp_path):
    orchestrator = ContinuousInspectionOrchestrator()
    recipe = create_sample_recipe("PROD_ASYNC")
    orchestrator.set_slot_recipe(0, recipe)

    # Enable raw image saving
    worker = orchestrator._workers[0]
    worker.save_raw_enabled = True
    worker.save_directory = tmp_path / "captures"

    results_received = []
    orchestrator.register_slot_callback(0, lambda r: results_received.append(r))

    img = np.zeros((200, 200), dtype=np.uint8)
    img[20:60, 20:80] = 255

    success = orchestrator.submit_async(0, img, source_name="AsyncTest")
    assert success is True

    # Wait for async processing
    time.sleep(0.5)
    assert len(results_received) >= 1
    assert results_received[0].summary == "A"

    # Reset slot yield
    orchestrator.reset_slot_yield(0)
    stats = orchestrator.get_slot_yield(0)
    assert stats["total"] == 0
    assert stats["A"] == 0

    orchestrator.stop()


def test_simulated_camera_streaming():
    cam = SimulatedCamera(width=64, height=64, fps=50.0)
    assert cam.connect() is True

    frames = []
    cam.register_frame_callback(lambda f: frames.append(f))
    cam.start_grabbing()
    time.sleep(0.15)
    cam.stop_grabbing()
    cam.disconnect()

    assert len(frames) > 0
    assert frames[0].shape == (64, 64)
