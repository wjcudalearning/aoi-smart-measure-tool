import cv2
import numpy as np

from aoi_system.core.models.geometry import (
    BoundingRect,
    Point2D,
    Point2I,
    ReferenceCornerCandidate,
    RotatedRect,
)
from aoi_system.core.models.recipe import ReferenceCornerPointMode, ReferenceCornerSnapshot


class ReferenceCornerDetector:
    """Detects workpiece reference corner to establish alignment coordinate system."""

    def find_candidate(
        self, binary_mat: np.ndarray, snapshot: ReferenceCornerSnapshot
    ) -> ReferenceCornerCandidate | None:
        if binary_mat is None or binary_mat.size == 0 or not snapshot.enabled:
            return None

        # Ensure 2D binary
        if binary_mat.ndim == 3 and binary_mat.shape[2] == 3:
            binary_mat = cv2.cvtColor(binary_mat, cv2.COLOR_BGR2GRAY)

        roi = snapshot.roi
        h, w = binary_mat.shape[:2]
        rx = max(0, roi.x)
        ry = max(0, roi.y)
        rw = min(w - rx, roi.width)
        rh = min(h - ry, roi.height)

        if rw <= 0 or rh <= 0:
            return None

        if snapshot.point_mode == ReferenceCornerPointMode.SCAN_SEARCH:
            return self._find_scan_search_candidate(
                binary_mat,
                rx,
                ry,
                rw,
                rh,
                snapshot.scan_line_threshold,
            )

        return self._find_contour_candidate(binary_mat, rx, ry, rw, rh, snapshot)

    def _find_scan_search_candidate(
        self, binary_mat: np.ndarray, rx: int, ry: int, rw: int, rh: int, threshold: int
    ) -> ReferenceCornerCandidate | None:
        thresh = max(1, threshold)
        for y in range(ry, ry + rh):
            row = binary_mat[y, rx : rx + rw]
            white_indices = np.where(row > 0)[0]
            if len(white_indices) == 0:
                continue

            # Find contiguous segments
            diffs = np.diff(white_indices)
            split_indices = np.where(diffs > 1)[0]
            starts = np.insert(white_indices[split_indices + 1], 0, white_indices[0])
            ends = np.append(white_indices[split_indices], white_indices[-1])

            for start, end in zip(starts, ends):
                length = end - start + 1
                if length >= thresh:
                    start_x = rx + int(start)
                    end_x = rx + int(end)
                    center_x = (start_x + end_x) // 2
                    return ReferenceCornerCandidate(
                        rotated_rect=RotatedRect(
                            center=Point2D(x=float(center_x), y=float(y)),
                            width=float(length),
                            height=1.0,
                            angle_degrees=0.0,
                        ),
                        top_left=Point2I(x=start_x, y=y),
                        top_right=Point2I(x=end_x, y=y),
                        center_point=Point2I(x=center_x, y=y),
                        bounding_rect=BoundingRect(x=start_x, y=y, width=int(length), height=1),
                    )
        return None

    def _find_contour_candidate(
        self,
        binary_mat: np.ndarray,
        rx: int,
        ry: int,
        rw: int,
        rh: int,
        snapshot: ReferenceCornerSnapshot,
    ) -> ReferenceCornerCandidate | None:
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            binary_mat, connectivity=8
        )
        best_candidate: ReferenceCornerCandidate | None = None
        best_area = -1

        for i in range(1, num_labels):
            x = int(stats[i, cv2.CC_STAT_LEFT])
            y = int(stats[i, cv2.CC_STAT_TOP])
            width = int(stats[i, cv2.CC_STAT_WIDTH])
            height = int(stats[i, cv2.CC_STAT_HEIGHT])
            area = int(stats[i, cv2.CC_STAT_AREA])

            # Check if fully inside ROI
            if not (x >= rx and y >= ry and (x + width) <= (rx + rw) and (y + height) <= (ry + rh)):
                continue

            if area <= best_area:
                continue

            candidate = self._create_candidate_from_label(
                labels, i, BoundingRect(x=x, y=y, width=width, height=height), snapshot
            )
            if candidate is not None:
                best_candidate = candidate
                best_area = area

        return best_candidate

    def _create_candidate_from_label(
        self,
        labels: np.ndarray,
        label_idx: int,
        bounding_rect: BoundingRect,
        snapshot: ReferenceCornerSnapshot,
    ) -> ReferenceCornerCandidate | None:
        mask = (labels == label_idx).astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        best_contour = max(contours, key=cv2.contourArea)
        rect = cv2.minAreaRect(best_contour)
        (center_x, center_y), (rect_w, rect_h), angle = rect

        if snapshot.point_mode == ReferenceCornerPointMode.ROI_TOP_EDGE:
            tl = Point2I(x=bounding_rect.x, y=bounding_rect.y)
            tr = Point2I(x=bounding_rect.x + bounding_rect.width - 1, y=bounding_rect.y)
        else:
            tl, tr = self._get_nearest_contour_points(
                best_contour,
                Point2I(x=bounding_rect.x, y=bounding_rect.y),
                Point2I(x=bounding_rect.x + bounding_rect.width - 1, y=bounding_rect.y),
            )

        return ReferenceCornerCandidate(
            rotated_rect=RotatedRect(
                center=Point2D(x=float(center_x), y=float(center_y)),
                width=float(rect_w),
                height=float(rect_h),
                angle_degrees=float(angle),
            ),
            top_left=tl,
            top_right=tr,
            center_point=Point2I(x=int(round(center_x)), y=int(round(center_y))),
            bounding_rect=bounding_rect,
        )

    def _get_nearest_contour_points(
        self, contour: np.ndarray, ideal_tl: Point2I, ideal_tr: Point2I
    ) -> tuple[Point2I, Point2I]:
        pts = contour.reshape(-1, 2).astype(np.float64)
        # Distance to ideal top-left
        d_tl = (pts[:, 0] - ideal_tl.x) ** 2 + (pts[:, 1] - ideal_tl.y) ** 2
        best_tl_idx = int(np.argmin(d_tl))
        tl = Point2I(x=int(pts[best_tl_idx, 0]), y=int(pts[best_tl_idx, 1]))

        # Distance to ideal top-right excluding tl point
        d_tr = (pts[:, 0] - ideal_tr.x) ** 2 + (pts[:, 1] - ideal_tr.y) ** 2
        d_tr[best_tl_idx] = np.inf
        best_tr_idx = int(np.argmin(d_tr))
        tr = Point2I(x=int(pts[best_tr_idx, 0]), y=int(pts[best_tr_idx, 1]))

        return tl, tr
