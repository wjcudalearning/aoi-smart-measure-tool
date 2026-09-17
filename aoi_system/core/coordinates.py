import math

from aoi_system.core.models.geometry import Point2D, Point2I, ReferenceBasis


def compute_reference_basis(anchor: Point2I, top_right: Point2I) -> ReferenceBasis:
    """Computes reference basis vectors given anchor point and top-right reference point."""
    dx = float(top_right.x - anchor.x)
    dy = float(top_right.y - anchor.y)
    length = math.sqrt(dx * dx + dy * dy)

    if length <= 1e-6:
        return ReferenceBasis(
            anchor=anchor,
            unit_x=Point2D(x=1.0, y=0.0),
            unit_y=Point2D(x=0.0, y=1.0),
            length=0.0,
        )

    ux = dx / length
    uy = dy / length
    # UnitY is perpendicular to UnitX (clockwise 90 degrees in image space: (-uy, ux))
    return ReferenceBasis(
        anchor=anchor,
        unit_x=Point2D(x=ux, y=uy),
        unit_y=Point2D(x=-uy, y=ux),
        length=length,
    )


def image_to_local(point: Point2D | Point2I, basis: ReferenceBasis) -> Point2D:
    """Transforms an image coordinate into the workpiece local coordinate space."""
    dx = float(point.x - basis.anchor.x)
    dy = float(point.y - basis.anchor.y)

    local_x = dx * basis.unit_x.x + dy * basis.unit_x.y
    local_y = dx * basis.unit_y.x + dy * basis.unit_y.y
    return Point2D(x=local_x, y=local_y)


def local_to_image(local_pt: Point2D, basis: ReferenceBasis) -> Point2D:
    """Transforms a workpiece local coordinate back into absolute image coordinate space."""
    img_x = float(basis.anchor.x) + local_pt.x * basis.unit_x.x + local_pt.y * basis.unit_y.x
    img_y = float(basis.anchor.y) + local_pt.x * basis.unit_x.y + local_pt.y * basis.unit_y.y
    return Point2D(x=img_x, y=img_y)
