from typing import override

import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QImage,
    QPainter,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QGraphicsItemGroup,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QWidget,
)

from aoi_system.core.models.geometry import BoundingRect, ReferenceCornerCandidate
from aoi_system.core.models.measurement import MeasureRecord


class ImageViewport(QGraphicsView):
    """High-performance hardware-accelerated image view with smooth pan/zoom
    and multi-layer overlays.
    """

    def __init__(self, parent: QWidget | None = None) -> None:

        super().__init__(parent)
        self.graphics_scene = QGraphicsScene(self)
        self.setScene(self.graphics_scene)

        # Layer Groups
        self.pixmap_item = QGraphicsPixmapItem()
        self.graphics_scene.addItem(self.pixmap_item)

        self.roi_item = QGraphicsRectItem()
        roi_pen = QPen(QColor("#0284c7"), 2, Qt.PenStyle.DashLine)
        self.roi_item.setPen(roi_pen)
        self.roi_item.setVisible(False)
        self.graphics_scene.addItem(self.roi_item)

        self.corner_group = QGraphicsItemGroup()
        self.graphics_scene.addItem(self.corner_group)

        self.measure_group = QGraphicsItemGroup()
        self.graphics_scene.addItem(self.measure_group)

        # Viewport render configuration
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setStyleSheet(
            "background-color: #121214; border: 1px solid #27272a; border-radius: 6px;"
        )

        self._zoom_factor = 1.15
        self._current_image_shape: tuple[int, int] | None = None

    def set_image(self, img: np.ndarray | None) -> None:
        """Sets viewport image from NumPy array with zero-copy or direct buffer mapping."""
        if img is None or img.size == 0:
            self.pixmap_item.setPixmap(QPixmap())
            self._current_image_shape = None
            return

        h, w = img.shape[:2]
        self._current_image_shape = (h, w)

        if img.ndim == 2:
            # Grayscale 8-bit
            qimg = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)
        elif img.ndim == 3 and img.shape[2] == 3:
            # BGR to RGB
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            bytes_per_line = 3 * w
            qimg = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        else:
            return

        pixmap = QPixmap.fromImage(qimg)
        self.pixmap_item.setPixmap(pixmap)
        self.graphics_scene.setSceneRect(0, 0, w, h)

    def set_roi(self, roi: BoundingRect | None) -> None:
        if roi is None or roi.width <= 0 or roi.height <= 0:
            self.roi_item.setVisible(False)
            return

        self.roi_item.setRect(roi.x, roi.y, roi.width, roi.height)
        self.roi_item.setVisible(True)

    def draw_reference_corner(self, candidate: ReferenceCornerCandidate | None) -> None:
        """Draws reference corner features (anchor, unit direction, bounding box)."""
        # Clear existing corner items
        for item in self.corner_group.childItems():
            self.graphics_scene.removeItem(item)

        if candidate is None:
            return

        pen = QPen(QColor("#eab308"), 2)  # Amber-yellow for corner
        brush = QBrush(QColor("#eab308"))

        # Anchor point (Top-Left)
        tl = candidate.top_left
        anchor_rect = self.graphics_scene.addEllipse(tl.x - 4, tl.y - 4, 8, 8, pen, brush)
        self.corner_group.addToGroup(anchor_rect)

        # Baseline connecting Top-Left to Top-Right
        tr = candidate.top_right
        base_line = self.graphics_scene.addLine(tl.x, tl.y, tr.x, tr.y, pen)
        self.corner_group.addToGroup(base_line)

        # Tag
        label = QGraphicsSimpleTextItem("REF_CORNER")
        label.setPos(tl.x + 8, tl.y - 14)
        label.setBrush(brush)
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        label.setFont(font)
        self.corner_group.addToGroup(label)

    def draw_measurements(
        self, records: list[MeasureRecord], values: dict[int, float] | None = None
    ) -> None:
        """Draws measurement lines, arrowheads, and physical mm annotations."""
        for item in self.measure_group.childItems():
            self.graphics_scene.removeItem(item)

        if not records:
            return

        pen = QPen(QColor("#06b6d4"), 2)  # Cyan for measurement lines
        brush = QBrush(QColor("#06b6d4"))
        font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)

        for i, rec in enumerate(records, start=1):
            p1 = rec.start_point
            p2 = rec.end_point

            line = self.graphics_scene.addLine(p1.x, p1.y, p2.x, p2.y, pen)
            self.measure_group.addToGroup(line)

            # Endpoints dots
            c1 = self.graphics_scene.addEllipse(p1.x - 3, p1.y - 3, 6, 6, pen, brush)
            c2 = self.graphics_scene.addEllipse(p2.x - 3, p2.y - 3, 6, 6, pen, brush)
            self.measure_group.addToGroup(c1)
            self.measure_group.addToGroup(c2)

            # Dimension Text
            mid_x = (p1.x + p2.x) / 2
            mid_y = (p1.y + p2.y) / 2
            val_text = f"L{i}: {values[i]:.3f} mm" if values and i in values else f"L{i}"

            text_item = QGraphicsSimpleTextItem(val_text)
            text_item.setPos(mid_x + 5, mid_y - 12)
            text_item.setBrush(brush)
            text_item.setFont(font)
            self.measure_group.addToGroup(text_item)

    def clear_overlays(self) -> None:
        self.set_roi(None)
        self.draw_reference_corner(None)
        self.draw_measurements([])

    def fit_in_view(self) -> None:
        """Fits whole image in viewport keeping aspect ratio."""
        if self._current_image_shape is not None:
            h, w = self._current_image_shape
            self.fitInView(0, 0, w, h, Qt.AspectRatioMode.KeepAspectRatio)

    def reset_view(self) -> None:
        self.resetTransform()
        self.fit_in_view()

    @override
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Smooth zooming anchored to cursor."""
        if event.angleDelta().y() > 0:
            factor = self._zoom_factor
        else:
            factor = 1.0 / self._zoom_factor
        self.scale(factor, factor)
