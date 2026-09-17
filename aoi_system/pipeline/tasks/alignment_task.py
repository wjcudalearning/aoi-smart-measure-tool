from typing import Any

import cv2
import numpy as np

from aoi_system.algorithms.corner_detection.detector import ReferenceCornerDetector
from aoi_system.core.context import InspectionContext
from aoi_system.core.coordinates import compute_reference_basis
from aoi_system.core.models.geometry import BoundingRect, Point2I
from aoi_system.core.models.recipe import ReferenceCornerPointMode, ReferenceCornerSnapshot
from aoi_system.pipeline.tasks.base import TaskResult, VisionTask


class CornerAlignmentTask(VisionTask):
    """Vision task detecting reference corner and establishing workpiece ReferenceBasis."""

    def __init__(
        self,
        task_id: str = "corner_alignment",
        task_type: str = "CornerAlignmentTask",
        enabled: bool = True,
        input_image_key: str = "binary",
        roi: tuple[int, int, int, int] | None = None,
        corner_mode: str = "ContourNearest",
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, task_type=task_type, enabled=enabled)
        self.input_image_key = input_image_key
        self.roi = roi
        mode_map = {
            "ContourNearest": ReferenceCornerPointMode.CONTOUR_NEAREST,
            "RoiTopEdge": ReferenceCornerPointMode.ROI_TOP_EDGE,
            "ScanSearch": ReferenceCornerPointMode.SCAN_SEARCH,
        }
        self.corner_mode = mode_map.get(corner_mode, ReferenceCornerPointMode.CONTOUR_NEAREST)
        self._detector = ReferenceCornerDetector()

    def run(self, ctx: InspectionContext) -> TaskResult:
        img = ctx.get_image(self.input_image_key)
        if img is None:
            raise ValueError(f"Image '{self.input_image_key}' not found in InspectionContext.")

        h, w = img.shape[:2]
        roi_rect = (
            BoundingRect(x=self.roi[0], y=self.roi[1], width=self.roi[2], height=self.roi[3])
            if self.roi is not None
            else BoundingRect(x=0, y=0, width=w, height=h)
        )

        snapshot = ReferenceCornerSnapshot(
            enabled=True,
            roi=roi_rect,
            point_mode=self.corner_mode,
        )

        candidate = self._detector.find_candidate(img, snapshot)
        if candidate is None:
            # Fallback default basis at origin
            basis = compute_reference_basis(Point2I(x=0, y=0), Point2I(x=100, y=0))
            ctx.reference_basis = basis
            return TaskResult(
                task_id=self.task_id,
                task_type=self.task_type,
                success=False,
                message="No reference corner found.",
            )

        anchor = candidate.top_left
        top_right = candidate.top_right
        basis = compute_reference_basis(anchor, top_right)
        ctx.reference_basis = basis
        ctx.set_feature("reference_corner", candidate)
        ctx.set_feature("reference_basis", basis)

        return TaskResult(
            task_id=self.task_id,
            task_type=self.task_type,
            success=True,
            message="Reference corner aligned successfully",
            output_data={
                "corner_x": candidate.top_left.x,
                "corner_y": candidate.top_left.y,
            },
        )


class TemplateMatchTask(VisionTask):
    """Vision task finding features or parts via normalized cross-correlation template matching."""

    def __init__(
        self,
        task_id: str = "template_match",
        task_type: str = "TemplateMatchTask",
        enabled: bool = True,
        input_image_key: str = "raw",
        template: np.ndarray | None = None,
        min_score: float = 0.7,
        output_feature_name: str = "template_match",
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, task_type=task_type, enabled=enabled)
        self.input_image_key = input_image_key
        self.template = template
        self.min_score = min_score
        self.output_feature_name = output_feature_name

    def run(self, ctx: InspectionContext) -> TaskResult:
        img = ctx.get_image(self.input_image_key)
        if img is None:
            raise ValueError(f"Image '{self.input_image_key}' not found in InspectionContext.")
        if self.template is None:
            # Fallback if no template provided: search center dummy match
            h, w = img.shape[:2]
            match_data = {"x": float(w // 2), "y": float(h // 2), "score": 1.0}
            ctx.set_feature(self.output_feature_name, match_data)
            return TaskResult(task_id=self.task_id, task_type=self.task_type, success=True)

        res = cv2.matchTemplate(img, self.template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

        tpl_h, tpl_w = self.template.shape[:2]
        center_x = max_loc[0] + tpl_w / 2.0
        center_y = max_loc[1] + tpl_h / 2.0

        match_info = {
            "center_x": center_x,
            "center_y": center_y,
            "score": float(max_val),
            "match_loc": max_loc,
        }
        ctx.set_feature(self.output_feature_name, match_info)

        if max_val < self.min_score:
            msg = f"Template match score {max_val:.3f} below threshold {self.min_score:.3f}"
            ctx.add_anomaly(msg)
            return TaskResult(
                task_id=self.task_id,
                task_type=self.task_type,
                success=False,
                message=msg,
                output_data=match_info,
            )

        return TaskResult(
            task_id=self.task_id,
            task_type=self.task_type,
            success=True,
            message=f"Template matched with score {max_val:.3f}",
            output_data=match_info,
        )
