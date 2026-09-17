import threading
import time
from collections.abc import Callable

import cv2
import numpy as np

from aoi_system.algorithms.corner_detection.detector import ReferenceCornerDetector
from aoi_system.algorithms.judgement.evaluator import JudgementEvaluator
from aoi_system.algorithms.measurement.calculator import MeasurementCalculator
from aoi_system.algorithms.preprocess.filters import PreprocessPipeline
from aoi_system.core.coordinates import compute_reference_basis
from aoi_system.core.models.measurement import MeasureDirectionMode
from aoi_system.core.models.recipe import InspectionRecipe
from aoi_system.core.models.results import (
    ContinuousInspectionResult,
)
from aoi_system.pipeline.context import InspectionContext
from aoi_system.pipeline.slot_worker import InspectionSlotWorker


class ContinuousInspectionOrchestrator:
    """Manages 3-slot concurrent continuous inspection pipeline and yield statistics."""

    NUM_SLOTS: int = 3

    def __init__(self, preprocess_pipeline: PreprocessPipeline | None = None) -> None:
        self.preprocess = preprocess_pipeline or PreprocessPipeline()
        self.corner_detector = ReferenceCornerDetector()
        self.measurer = MeasurementCalculator()
        self.judgement = JudgementEvaluator()

        self._recipes: dict[int, InspectionRecipe] = {}
        self._yield_stats: dict[int, dict[str, int]] = {
            i: {"total": 0, "A": 0, "B": 0, "NG": 0, "unjudgeable": 0}
            for i in range(self.NUM_SLOTS)
        }
        self._stats_lock = threading.Lock()

        # Initialize slot workers
        self._workers: dict[int, InspectionSlotWorker] = {}
        for i in range(self.NUM_SLOTS):
            worker = InspectionSlotWorker(
                slot_index=i,
                process_fn=self._process_context,
            )
            self._workers[i] = worker
            worker.start()

    def set_slot_recipe(self, slot_index: int, recipe: InspectionRecipe) -> None:
        if 0 <= slot_index < self.NUM_SLOTS:
            self._recipes[slot_index] = recipe

    def get_slot_recipe(self, slot_index: int) -> InspectionRecipe | None:
        return self._recipes.get(slot_index)

    def get_slot_yield(self, slot_index: int) -> dict[str, int]:
        with self._stats_lock:
            return dict(self._yield_stats.get(slot_index, {}))

    def reset_slot_yield(self, slot_index: int) -> None:
        with self._stats_lock:
            if slot_index in self._yield_stats:
                self._yield_stats[slot_index] = {
                    "total": 0,
                    "A": 0,
                    "B": 0,
                    "NG": 0,
                    "unjudgeable": 0,
                }

    def register_slot_callback(
        self, slot_index: int, callback: Callable[[ContinuousInspectionResult], None]
    ) -> None:
        if slot_index in self._workers:
            self._workers[slot_index].register_callback(callback)

    def submit_async(self, slot_index: int, image: np.ndarray, source_name: str = "") -> bool:
        """Submits frame to worker queue for non-blocking execution."""
        if slot_index not in self._workers:
            return False
        ctx = InspectionContext(
            slot_index=slot_index,
            image=image,
            recipe=self._recipes.get(slot_index),
            source_name=source_name,
        )
        return self._workers[slot_index].submit(ctx)

    def load_and_judge(
        self, slot_index: int, image: np.ndarray, source_name: str = ""
    ) -> ContinuousInspectionResult:
        """Direct synchronous inspection execution."""
        ctx = InspectionContext(
            slot_index=slot_index,
            image=image,
            recipe=self._recipes.get(slot_index),
            source_name=source_name,
        )
        return self._process_context(ctx)

    def _process_context(self, ctx: InspectionContext) -> ContinuousInspectionResult:
        t0 = time.perf_counter()
        recipe = ctx.recipe or self._recipes.get(ctx.slot_index)
        if recipe is None:
            return ContinuousInspectionResult(
                slot_index=ctx.slot_index,
                summary="未設定條件",
                rules=[],
                processing_time_ms=0.0,
            )

        # Grayscale conversion
        raw_img = ctx.image
        if raw_img.ndim == 3 and raw_img.shape[2] == 3:
            gray = cv2.cvtColor(raw_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = raw_img

        # 1. Preprocess Images
        preprocessed_images: dict[str, np.ndarray] = {"Raw": gray}
        for i, snap in enumerate(recipe.preprocess_snapshots):
            key = f"Preprocess {i + 1}"
            if snap.enabled:
                preprocessed_images[key] = self.preprocess.apply_preprocess(gray, snap)

        if recipe.dual_threshold.enabled:
            preprocessed_images["DualThreshold"] = self.preprocess.apply_dual_threshold(
                gray, recipe.dual_threshold
            )

        # 2. Reference Corner & Coordinate Basis
        basis = None
        if recipe.reference_corner.enabled:
            corner_src_key = f"Preprocess {recipe.reference_corner.source_index + 1}"
            corner_img = preprocessed_images.get(corner_src_key)
            if corner_img is None:
                # Fallback to any preprocessed image or gray
                corner_img = (
                    preprocessed_images.get("Preprocess 1")
                    or preprocessed_images.get("DualThreshold")
                    or gray
                )

            candidate = self.corner_detector.find_candidate(corner_img, recipe.reference_corner)
            if candidate is not None:
                basis = compute_reference_basis(candidate.top_left, candidate.top_right)

        # 3. Measurement Records
        line_values: dict[int, float] = {}
        for idx, rec in enumerate(recipe.measure_records, start=1):
            src_img = preprocessed_images.get(rec.source_name)
            if src_img is None:
                src_img = (
                    preprocessed_images.get("Preprocess 1")
                    or preprocessed_images.get("DualThreshold")
                    or gray
                )

            # Determine start and end points in absolute coordinates
            start_pt = rec.start_point
            end_pt = rec.end_point

            if rec.direction in (MeasureDirectionMode.PARALLEL, MeasureDirectionMode.PERPENDICULAR):
                dist = self.measurer.compute_projected_distance(
                    start_pt,
                    end_pt,
                    rec.direction,
                    basis,
                    recipe.calibration,
                )
            else:
                line_res = self.measurer.analyze_line_measurement(
                    src_img,
                    start_pt,
                    end_pt,
                    recipe.calibration,
                )
                dist = line_res.millimeter_distance

            line_values[idx] = dist

        # 4. Tolerance Judgement
        summary_grade, rule_results = self.judgement.evaluate_rules(
            recipe.judgement_rules, line_values
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        result = ContinuousInspectionResult(
            slot_index=ctx.slot_index,
            summary=summary_grade.value,
            sub_parameter_name=recipe.product_key,
            rules=rule_results,
            processing_time_ms=elapsed_ms,
        )

        # 5. Update yield stats
        with self._stats_lock:
            stats = self._yield_stats.setdefault(
                ctx.slot_index,
                {"total": 0, "A": 0, "B": 0, "NG": 0, "unjudgeable": 0},
            )
            stats["total"] += 1
            if result.summary == "A":
                stats["A"] += 1
            elif result.summary == "B":
                stats["B"] += 1
            elif result.summary == "NG":
                stats["NG"] += 1
            else:
                stats["unjudgeable"] += 1

        return result

    def stop(self) -> None:
        """Stops all slot worker threads."""
        for worker in self._workers.values():
            worker.stop()
