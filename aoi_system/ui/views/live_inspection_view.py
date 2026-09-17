import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from aoi_system.core.models.results import ContinuousInspectionResult
from aoi_system.ui.components.image_viewport import ImageViewport
from aoi_system.ui.components.stat_card import StatCard
from aoi_system.ui.theme import (
    COLOR_GRADE_A,
    COLOR_GRADE_B,
    COLOR_GRADE_NG,
    COLOR_GRADE_READY,
)
from aoi_system.ui.viewmodels.inspection_viewmodel import InspectionViewModel


class SlotInspectionCard(QFrame):
    """Card representing one AOI inspection slot with viewport, badges, and yield counters."""

    def __init__(
        self, slot_index: int, viewmodel: InspectionViewModel, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.slot_index = slot_index
        self.viewmodel = viewmodel
        self.setObjectName("cardPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. Header
        header_layout = QHBoxLayout()
        self.title_label = QLabel(f"通道 {slot_index + 1} (Slot {slot_index})")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #f4f4f5;")
        self.latency_label = QLabel("0.0 ms")
        self.latency_label.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.latency_label)
        layout.addLayout(header_layout)

        # 2. Viewport
        self.viewport = ImageViewport()
        self.viewport.setMinimumHeight(240)
        layout.addWidget(self.viewport, stretch=1)

        # 3. Judgement Badge
        self.badge_label = QLabel("READY")
        self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.badge_label.setFixedHeight(46)
        self.badge_label.setStyleSheet(
            f"background-color: {COLOR_GRADE_READY}; color: white; font-size: 24px; "
            f"font-weight: 800; border-radius: 6px; letter-spacing: 2px;"
        )
        layout.addWidget(self.badge_label)

        # 4. Yield Counters
        stats_layout = QGridLayout()
        stats_layout.setSpacing(4)
        self.card_total = StatCard("檢測總數", "0", accent_color="#38bdf8")
        self.card_a = StatCard("A 規良品", "0 (0%)", accent_color=COLOR_GRADE_A)
        self.card_b = StatCard("B 規次品", "0 (0%)", accent_color=COLOR_GRADE_B)
        self.card_ng = StatCard("NG 不良品", "0 (0%)", accent_color=COLOR_GRADE_NG)

        stats_layout.addWidget(self.card_total, 0, 0)
        stats_layout.addWidget(self.card_a, 0, 1)
        stats_layout.addWidget(self.card_b, 1, 0)
        stats_layout.addWidget(self.card_ng, 1, 1)
        layout.addLayout(stats_layout)

        # 5. Slot Action Buttons
        btn_layout = QHBoxLayout()
        self.btn_step = QPushButton("單次拍照檢測")
        self.btn_step.clicked.connect(lambda: self.viewmodel.trigger_single_step(self.slot_index))
        self.btn_reset = QPushButton("重置計數")
        self.btn_reset.clicked.connect(lambda: self.viewmodel.reset_slot_yield(self.slot_index))

        btn_layout.addWidget(self.btn_step)
        btn_layout.addWidget(self.btn_reset)
        layout.addLayout(btn_layout)

    def update_result(self, result: ContinuousInspectionResult) -> None:
        self.latency_label.setText(f"{result.processing_time_ms:.1f} ms")
        grade = result.summary
        if grade == "A":
            bg_color = COLOR_GRADE_A
        elif grade == "B":
            bg_color = COLOR_GRADE_B
        elif grade == "NG":
            bg_color = COLOR_GRADE_NG
        else:
            bg_color = COLOR_GRADE_READY

        self.badge_label.setText(grade)
        self.badge_label.setStyleSheet(
            f"background-color: {bg_color}; color: white; font-size: 24px; "
            f"font-weight: 800; border-radius: 6px; letter-spacing: 2px;"
        )

    def update_frame(self, frame: np.ndarray) -> None:
        self.viewport.set_image(frame)
        self.viewport.fit_in_view()

    def update_yield(self, stats: dict[str, int]) -> None:
        total = stats.get("total", 0)
        a_cnt = stats.get("A", 0)
        b_cnt = stats.get("B", 0)
        ng_cnt = stats.get("NG", 0)

        a_pct = (a_cnt / total * 100) if total > 0 else 0.0
        b_pct = (b_cnt / total * 100) if total > 0 else 0.0
        ng_pct = (ng_cnt / total * 100) if total > 0 else 0.0

        self.card_total.set_value(f"{total:,}")
        self.card_a.set_value(f"{a_cnt:,} ({a_pct:.1f}%)")
        self.card_b.set_value(f"{b_cnt:,} ({b_pct:.1f}%)")
        self.card_ng.set_value(f"{ng_cnt:,} ({ng_pct:.1f}%)")


class LiveInspectionView(QWidget):
    """3-Slot live continuous inspection dashboard."""

    def __init__(self, viewmodel: InspectionViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.viewmodel = viewmodel

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Global Control Bar
        bar = QFrame()
        bar.setObjectName("cardPanel")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 6, 8, 6)

        title = QLabel("三通道平行即時檢測儀表板 (3-Slot Continuous Inspection)")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #f4f4f5;")

        self.btn_start = QPushButton("▶ 啟動全通道連續檢測")
        self.btn_start.setObjectName("primaryButton")
        self.btn_start.clicked.connect(self.viewmodel.start_all)

        self.btn_simulate = QPushButton("🧪 模擬單次檢測 (Simulate Step)")
        self.btn_simulate.clicked.connect(self._on_simulate_all)

        self.btn_stop = QPushButton("⏹ 停止檢測")
        self.btn_stop.clicked.connect(self.viewmodel.stop_all)
        self.btn_stop.setEnabled(False)

        bar_layout.addWidget(title)
        bar_layout.addStretch()
        bar_layout.addWidget(self.btn_simulate)
        bar_layout.addWidget(self.btn_start)
        bar_layout.addWidget(self.btn_stop)
        layout.addWidget(bar)

        # 3 Slots Layout
        slots_layout = QHBoxLayout()
        slots_layout.setSpacing(10)

        self.slot_cards: dict[int, SlotInspectionCard] = {}
        for i in range(3):
            card = SlotInspectionCard(i, self.viewmodel)
            self.slot_cards[i] = card
            slots_layout.addWidget(card, stretch=1)

        layout.addLayout(slots_layout, stretch=1)

        # Connect viewmodel signals
        self.viewmodel.frame_received.connect(self._on_frame)
        self.viewmodel.inspection_completed.connect(self._on_result)
        self.viewmodel.yield_updated.connect(self._on_yield)
        self.viewmodel.running_state_changed.connect(self._on_running_changed)

    def _on_running_changed(self, running: bool) -> None:
        self.btn_start.setEnabled(not running)
        self.btn_stop.setEnabled(running)

    def _on_frame(self, slot: int, frame: np.ndarray) -> None:
        if slot in self.slot_cards:
            self.slot_cards[slot].update_frame(frame)

    def _on_result(self, slot: int, result: ContinuousInspectionResult) -> None:
        if slot in self.slot_cards:
            self.slot_cards[slot].update_result(result)

    def _on_yield(self, slot: int, stats: dict[str, int]) -> None:
        if slot in self.slot_cards:
            self.slot_cards[slot].update_yield(stats)

    def _on_simulate_all(self) -> None:
        """Triggers a simulated single inspection step across all 3 slots."""
        for slot in range(3):
            self.viewmodel.trigger_single_step(slot)
