"""High-Throughput and Latency Profiling Script for AOI Continuous Inspection Pipeline."""

import time

import numpy as np

from aoi_system.algorithms.backend.manager import BackendManager
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


def build_benchmark_recipe() -> InspectionRecipe:
    recipe = InspectionRecipe(product_key="BENCHMARK_PROD")
    recipe.preprocess_snapshots[0] = PreprocessSnapshot(
        enabled=True,
        threshold=120,
        upper_threshold=255,
        erode_iterations=1,
        dilate_iterations=1,
    )
    recipe.reference_corner = ReferenceCornerSnapshot(
        enabled=True,
        point_mode=ReferenceCornerPointMode.CONTOUR_NEAREST,
        roi=BoundingRect(x=10, y=10, width=200, height=200),
    )
    for i in range(5):
        recipe.measure_records.append(
            MeasureRecord(
                start_point=Point2I(x=20 + i * 10, y=30),
                end_point=Point2I(x=120 + i * 10, y=30),
                source_name="Preprocess 1",
                direction=MeasureDirectionMode.PARALLEL,
            )
        )
        recipe.judgement_rules.append(
            JudgementCriterionRule(
                name=f"Spec_{i + 1}",
                calc_expression=f"({i + 1})",
                spec_expression="0.40~0.60",
            )
        )
    recipe.calibration = CameraCalibration(
        ccd_x_precision=0.005,
        ccd_y_precision=0.005,
        measurement_scale_factor=1.0,
    )
    return recipe


def run_profiling(num_frames: int = 150) -> None:
    backend = BackendManager()
    print("=========================================================")
    print("  AOI System High-Frequency Profiler & Latency Benchmark")
    print("=========================================================")
    print(f"Backend in Use: {backend.current_backend.value}")
    print(f"Test Workload: {num_frames} frames across 3 concurrent slots")

    orchestrator = ContinuousInspectionOrchestrator()
    recipe = build_benchmark_recipe()
    for s in range(3):
        orchestrator.set_slot_recipe(s, recipe)

    # Synthetic 640x480 frame with workpiece feature
    test_frame = np.zeros((480, 640), dtype=np.uint8)
    test_frame[50:350, 80:500] = 255

    latencies: list[float] = []

    t_start = time.perf_counter()
    for i in range(num_frames):
        slot = i % 3
        res = orchestrator.load_and_judge(slot, test_frame, source_name="ProfileStream")
        latencies.append(res.processing_time_ms)

    total_time = time.perf_counter() - t_start
    fps = num_frames / total_time
    avg_lat = sum(latencies) / len(latencies)
    min_lat = min(latencies)
    max_lat = max(latencies)

    print("\n--- Profiling Results ---")
    print(f"Total Elapsed Time : {total_time:.3f} seconds")
    print(f"Overall Throughput : {fps:.2f} FPS")
    print(f"Average Latency    : {avg_lat:.2f} ms")
    print(f"Min / Max Latency  : {min_lat:.2f} ms / {max_lat:.2f} ms")

    for s in range(3):
        stats = orchestrator.get_slot_yield(s)
        print(f"Slot {s} Yield Stats: {stats}")

    orchestrator.stop()
    print("=========================================================")


if __name__ == "__main__":
    run_profiling()
