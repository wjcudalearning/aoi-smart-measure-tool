from enum import IntEnum
from typing import Any

from pydantic import BaseModel, Field

from aoi_system.core.models.geometry import BoundingRect
from aoi_system.core.models.measurement import MeasureRecord


class ReferenceCornerPointMode(IntEnum):
    CONTOUR_NEAREST = 0
    ROI_TOP_EDGE = 1
    SCAN_SEARCH = 2


class PreprocessSnapshot(BaseModel):
    enabled: bool = False
    threshold: int = 128
    upper_threshold: int = 255
    use_dual_threshold: bool = False
    erode_iterations: int = 0
    dilate_iterations: int = 0
    open_iterations: int = 0
    close_iterations: int = 0


class DualThresholdSnapshot(BaseModel):
    enabled: bool = False
    lower_threshold: int = 50
    upper_threshold: int = 200
    erode_iterations: int = 0
    dilate_iterations: int = 0
    open_iterations: int = 0
    close_iterations: int = 0


class ReferenceCornerSnapshot(BaseModel):
    enabled: bool = False
    source_index: int = 0
    point_mode: ReferenceCornerPointMode = ReferenceCornerPointMode.CONTOUR_NEAREST
    scan_line_threshold: int = 128
    roi: BoundingRect = Field(default_factory=BoundingRect)
    roi_saved: bool = False
    corner_found: bool = False


class JudgementCriterionRule(BaseModel):
    name: str = ""
    calc_expression: str = ""
    spec_expression: str = ""
    calc_expression_b: str = ""
    spec_expression_b: str = ""


class CameraCalibration(BaseModel):
    camera_name: str = "DefaultCamera"
    usage_name: str = "Inspection"
    ccd_x_precision: float = 0.005  # mm per pixel
    ccd_y_precision: float = 0.005  # mm per pixel
    measurement_scale_factor: float = 1.0


class VisionTaskConfig(BaseModel):
    task_id: str
    task_type: str
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)


class InspectionRecipe(BaseModel):
    """Complete product inspection recipe entity supporting dynamic vision task pipeline."""

    product_key: str = "DEFAULT"
    tasks: list[VisionTaskConfig] = Field(default_factory=list)

    # Legacy fields for backward compatibility with existing configs & INI
    preprocess_snapshots: list[PreprocessSnapshot] = Field(
        default_factory=lambda: [PreprocessSnapshot() for _ in range(4)]
    )
    dual_threshold: DualThresholdSnapshot = Field(default_factory=DualThresholdSnapshot)
    reference_corner: ReferenceCornerSnapshot = Field(default_factory=ReferenceCornerSnapshot)
    measure_records: list[MeasureRecord] = Field(default_factory=list)
    judgement_rules: list[JudgementCriterionRule] = Field(default_factory=list)
    calibration: CameraCalibration = Field(default_factory=CameraCalibration)
