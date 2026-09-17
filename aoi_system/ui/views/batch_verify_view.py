import csv
from pathlib import Path

import cv2
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from aoi_system.pipeline.orchestrator import ContinuousInspectionOrchestrator
from aoi_system.ui.components.stat_card import StatCard
from aoi_system.ui.theme import COLOR_GRADE_A, COLOR_GRADE_B, COLOR_GRADE_NG
from aoi_system.ui.viewmodels.main_viewmodel import MainViewModel


class BatchVerifyView(QWidget):
    """Batch golden sample inspection runner and CSV report generator."""

    def __init__(self, main_viewmodel: MainViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_viewmodel = main_viewmodel
        self.orchestrator = ContinuousInspectionOrchestrator()
        self.results_data: list[dict[str, str]] = []

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Control Bar
        top_bar = QFrame()
        top_bar.setObjectName("cardPanel")
        bar_layout = QHBoxLayout(top_bar)

        title = QLabel("批次多圖走查與公差驗證 (Batch Sample Inspection)")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f4f4f5;")

        btn_select_dir = QPushButton("📁 選擇測試圖檔目錄...")
        btn_select_dir.clicked.connect(self._select_directory)

        self.btn_run = QPushButton("⚡ 開始批次驗證")
        self.btn_run.setObjectName("primaryButton")
        self.btn_run.clicked.connect(self._run_batch_inspection)

        btn_export = QPushButton("📊 匯出 CSV 報告...")
        btn_export.clicked.connect(self._export_csv)

        bar_layout.addWidget(title)
        bar_layout.addStretch()
        bar_layout.addWidget(btn_select_dir)
        bar_layout.addWidget(self.btn_run)
        bar_layout.addWidget(btn_export)
        layout.addWidget(top_bar)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setTextVisible(False)
        layout.addWidget(self.progress_bar)

        # KPI Cards
        cards_layout = QHBoxLayout()
        self.card_total = StatCard("總檢測數", "0", accent_color="#38bdf8")
        self.card_a = StatCard("A 規良品", "0 (0%)", accent_color=COLOR_GRADE_A)
        self.card_b = StatCard("B 規次品", "0 (0%)", accent_color=COLOR_GRADE_B)
        self.card_ng = StatCard("NG 不良品", "0 (0%)", accent_color=COLOR_GRADE_NG)

        cards_layout.addWidget(self.card_total)
        cards_layout.addWidget(self.card_a)
        cards_layout.addWidget(self.card_b)
        cards_layout.addWidget(self.card_ng)
        layout.addLayout(cards_layout)

        # Results Table
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["序號", "圖檔名稱", "綜合判定", "規則數值", "耗時 (ms)"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, stretch=1)

        self.target_folder: Path | None = None

    def _select_directory(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "選擇影像目錄")
        if folder:
            self.target_folder = Path(folder)
            self.main_viewmodel.status_message.emit(f"已選取測試圖檔目錄: {folder}")

    def _run_batch_inspection(self) -> None:
        if not self.target_folder or not self.target_folder.is_dir():
            QMessageBox.warning(self, "未選擇目錄", "請先選擇包含測試影像的目錄！")
            return

        image_files: list[Path] = []
        for ext in ("*.png", "*.bmp", "*.jpg", "*.jpeg", "*.tif", "*.tiff"):
            image_files.extend(self.target_folder.glob(ext))
        image_files.sort()

        if not image_files:
            QMessageBox.warning(self, "無影像", "選取的目錄中未找到任何支援的圖檔！")
            return

        recipe = self.main_viewmodel.active_recipe
        self.orchestrator.set_slot_recipe(0, recipe)

        self.table.setRowCount(0)
        self.results_data.clear()
        self.progress_bar.setRange(0, len(image_files))

        total_cnt = len(image_files)
        a_cnt = 0
        b_cnt = 0
        ng_cnt = 0

        for i, fpath in enumerate(image_files, start=1):
            img = cv2.imread(str(fpath), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            res = self.orchestrator.load_and_judge(0, img, source_name=fpath.name)
            rule_str = "; ".join(f"{r.rule_name}={r.calculation_value}" for r in res.rules)

            if res.summary == "A":
                a_cnt += 1
            elif res.summary == "B":
                b_cnt += 1
            elif res.summary == "NG":
                ng_cnt += 1

            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(i)))
            self.table.setItem(row, 1, QTableWidgetItem(fpath.name))
            self.table.setItem(row, 2, QTableWidgetItem(res.summary))
            self.table.setItem(row, 3, QTableWidgetItem(rule_str))
            self.table.setItem(row, 4, QTableWidgetItem(f"{res.processing_time_ms:.1f}"))

            self.results_data.append(
                {
                    "Index": str(i),
                    "Filename": fpath.name,
                    "Judgement": res.summary,
                    "Rules": rule_str,
                    "LatencyMs": f"{res.processing_time_ms:.1f}",
                }
            )

            self.progress_bar.setValue(i)

        a_pct = (a_cnt / total_cnt * 100) if total_cnt > 0 else 0.0
        b_pct = (b_cnt / total_cnt * 100) if total_cnt > 0 else 0.0
        ng_pct = (ng_cnt / total_cnt * 100) if total_cnt > 0 else 0.0

        self.card_total.set_value(str(total_cnt))
        self.card_a.set_value(f"{a_cnt} ({a_pct:.1f}%)")
        self.card_b.set_value(f"{b_cnt} ({b_pct:.1f}%)")
        self.card_ng.set_value(f"{ng_cnt} ({ng_pct:.1f}%)")

    def _export_csv(self) -> None:
        if not self.results_data:
            QMessageBox.warning(self, "無資料", "目前無可匯出的驗證紀錄！")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "匯出 CSV 報告", "batch_inspection_report.csv", "CSV Files (*.csv)"
        )
        if file_path:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["Index", "Filename", "Judgement", "Rules", "LatencyMs"]
                )
                writer.writeheader()
                writer.writerows(self.results_data)
            QMessageBox.information(self, "匯出完成", f"CSV 報告已儲存至:\n{file_path}")
