import math

import numpy as np

from aoi_system.algorithms.measurement.calculator import MeasurementCalculator
from aoi_system.core.models.geometry import Point2D, Point2I, ReferenceBasis
from aoi_system.core.models.measurement import MeasureDirectionMode
from aoi_system.core.models.recipe import CameraCalibration


def test_sample_line_points():
    calc = MeasurementCalculator()
    p1 = Point2I(x=0, y=0)
    p2 = Point2I(x=4, y=0)
    pts = calc.sample_line_points(p1, p2)
    assert len(pts) == 5
    assert pts[0] == Point2I(x=0, y=0)
    assert pts[-1] == Point2I(x=4, y=0)


def test_analyze_line_measurement_on_binary():
    calc = MeasurementCalculator()
    # 50x50 image with a white strip from x=10 to x=30 at y=20
    img = np.zeros((50, 50), dtype=np.uint8)
    img[20, 10:31] = 255  # 21 pixels wide

    start_pt = Point2I(x=5, y=20)
    end_pt = Point2I(x=35, y=20)
    calib = CameraCalibration(
        ccd_x_precision=0.005, ccd_y_precision=0.005, measurement_scale_factor=1.0
    )

    res = calc.analyze_line_measurement(img, start_pt, end_pt, calib)
    assert res.is_valid is True
    assert res.first_point.x == 10
    assert res.first_point.y == 20
    # Length of white run
    assert res.pixel_distance > 18
    # 20 pixels * 0.005 mm/px = 0.1 mm
    assert math.isclose(res.millimeter_distance, res.pixel_distance * 0.005, abs_tol=1e-4)


def test_projected_distance_parallel_and_perpendicular():
    calc = MeasurementCalculator()
    # Baseline oriented horizontally
    basis = ReferenceBasis(
        anchor=Point2I(x=0, y=0),
        unit_x=Point2D(x=1.0, y=0.0),
        unit_y=Point2D(x=0.0, y=1.0),
        length=100.0,
    )
    # A diagonal segment: delta_x = 30, delta_y = 40
    p1 = Point2I(x=10, y=10)
    p2 = Point2I(x=40, y=50)
    calib = CameraCalibration(
        ccd_x_precision=0.002, ccd_y_precision=0.002, measurement_scale_factor=1.0
    )

    # Parallel projection should only measure along X (30 px) -> 30 * 0.002 = 0.06 mm
    dist_parallel = calc.compute_projected_distance(
        p1, p2, MeasureDirectionMode.PARALLEL, basis, calib
    )
    assert math.isclose(dist_parallel, 30 * 0.002, abs_tol=1e-5)

    # Perpendicular projection should only measure along Y (40 px) -> 40 * 0.002 = 0.08 mm
    dist_perp = calc.compute_projected_distance(
        p1, p2, MeasureDirectionMode.PERPENDICULAR, basis, calib
    )
    assert math.isclose(dist_perp, 40 * 0.002, abs_tol=1e-5)
