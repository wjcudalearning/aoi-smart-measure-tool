from pydantic import BaseModel


class Point2D(BaseModel):
    """Sub-pixel or floating point 2D coordinate."""

    x: float = 0.0
    y: float = 0.0


class Point2I(BaseModel):
    """Integer pixel 2D coordinate."""

    x: int = 0
    y: int = 0


class BoundingRect(BaseModel):
    """Axis-aligned bounding rectangle."""

    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0


class RotatedRect(BaseModel):
    """Rotated bounding box with center, size, and angle."""

    center: Point2D
    width: float
    height: float
    angle_degrees: float


class ReferenceBasis(BaseModel):
    """Workpiece local coordinate system basis derived from reference corner."""

    anchor: Point2I
    unit_x: Point2D
    unit_y: Point2D
    length: float
