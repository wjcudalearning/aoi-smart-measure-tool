import math
import pytest
from aoi_system.core.models.geometry import Point2D, Point2I, ReferenceBasis
from aoi_system.core.coordinates import image_to_local, local_to_image, compute_reference_basis

def test_compute_reference_basis_horizontal():
    # Anchor at (100, 100), TopRight at (200, 100) -> 0 degree angle
    anchor = Point2I(x=100, y=100)
    top_right = Point2I(x=200, y=100)
    basis = compute_reference_basis(anchor, top_right)
    
    assert basis.anchor == anchor
    assert math.isclose(basis.length, 100.0, abs_tol=1e-5)
    assert math.isclose(basis.unit_x.x, 1.0, abs_tol=1e-5)
    assert math.isclose(basis.unit_x.y, 0.0, abs_tol=1e-5)
    # UnitY is perpendicular to UnitX (clockwise/downward for image coords: (0, 1))
    assert math.isclose(basis.unit_y.x, 0.0, abs_tol=1e-5)
    assert math.isclose(basis.unit_y.y, 1.0, abs_tol=1e-5)

def test_coordinate_roundtrip():
    anchor = Point2I(x=50, y=80)
    top_right = Point2I(x=150, y=180) # 45 degree vector
    basis = compute_reference_basis(anchor, top_right)
    
    original_pt = Point2D(x=120.5, y=210.3)
    local_pt = image_to_local(original_pt, basis)
    restored_pt = local_to_image(local_pt, basis)
    
    assert math.isclose(restored_pt.x, original_pt.x, abs_tol=1e-4)
    assert math.isclose(restored_pt.y, original_pt.y, abs_tol=1e-4)

def test_image_to_local_origin():
    anchor = Point2I(x=200, y=300)
    top_right = Point2I(x=300, y=300)
    basis = compute_reference_basis(anchor, top_right)
    
    local_pt = image_to_local(Point2D(x=200, y=300), basis)
    assert math.isclose(local_pt.x, 0.0, abs_tol=1e-6)
    assert math.isclose(local_pt.y, 0.0, abs_tol=1e-6)
