from pathlib import Path

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from aoi_system.core.models.geometry import Point2I
from aoi_system.core.models.measurement import MeasureDirectionMode, MeasureRecord
from aoi_system.core.models.recipe import (
    CameraCalibration,
    InspectionRecipe,
    JudgementCriterionRule,
)
from aoi_system.storage.legacy_migrator import LegacyIniMigrator
from aoi_system.storage.recipe_repository import RecipeRepository
from aoi_system.ui.viewmodels.main_viewmodel import MainViewModel


class RecipeEditorView(QWidget):
    """Visual Recipe Editor for inspection lines, tolerance rules, and calibration parameters."""

    def __init__(self, main_viewmodel: MainViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_viewmodel = main_viewmodel
        self.repo = RecipeRepository()

        self._setup_ui()
        self._load_from_active_recipe()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Top Metadata Bar
        meta_frame = QFrame()
        meta_frame.setObjectName("cardPanel")
        meta_layout = QGridLayout(meta_frame)
        meta_layout.setContentsMargins(10, 8, 10, 8)

        meta_layout.addWidget(QLabel("產品型號 (Product Key):"), 0, 0)
        self.input_key = QLineEdit()
        meta_layout.addWidget(self.input_key, 0, 1)

        meta_layout.addWidget(QLabel("CCD X 精度 (mm/px):"), 0, 2)
        self.spin_ccd_x = QDoubleSpinBox()
        self.spin_ccd_x.setDecimals(6)
        self.spin_ccd_x.setRange(0.000001, 10.0)
        self.spin_ccd_x.setValue(0.005)
        meta_layout.addWidget(self.spin_ccd_x, 0, 3)

        meta_layout.addWidget(QLabel("CCD Y 精度 (mm/px):"), 0, 4)
        self.spin_ccd_y = QDoubleSpinBox()
        self.spin_ccd_y.setDecimals(6)
        self.spin_ccd_y.setRange(0.000001, 10.0)
        self.spin_ccd_y.setValue(0.005)
        meta_layout.addWidget(self.spin_ccd_y, 0, 5)

        meta_layout.addWidget(QLabel("尺寸縮放係數 (Scale Factor):"), 1, 0)
        self.spin_scale = QDoubleSpinBox()
        self.spin_scale.setDecimals(4)
        self.spin_scale.setRange(0.001, 100.0)
        self.spin_scale.setValue(1.0)
        meta_layout.addWidget(self.spin_scale, 1, 1)

        layout.addWidget(meta_frame)

        # Tabs for Measurements & Judgements
        self.tabs = QTabWidget()

        # Tab 1: Measurements
        tab_measures = QWidget()
        m_layout = QVBoxLayout(tab_measures)
        self.table_measures = QTableWidget(0, 5)
        self.table_measures.setHorizontalHeaderLabels(
            ["ID", "起點 (X, Y)", "終點 (X, Y)", "前處理來源", "量測方向模式"]
        )
        self.table_measures.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        m_layout.addWidget(self.table_measures)

        m_btn_layout = QHBoxLayout()
        btn_add_m = QPushButton("＋ 新增量測線")
        btn_add_m.clicked.connect(self._add_measure_row)
        btn_del_m = QPushButton("－ 刪除選取線段")
        btn_del_m.clicked.connect(self._del_measure_row)
        m_btn_layout.addWidget(btn_add_m)
        m_btn_layout.addWidget(btn_del_m)
        m_btn_layout.addStretch()
        m_layout.addLayout(m_btn_layout)

        self.tabs.addTab(tab_measures, "量測線配置 (Measurement Lines)")

        # Tab 2: Judgement Rules
        tab_rules = QWidget()
        r_layout = QVBoxLayout(tab_rules)
        self.table_rules = QTableWidget(0, 5)
        self.table_rules.setHorizontalHeaderLabels(
            ["項目名稱", "計算式 (A)", "規格範圍 (A)", "計算式 (B)", "規格範圍 (B)"]
        )
        self.table_rules.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        r_layout.addWidget(self.table_rules)

        r_btn_layout = QHBoxLayout()
        btn_add_r = QPushButton("＋ 新增判定規則")
        btn_add_r.clicked.connect(self._add_rule_row)
        btn_del_r = QPushButton("－ 刪除選取規則")
        btn_del_r.clicked.connect(self._del_rule_row)
        r_btn_layout.addWidget(btn_add_r)
        r_btn_layout.addWidget(btn_del_r)
        r_btn_layout.addStretch()
        r_layout.addLayout(r_btn_layout)

        self.tabs.addTab(tab_rules, "公差評判規格 (Tolerance Rules)")
        layout.addWidget(self.tabs, stretch=1)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        btn_import_ini = QPushButton("📥 匯入舊版 INI 配方...")
        btn_import_ini.clicked.connect(self._import_legacy_ini)

        btn_load_json = QPushButton("📂 開啟 JSON 配方...")
        btn_load_json.clicked.connect(self._load_json_recipe)

        btn_save_json = QPushButton("💾 儲存配方 (JSON)")
        btn_save_json.setObjectName("primaryButton")
        btn_save_json.clicked.connect(self._save_recipe)

        bottom_bar.addWidget(btn_import_ini)
        bottom_bar.addWidget(btn_load_json)
        bottom_bar.addStretch()
        bottom_bar.addWidget(btn_save_json)
        layout.addLayout(bottom_bar)

    def _load_from_active_recipe(self) -> None:
        recipe = self.main_viewmodel.active_recipe
        self.input_key.setText(recipe.product_key)
        self.spin_ccd_x.setValue(recipe.calibration.ccd_x_precision)
        self.spin_ccd_y.setValue(recipe.calibration.ccd_y_precision)
        self.spin_scale.setValue(recipe.calibration.measurement_scale_factor)

        # Measurements
        self.table_measures.setRowCount(0)
        for i, rec in enumerate(recipe.measure_records, start=1):
            row = self.table_measures.rowCount()
            self.table_measures.insertRow(row)
            self.table_measures.setItem(row, 0, QTableWidgetItem(f"L{i}"))
            self.table_measures.setItem(
                row, 1, QTableWidgetItem(f"{rec.start_point.x}, {rec.start_point.y}")
            )
            self.table_measures.setItem(
                row, 2, QTableWidgetItem(f"{rec.end_point.x}, {rec.end_point.y}")
            )
            self.table_measures.setItem(row, 3, QTableWidgetItem(rec.source_name or "Preprocess 1"))
            self.table_measures.setItem(row, 4, QTableWidgetItem(rec.direction.value))

        # Rules
        self.table_rules.setRowCount(0)
        for rule in recipe.judgement_rules:
            row = self.table_rules.rowCount()
            self.table_rules.insertRow(row)
            self.table_rules.setItem(row, 0, QTableWidgetItem(rule.name))
            self.table_rules.setItem(row, 1, QTableWidgetItem(rule.calc_expression))
            self.table_rules.setItem(row, 2, QTableWidgetItem(rule.spec_expression))
            self.table_rules.setItem(row, 3, QTableWidgetItem(rule.calc_expression_b))
            self.table_rules.setItem(row, 4, QTableWidgetItem(rule.spec_expression_b))

    def _add_measure_row(self) -> None:
        row = self.table_measures.rowCount()
        self.table_measures.insertRow(row)
        self.table_measures.setItem(row, 0, QTableWidgetItem(f"L{row + 1}"))
        self.table_measures.setItem(row, 1, QTableWidgetItem("100, 150"))
        self.table_measures.setItem(row, 2, QTableWidgetItem("200, 150"))
        self.table_measures.setItem(row, 3, QTableWidgetItem("Preprocess 1"))
        self.table_measures.setItem(row, 4, QTableWidgetItem(MeasureDirectionMode.PARALLEL.value))

    def _del_measure_row(self) -> None:
        row = self.table_measures.currentRow()
        if row >= 0:
            self.table_measures.removeRow(row)

    def _add_rule_row(self) -> None:
        row = self.table_rules.rowCount()
        self.table_rules.insertRow(row)
        self.table_rules.setItem(row, 0, QTableWidgetItem(f"Item_{row + 1}"))
        self.table_rules.setItem(row, 1, QTableWidgetItem("(1)"))
        self.table_rules.setItem(row, 2, QTableWidgetItem("10.0+-0.5"))
        self.table_rules.setItem(row, 3, QTableWidgetItem("(1)"))
        self.table_rules.setItem(row, 4, QTableWidgetItem("10.0+-1.0"))

    def _del_rule_row(self) -> None:
        row = self.table_rules.currentRow()
        if row >= 0:
            self.table_rules.removeRow(row)

    def _save_recipe(self) -> None:
        recipe = self._build_recipe_from_ui()
        self.main_viewmodel.set_active_recipe(recipe)

        file_path, _ = QFileDialog.getSaveFileName(
            self, "儲存配方 (JSON)", f"{recipe.product_key}.json", "JSON Files (*.json)"
        )
        if file_path:
            p = Path(file_path)
            p.write_text(recipe.model_dump_json(indent=2), encoding="utf-8")
            QMessageBox.information(self, "儲存成功", f"配方已成功儲存至:\n{file_path}")

    def _load_json_recipe(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "開啟 JSON 配方", "", "JSON Files (*.json)"
        )
        if file_path:
            try:
                p = Path(file_path)
                recipe = InspectionRecipe.model_validate_json(p.read_text(encoding="utf-8"))
                self.main_viewmodel.set_active_recipe(recipe)
                self._load_from_active_recipe()
            except Exception as e:
                QMessageBox.critical(self, "讀取失敗", f"無法解析配方檔案: {e}")

    def _import_legacy_ini(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇舊版 setting.ini", "", "INI Files (*.ini)"
        )
        if file_path:
            try:
                migrator = LegacyIniMigrator()
                bundle = migrator.migrate_all(Path(file_path))
                if bundle.recipes:
                    first_recipe = next(iter(bundle.recipes.values()))
                    self.main_viewmodel.set_active_recipe(first_recipe)
                    self._load_from_active_recipe()
                    QMessageBox.information(
                        self,
                        "匯入成功",
                        f"成功解析舊版 INI，已匯入 {len(bundle.recipes)} 組產品配方！",
                    )
            except Exception as e:
                QMessageBox.critical(self, "匯入失敗", f"舊版 INI 解析異常: {e}")

    def _build_recipe_from_ui(self) -> InspectionRecipe:
        recipe = self.main_viewmodel.active_recipe.model_copy()
        recipe.product_key = self.input_key.text().strip() or "DEFAULT"
        recipe.calibration = CameraCalibration(
            ccd_x_precision=self.spin_ccd_x.value(),
            ccd_y_precision=self.spin_ccd_y.value(),
            measurement_scale_factor=self.spin_scale.value(),
        )

        # Parse measures
        records: list[MeasureRecord] = []
        for r in range(self.table_measures.rowCount()):
            it_p1 = self.table_measures.item(r, 1)
            it_p2 = self.table_measures.item(r, 2)
            it_src = self.table_measures.item(r, 3)
            it_dir = self.table_measures.item(r, 4)

            p1_str = it_p1.text() if it_p1 else ""
            p2_str = it_p2.text() if it_p2 else ""
            src = it_src.text() if it_src else "Preprocess 1"
            dir_str = it_dir.text() if it_dir else ""

            p1_parts = [int(x.strip()) for x in p1_str.split(",") if x.strip().isdigit()]
            p2_parts = [int(x.strip()) for x in p2_str.split(",") if x.strip().isdigit()]
            p1 = Point2I(x=p1_parts[0], y=p1_parts[1]) if len(p1_parts) == 2 else Point2I()
            p2 = Point2I(x=p2_parts[0], y=p2_parts[1]) if len(p2_parts) == 2 else Point2I()

            mode = MeasureDirectionMode.NONE
            if dir_str == MeasureDirectionMode.PARALLEL.value:
                mode = MeasureDirectionMode.PARALLEL
            elif dir_str == MeasureDirectionMode.PERPENDICULAR.value:
                mode = MeasureDirectionMode.PERPENDICULAR

            records.append(
                MeasureRecord(
                    start_point=p1,
                    end_point=p2,
                    source_name=src,
                    direction=mode,
                )
            )
        recipe.measure_records = records

        # Parse rules
        rules: list[JudgementCriterionRule] = []
        for r in range(self.table_rules.rowCount()):
            it_name = self.table_rules.item(r, 0)
            it_ca = self.table_rules.item(r, 1)
            it_sa = self.table_rules.item(r, 2)
            it_cb = self.table_rules.item(r, 3)
            it_sb = self.table_rules.item(r, 4)

            name = it_name.text() if it_name else f"Rule_{r + 1}"
            calc_a = it_ca.text() if it_ca else ""
            spec_a = it_sa.text() if it_sa else ""
            calc_b = it_cb.text() if it_cb else ""
            spec_b = it_sb.text() if it_sb else ""

            rules.append(
                JudgementCriterionRule(
                    name=name,
                    calc_expression=calc_a,
                    spec_expression=spec_a,
                    calc_expression_b=calc_b,
                    spec_expression_b=spec_b,
                )
            )
        recipe.judgement_rules = rules

        return recipe
