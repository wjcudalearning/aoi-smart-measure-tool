from typing import Any

import cv2
import numpy as np

from aoi_system.algorithms.measurement.calculator import MeasurementCalculator
from aoi_system.core.context import InspectionContext
from aoi_system.core.models.geometry import Point2D, Point2I
from aoi_system.core.models.measurement import MeasureDirectionMode
from aoi_system.core.models.recipe import CameraCalibration
from aoi_system.pipeline.tasks.base import TaskResult, VisionTask


class LineMeasureTask(VisionTask):
    """Vision task measuring projected parallel/perpendicular distance between features."""

    def __init__(
        self,
        task_id: str = "line_measure",
        task_type: str = "LineMeasureTask",
        enabled: bool = True,
        param_name: str = "distance",
        point1: Point2D | None = None,
        point2: Point2D | None = None,
        mode: str = "Parallel",
        pixel_size_mm: float = 0.01,
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, task_type=task_type, enabled=enabled)
        self.param_name = param_name
        self.point1 = point1 or Point2D(x=0.0, y=0.0)
        self.point2 = point2 or Point2D(x=100.0, y=0.0)
        self.mode = (
            MeasureDirectionMode.PERPENDICULAR
            if mode.lower().startswith("perp")
            else MeasureDirectionMode.PARALLEL
        )
        self.pixel_size_mm = pixel_size_mm
        self._calc = MeasurementCalculator()

    def run(self, ctx: InspectionContext) -> TaskResult:
        basis = ctx.reference_basis

        p1 = Point2I(x=int(self.point1.x), y=int(self.point1.y))
        p2 = Point2I(x=int(self.point2.x), y=int(self.point2.y))
        calibration = CameraCalibration(
            ccd_x_precision=self.pixel_size_mm,
            ccd_y_precision=self.pixel_size_mm,
        )

        dist_mm = self._calc.compute_projected_distance(
            p1=p1,
            p2=p2,
            direction=self.mode,
            basis=basis,
            calibration=calibration,
        )

        ctx.set_measurement(self.param_name, dist_mm)

        return TaskResult(
            task_id=self.task_id,
            task_type=self.task_type,
            success=True,
            message=f"Measured {self.param_name}: {dist_mm:.4f} mm",
            output_data={
                "distance_mm": dist_mm,
            },
        )


class CircleFitTask(VisionTask):
    """Vision task fitting circle to circular holes or pins using least squares contour fitting."""

    def __init__(
        self,
        task_id: str = "circle_fit",
        task_type: str = "CircleFitTask",
        enabled: bool = True,
        input_image_key: str = "raw",
        roi: tuple[int, int, int, int] | None = None,
        pixel_size_mm: float = 0.01,
        diameter_param_name: str = "hole_diameter",
        **kwargs: Any,
    ) -> None:
        super().__init__(task_id=task_id, task_type=task_type, enabled=enabled)
        self.input_image_key = input_image_key
        self.roi = roi
        self.pixel_size_mm = pixel_size_mm
        self.diameter_param_name = diameter_param_name

    def run(self, ctx: InspectionContext) -> TaskResult:
        img = ctx.get_image(self.input_image_key)
        if img is None:
            raise ValueError(f"Image '{self.input_image_key}' not found in InspectionContext.")

        x, y, w, h = self.roi if self.roi else (0, 0, img.shape[1], img.shape[0])
        roi_img = img[y : y + h, x : x + w]

        # Extract edges
        edges = cv2.Canny(roi_img, 50, 150)
        pts = cv2.findNonZero(edges)

        if pts is None or len(pts) < 5:
            # Fallback to contour
            _, binary = cv2.threshold(roi_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            contours, _ = cv2.findContours(binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
            if contours:
                pts = max(contours, key=cv2.contourArea)

        if pts is None or len(pts) < 5:
            ctx.add_anomaly(f"Task [{self.task_id}]: Insufficient edge points to fit circle.")
            return TaskResult(task_id=self.task_id, task_type=self.task_type, success=False)

        pts_array = pts.reshape(-1, 2)
        # Shift back to full image coordinates
        pts_full = pts_array + np.array([x, y])

        (cx, cy), radius = cv2.minEnclosingCircle(pts_full.astype(np.float32))
        diameter_mm = float(radius * 2.0 * self.pixel_size_mm)

        ctx.set_measurement(self.diameter_param_name, diameter_mm)
        ctx.set_feature(
            self.task_id,
            {
                "center_x": float(cx),
                "center_y": float(cy),
                "radius_px": float(radius),
                "diameter_mm": diameter_mm,
            },
        )

        return TaskResult(
            task_id=self.task_id,
            task_type=self.task_type,
            success=True,
            message=f"Circle fitted: center=({cx:.1f}, {cy:.1f}), diameter={diameter_mm:.4f} mm",
            output_data={"diameter_mm": diameter_mm, "center_x": float(cx), "center_y": float(cy)},
        )
