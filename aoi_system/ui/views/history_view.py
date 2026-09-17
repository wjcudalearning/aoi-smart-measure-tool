from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from aoi_system.storage.database.analytics import QualityAnalyticsService
from aoi_system.storage.database.models import InspectionRecordModel
from aoi_system.storage.database.sqlite_db import SqliteInspectionDatabase
from aoi_system.storage.exporter import ReportExporter
from aoi_system.ui.components.stat_card import StatCard


class HistoryView(QWidget):
    """Historical inspection records viewer with process capability analytics and export."""

    def __init__(
        self,
        database: SqliteInspectionDatabase | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.db = database or SqliteInspectionDatabase()
        self.analytics = QualityAnalyticsService()
        self.exporter = ReportExporter()
        self._current_records: list[InspectionRecordModel] = []

        self._setup_ui()
        self._refresh_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 1. Top KPI Summary Cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(10)
        self.card_total = StatCard("總檢測數", "0", accent_color="#38bdf8")
        self.card_yield = StatCard("即時良率 (Yield)", "0.0%", accent_color="#10b981")
        self.card_a = StatCard("A規合格數", "0", accent_color="#10b981")
        self.card_b = StatCard("B規降級數", "0", accent_color="#f59e0b")
        self.card_ng = StatCard("NG不合格數", "0", accent_color="#ef4444")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_yield)
        kpi_layout.addWidget(self.card_a)
        kpi_layout.addWidget(self.card_b)
        kpi_layout.addWidget(self.card_ng)
        layout.addLayout(kpi_layout)

        # 2. Filter and Action Toolbar
        toolbar = QFrame()
        toolbar.setObjectName("cardPanel")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(10, 8, 10, 8)
        tb_layout.setSpacing(10)

        tb_layout.addWidget(QLabel("通道篩選:"))
        self.combo_slot = QComboBox()
        self.combo_slot.addItems(["全部 (All)", "Slot 0", "Slot 1", "Slot 2"])
        tb_layout.addWidget(self.combo_slot)

        tb_layout.addWidget(QLabel("判定結果:"))
        self.combo_grade = QComboBox()
        self.combo_grade.addItems(["全部 (All)", "A", "B", "NG"])
        tb_layout.addWidget(self.combo_grade)

        self.btn_query = QPushButton("🔍 查詢紀錄")
        self.btn_query.setObjectName("primaryButton")
        self.btn_query.clicked.connect(self._refresh_data)
        tb_layout.addWidget(self.btn_query)

        tb_layout.addStretch()

        self.btn_export_csv = QPushButton("📥 匯出 CSV")
        self.btn_export_csv.clicked.connect(self._on_export_csv)
        self.btn_export_excel = QPushButton("📊 匯出 Excel")
        self.btn_export_excel.clicked.connect(self._on_export_excel)

        tb_layout.addWidget(self.btn_export_csv)
        tb_layout.addWidget(self.btn_export_excel)
        layout.addWidget(toolbar)

        # 3. Records Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "時間戳記 (Timestamp)", "通道", "配方名稱", "最終判定", "耗時 (ms)", "尺寸數值"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, stretch=1)

    def _refresh_data(self) -> None:
        slot_text = self.combo_slot.currentText()
        slot_idx: int | None = None
        if "Slot" in slot_text:
            slot_idx = int(slot_text.split()[-1])

        grade_text = self.combo_grade.currentText()
        grade_filter: str | None = grade_text if grade_text in ("A", "B", "NG") else None

        records = self.db.query_records(limit=200, slot_index=slot_idx, grade=grade_filter)
        self._current_records = records

        # Update KPI cards
        stats = self.analytics.calculate_yield_stats(records)
        self.card_total.set_value(str(stats["total"]))
        self.card_yield.set_value(f"{stats['yield_rate'] * 100:.1f}%")
        self.card_a.set_value(str(stats["count_A"]))
        self.card_b.set_value(str(stats["count_B"]))
        self.card_ng.set_value(str(stats["count_NG"]))

        # Populate Table
        self.table.setRowCount(len(records))
        for row, r in enumerate(records):
            self.table.setItem(row, 0, QTableWidgetItem(str(r.record_id or "")))
            self.table.setItem(row, 1, QTableWidgetItem(r.timestamp))
            self.table.setItem(row, 2, QTableWidgetItem(f"Slot {r.slot_index}"))
            self.table.setItem(row, 3, QTableWidgetItem(r.recipe_name))

            grade_item = QTableWidgetItem(r.overall_grade)
            if r.overall_grade == "A":
                grade_item.setForeground(Qt.GlobalColor.green)
            elif r.overall_grade == "B":
                grade_item.setForeground(Qt.GlobalColor.yellow)
            else:
                grade_item.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 4, grade_item)

            self.table.setItem(row, 5, QTableWidgetItem(f"{r.execution_time_ms:.2f}"))
            self.table.setItem(row, 6, QTableWidgetItem(r.measurements_json))

    def _on_export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "匯出 CSV 報表", "inspection_report.csv", "CSV Files (*.csv)"
        )
        if path:
            out = self.exporter.export_to_csv(self._current_records, Path(path))
            QMessageBox.information(self, "匯出成功", f"檢測記錄已成功匯出至:\n{out}")

    def _on_export_excel(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "匯出 Excel 報表", "inspection_report.xlsx", "Excel Files (*.xlsx)"
        )
        if path:
            out = self.exporter.export_to_excel(self._current_records, Path(path))
            QMessageBox.information(self, "匯出成功", f"檢測記錄已成功匯出至:\n{out}")
