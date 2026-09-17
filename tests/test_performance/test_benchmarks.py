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
from aoi_system.pipeline.orchestrator import ContinuousInspectionOrchestrator


def test_throughput_benchmark_under_30ms():
    orchestrator = ContinuousInspectionOrchestrator()
    recipe = InspectionRecipe(product_key="PERF_PROD")
    recipe.preprocess_snapshots[0] = PreprocessSnapshot(
        enabled=True,
        threshold=128,
        upper_threshold=255,
    )
    recipe.reference_corner = ReferenceCornerSnapshot(
        enabled=True,
        point_mode=ReferenceCornerPointMode.CONTOUR_NEAREST,
        roi=BoundingRect(x=10, y=10, width=150, height=150),
    )
    recipe.measure_records.append(
        MeasureRecord(
            start_point=Point2I(x=20, y=30),
            end_point=Point2I(x=100, y=30),
            source_name="Preprocess 1",
            direction=MeasureDirectionMode.PARALLEL,
        )
    )
    recipe.judgement_rules.append(
        JudgementCriterionRule(
            name="Spec1",
            calc_expression="(1)",
            spec_expression="0.30~0.50",
        )
    )
    recipe.calibration = CameraCalibration(
        ccd_x_precision=0.005,
        ccd_y_precision=0.005,
        measurement_scale_factor=1.0,
    )

    orchestrator.set_slot_recipe(0, recipe)

    frame = np.zeros((300, 300), dtype=np.uint8)
    frame[20:100, 20:120] = 255

    # Run 30 consecutive inspection frames
    t0 = time.perf_counter()
    latencies = []
    for _ in range(30):
        res = orchestrator.load_and_judge(0, frame)
        latencies.append(res.processing_time_ms)

    total_time = time.perf_counter() - t0
    avg_latency = sum(latencies) / len(latencies)

    # Average latency must be well under 30ms (< 33.3ms = 30FPS)
    assert avg_latency < 30.0, f"Average latency too high: {avg_latency:.2f} ms"
    assert total_time < 1.5

    orchestrator.stop()


def test_60fps_continuous_stream_benchmark():
    """Verify that processing 60 consecutive frames completes well within real-time budget."""
    orchestrator = ContinuousInspectionOrchestrator()
    recipe = InspectionRecipe(product_key="60FPS_TEST")
    recipe.preprocess_snapshots[0] = PreprocessSnapshot(enabled=True, threshold=100)
    orchestrator.set_slot_recipe(0, recipe)

    frame = np.zeros((200, 200), dtype=np.uint8)
    frame[50:150, 50:150] = 200

    t_start = time.perf_counter()
    latencies = []
    for _ in range(60):
        res = orchestrator.load_and_judge(0, frame)
        latencies.append(res.processing_time_ms)

    total_duration = time.perf_counter() - t_start
    avg_latency = sum(latencies) / len(latencies)

    # For 60 FPS real-time streaming, average processing time per frame must be < 30ms
    assert avg_latency < 30.0, f"Average latency too high for 60FPS: {avg_latency:.2f} ms"
    # Total duration for 60 frames on simple image should be < 2 seconds
    assert total_duration < 2.0
    orchestrator.stop()


def test_multislot_concurrent_load():
    """Verify 3-Slot simultaneous inspection throughput and isolation."""
    orchestrator = ContinuousInspectionOrchestrator()
    for slot_idx in range(3):
        rec = InspectionRecipe(product_key=f"PROD_SLOT_{slot_idx}")
        rec.preprocess_snapshots[0] = PreprocessSnapshot(enabled=True, threshold=120)
        orchestrator.set_slot_recipe(slot_idx, rec)

    frame = np.zeros((150, 150), dtype=np.uint8)
    frame[30:80, 30:80] = 255

    for _ in range(10):
        for slot_idx in range(3):
            res = orchestrator.load_and_judge(slot_idx, frame)
            assert res is not None
            assert res.processing_time_ms < 30.0

    orchestrator.stop()


def test_build_exe_script_executable():
    """Verify scripts/build_exe.py is syntactically valid and importable."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("build_exe", "scripts/build_exe.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "build")
