import math

import numpy as np
from pydantic import BaseModel, Field

from aoi_system.core.models.geometry import Point2I, ReferenceBasis
from aoi_system.core.models.measurement import MeasureDirectionMode
from aoi_system.core.models.recipe import CameraCalibration


class LineMeasurementResult(BaseModel):
    is_valid: bool = False
    first_point: Point2I = Field(default_factory=Point2I)
    last_point: Point2I = Field(default_factory=Point2I)
    pixel_distance: float = 0.0
    millimeter_distance: float = 0.0
    status_text: str = ""


class MeasurementCalculator:
    """Calculates sub-pixel and line segment dimensions with calibration projection."""

    def sample_line_points(self, p1: Point2I, p2: Point2I) -> list[Point2I]:
        """Samples integer pixel points along line connecting p1 and p2 (Bresenham line)."""
        x0, y0 = p1.x, p1.y
        x1, y1 = p2.x, p2.y
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        points: list[Point2I] = []
        curr_x, curr_y = x0, y0

        while True:
            points.append(Point2I(x=curr_x, y=curr_y))
            if curr_x == x1 and curr_y == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                curr_x += sx
            if e2 < dx:
                err += dx
                curr_y += sy

        return points

    def analyze_line_measurement(
        self,
        binary_mat: np.ndarray,
        start_point: Point2I,
        end_point: Point2I,
        calibration: CameraCalibration,
        white_threshold: int = 127,
    ) -> LineMeasurementResult:
        """Finds edge feature run along a line segment and converts to physical dimensions."""
        if binary_mat is None or binary_mat.size == 0:
            return LineMeasurementResult(is_valid=False, status_text="影像為空")

        sample_pts = self.sample_line_points(start_point, end_point)
        if len(sample_pts) < 2:
            return LineMeasurementResult(is_valid=False, status_text="採樣點不足")

        h, w = binary_mat.shape[:2]
        best_run_start = -1
        best_run_len = 0
        curr_run_start = -1

        for i, pt in enumerate(sample_pts):
            if pt.x < 0 or pt.y < 0 or pt.x >= w or pt.y >= h:
                if curr_run_start >= 0:
                    run_len = i - curr_run_start
                    if run_len > best_run_len:
                        best_run_start = curr_run_start
                        best_run_len = run_len
                    curr_run_start = -1
                continue

            val = int(binary_mat[pt.y, pt.x])
            if val > white_threshold:
                if curr_run_start < 0:
                    curr_run_start = i
            elif curr_run_start >= 0:
                run_len = i - curr_run_start
                if run_len > best_run_len:
                    best_run_start = curr_run_start
                    best_run_len = run_len
                curr_run_start = -1

        if curr_run_start >= 0:
            run_len = len(sample_pts) - curr_run_start
            if run_len > best_run_len:
                best_run_start = curr_run_start
                best_run_len = run_len

        if best_run_start < 0 or best_run_len < 2:
            return LineMeasurementResult(is_valid=False, status_text="找不到特徵邊界")

        first_pt = sample_pts[best_run_start]
        last_white_pt = sample_pts[best_run_start + best_run_len - 1]
        next_idx = best_run_start + best_run_len
        last_pt = sample_pts[next_idx] if next_idx < len(sample_pts) else last_white_pt

        dx = last_pt.x - first_pt.x
        dy = last_pt.y - first_pt.y
        pix_dist = math.sqrt(dx * dx + dy * dy)

        # Scale by CCD precision and factor
        scale = (
            calibration.measurement_scale_factor
            if calibration.measurement_scale_factor > 0
            else 1.0
        )
        mm_dist = (
            math.sqrt(
                (dx * calibration.ccd_x_precision) ** 2 + (dy * calibration.ccd_y_precision) ** 2
            )
            * scale
        )

        return LineMeasurementResult(
            is_valid=True,
            first_point=first_pt,
            last_point=last_pt,
            pixel_distance=pix_dist,
            millimeter_distance=mm_dist,
            status_text="OK",
        )

    def compute_projected_distance(
        self,
        p1: Point2I,
        p2: Point2I,
        direction: MeasureDirectionMode,
        basis: ReferenceBasis | None,
        calibration: CameraCalibration,
    ) -> float:
        """Projects delta vector between p1 and p2 along parallel/perpendicular baseline."""
        dx = float(p2.x - p1.x)
        dy = float(p2.y - p1.y)

        if basis is not None and direction == MeasureDirectionMode.PARALLEL:
            proj_pixels = abs(dx * basis.unit_x.x + dy * basis.unit_x.y)
        elif basis is not None and direction == MeasureDirectionMode.PERPENDICULAR:
            proj_pixels = abs(dx * basis.unit_y.x + dy * basis.unit_y.y)
        else:
            proj_pixels = math.sqrt(dx * dx + dy * dy)

        scale = (
            calibration.measurement_scale_factor
            if calibration.measurement_scale_factor > 0
            else 1.0
        )
        # For projected distance along axis, convert using appropriate precision
        # Average CCD precision or directional precision
        return proj_pixels * calibration.ccd_x_precision * scale
