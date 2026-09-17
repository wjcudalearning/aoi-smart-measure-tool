from enum import StrEnum

from pydantic import BaseModel, Field

from aoi_system.core.models.geometry import Point2D, Point2I


class MeasureDirectionMode(StrEnum):
    NONE = "None"
    PARALLEL = "Parallel"
    PERPENDICULAR = "Perpendicular"


class MeasureRecord(BaseModel):
    """Stores definition and computed values of a measurement line."""

    start_point: Point2I = Field(default_factory=Point2I)
    end_point: Point2I = Field(default_factory=Point2I)
    center_point: Point2I = Field(default_factory=Point2I)
    local_start_point: Point2D = Field(default_factory=Point2D)
    local_end_point: Point2D = Field(default_factory=Point2D)
    distance: float = 0.0
    source_name: str = ""
    direction: MeasureDirectionMode = MeasureDirectionMode.NONE
    status_text: str = ""
