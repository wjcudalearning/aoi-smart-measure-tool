import cv2
import numpy as np

from aoi_system.algorithms.corner_detection.detector import ReferenceCornerDetector
from aoi_system.core.models.geometry import BoundingRect
from aoi_system.core.models.recipe import ReferenceCornerPointMode, ReferenceCornerSnapshot


def test_detect_corner_contour_nearest():
    # 200x200 black image with a white rectangle at (50, 50, 60, 40)
    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (110, 90), 255, -1)

    snapshot = ReferenceCornerSnapshot(
        enabled=True,
        point_mode=ReferenceCornerPointMode.CONTOUR_NEAREST,
        roi=BoundingRect(x=30, y=30, width=120, height=100),
    )

    detector = ReferenceCornerDetector()
    candidate = detector.find_candidate(img, snapshot)

    assert candidate is not None
    assert candidate.top_left.x == 50
    assert candidate.top_left.y == 50
    assert candidate.top_right.x == 110
    assert candidate.top_right.y == 50
    assert candidate.center_point.x == 80
    assert candidate.center_point.y == 70


def test_detect_corner_roi_top_edge():
    img = np.zeros((200, 200), dtype=np.uint8)
    cv2.rectangle(img, (60, 40), (140, 100), 255, -1)

    snapshot = ReferenceCornerSnapshot(
        enabled=True,
        point_mode=ReferenceCornerPointMode.ROI_TOP_EDGE,
        roi=BoundingRect(x=20, y=20, width=160, height=120),
    )

    detector = ReferenceCornerDetector()
    candidate = detector.find_candidate(img, snapshot)

    assert candidate is not None
    assert candidate.top_left.x == 60
    assert candidate.top_left.y == 40
    assert candidate.top_right.x == 140
    assert candidate.top_right.y == 40


def test_detect_corner_scan_search():
    img = np.zeros((200, 200), dtype=np.uint8)
    # A line of white pixels from x=40 to x=100 at y=75
    img[75, 40:101] = 255

    snapshot = ReferenceCornerSnapshot(
        enabled=True,
        point_mode=ReferenceCornerPointMode.SCAN_SEARCH,
        scan_line_threshold=20,
        roi=BoundingRect(x=20, y=50, width=120, height=50),
    )

    detector = ReferenceCornerDetector()
    candidate = detector.find_candidate(img, snapshot)

    assert candidate is not None
    assert candidate.top_left.x == 40
    assert candidate.top_left.y == 75
    assert candidate.top_right.x == 100
    assert candidate.top_right.y == 75
