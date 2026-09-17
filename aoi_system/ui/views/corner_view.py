import numpy as np
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from aoi_system.algorithms.corner_detection.detector import ReferenceCornerDetector
from aoi_system.core.models.geometry import BoundingRect
from aoi_system.core.models.recipe import ReferenceCornerPointMode, ReferenceCornerSnapshot
from aoi_system.ui.components.image_viewport import ImageViewport
from aoi_system.ui.components.stat_card import StatCard
from aoi_system.ui.viewmodels.main_viewmodel import MainViewModel


class CornerView(QWidget):
    """Reference corner detection calibration and coordinate system alignment workspace."""

    def __init__(self, main_viewmodel: MainViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_viewmodel = main_viewmodel
        self.detector = ReferenceCornerDetector()

        # Synthetic sample image with a workpiece rectangle
        self.image = np.zeros((480, 640), dtype=np.uint8)
        self.image[80:320, 100:460] = 255

        self._setup_ui()
        self._detect_corner()

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Left Control Panel
        control_panel = QFrame()
        control_panel.setObjectName("cardPanel")
        control_panel.setFixedWidth(340)
        ctrl_layout = QVBoxLayout(control_panel)
        ctrl_layout.setSpacing(10)

        title = QLabel("基準角定位標定 (Reference Corner)")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f4f4f5;")
        ctrl_layout.addWidget(title)

        # Point mode
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("演算法模式:"))
        self.combo_mode = QComboBox()
        self.combo_mode.addItem(
            "輪廓極值點 (Contour Nearest)", ReferenceCornerPointMode.CONTOUR_NEAREST
        )
        self.combo_mode.addItem("ROI 上邊緣 (ROI Top Edge)", ReferenceCornerPointMode.ROI_TOP_EDGE)
        self.combo_mode.addItem("掃描尋邊 (Scan Search)", ReferenceCornerPointMode.SCAN_SEARCH)
        self.combo_mode.currentIndexChanged.connect(self._on_param_changed)
        mode_layout.addWidget(self.combo_mode)
        ctrl_layout.addLayout(mode_layout)

        # ROI Parameters
        roi_box = QFrame()
        roi_box.setObjectName("cardPanel")
        roi_layout = QGridLayout(roi_box)
        roi_layout.addWidget(QLabel("搜尋 ROI 設定:"), 0, 0, 1, 2)

        self.spin_x = self._create_spin(0, 4000, 50)
        self.spin_y = self._create_spin(0, 4000, 50)
        self.spin_w = self._create_spin(10, 4000, 300)
        self.spin_h = self._create_spin(10, 4000, 200)

        roi_layout.addWidget(QLabel("ROI X:"), 1, 0)
        roi_layout.addWidget(self.spin_x, 1, 1)
        roi_layout.addWidget(QLabel("ROI Y:"), 2, 0)
        roi_layout.addWidget(self.spin_y, 2, 1)
        roi_layout.addWidget(QLabel("ROI 寬度:"), 3, 0)
        roi_layout.addWidget(self.spin_w, 3, 1)
        roi_layout.addWidget(QLabel("ROI 高度:"), 4, 0)
        roi_layout.addWidget(self.spin_h, 4, 1)
        ctrl_layout.addWidget(roi_box)

        # Detected results summary
        self.card_anchor = StatCard("錨點座標 (Anchor TL)", "(0, 0)", accent_color="#eab308")
        self.card_angle = StatCard("基準方向角 (Angle)", "0.0°", accent_color="#38bdf8")
        ctrl_layout.addWidget(self.card_anchor)
        ctrl_layout.addWidget(self.card_angle)

        ctrl_layout.addStretch()

        btn_detect = QPushButton("執行基準角定位")
        btn_detect.clicked.connect(self._detect_corner)
        btn_save = QPushButton("儲存基準角至配方")
        btn_save.setObjectName("primaryButton")
        btn_save.clicked.connect(self._save_to_recipe)

        ctrl_layout.addWidget(btn_detect)
        ctrl_layout.addWidget(btn_save)
        main_layout.addWidget(control_panel)

        # Right Viewport
        self.viewport = ImageViewport()
        self.viewport.set_image(self.image)
        self.viewport.fit_in_view()
        main_layout.addWidget(self.viewport, stretch=1)

    def _create_spin(self, min_val: int, max_val: int, default_val: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default_val)
        spin.valueChanged.connect(self._on_param_changed)
        return spin

    def _on_param_changed(self) -> None:
        roi = BoundingRect(
            x=self.spin_x.value(),
            y=self.spin_y.value(),
            width=self.spin_w.value(),
            height=self.spin_h.value(),
        )
        self.viewport.set_roi(roi)
        self._detect_corner()

    def _detect_corner(self) -> None:
        roi = BoundingRect(
            x=self.spin_x.value(),
            y=self.spin_y.value(),
            width=self.spin_w.value(),
            height=self.spin_h.value(),
        )
        self.viewport.set_roi(roi)

        mode = self.combo_mode.currentData()
        snapshot = ReferenceCornerSnapshot(
            enabled=True,
            point_mode=mode,
            roi=roi,
            scan_line_threshold=50,
        )

        candidate = self.detector.find_candidate(self.image, snapshot)
        if candidate is not None:
            self.viewport.draw_reference_corner(candidate)
            tl = candidate.top_left
            self.card_anchor.set_value(f"({tl.x}, {tl.y})")
            self.card_angle.set_value(f"{candidate.rotated_rect.angle_degrees:.2f}°")
        else:
            self.viewport.draw_reference_corner(None)
            self.card_anchor.set_value("未尋得特徵")
            self.card_angle.set_value("N/A")

    def _save_to_recipe(self) -> None:
        recipe = self.main_viewmodel.active_recipe
        mode = self.combo_mode.currentData()
        recipe.reference_corner = ReferenceCornerSnapshot(
            enabled=True,
            point_mode=mode,
            roi=BoundingRect(
                x=self.spin_x.value(),
                y=self.spin_y.value(),
                width=self.spin_w.value(),
                height=self.spin_h.value(),
            ),
            scan_line_threshold=50,
        )
        self.main_viewmodel.status_message.emit("基準角設定已同步儲存至當前配方！")
