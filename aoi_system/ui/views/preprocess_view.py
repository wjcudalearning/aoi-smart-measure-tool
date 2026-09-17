import cv2
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from aoi_system.algorithms.preprocess.filters import PreprocessPipeline
from aoi_system.core.models.recipe import PreprocessSnapshot
from aoi_system.ui.components.image_viewport import ImageViewport
from aoi_system.ui.viewmodels.main_viewmodel import MainViewModel


class PreprocessView(QWidget):
    """Interactive preprocessing calibration workspace with real-time
    thresholding and morphology preview.
    """

    def __init__(self, main_viewmodel: MainViewModel, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.main_viewmodel = main_viewmodel
        self.pipeline = PreprocessPipeline()

        # Generate default synthetic test image if none loaded
        self.raw_image: np.ndarray = np.zeros((480, 640), dtype=np.uint8)
        self.raw_image[100:380, 150:490] = 180
        cv2.circle(self.raw_image, (320, 240), 60, 255, -1)
        self.processed_image: np.ndarray = self.raw_image.copy()

        self._setup_ui()
        self._update_preview()

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # Left Control Panel
        control_panel = QFrame()
        control_panel.setObjectName("cardPanel")
        control_panel.setFixedWidth(360)
        ctrl_layout = QVBoxLayout(control_panel)
        ctrl_layout.setSpacing(10)

        title = QLabel("前處理參數調校 (Preprocess Tuning)")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #f4f4f5;")
        ctrl_layout.addWidget(title)

        # Preset selector
        preset_layout = QHBoxLayout()
        preset_label = QLabel("前處理組別:")
        self.combo_preset = QComboBox()
        self.combo_preset.addItems(["Preprocess 1", "Preprocess 2", "Preprocess 3", "Preprocess 4"])
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.combo_preset)
        ctrl_layout.addLayout(preset_layout)

        # Dual threshold checkbox
        self.chk_dual = QCheckBox("啟用雙門檻分割 (Dual Threshold)")
        self.chk_dual.toggled.connect(self._on_param_changed)
        ctrl_layout.addWidget(self.chk_dual)

        # Sliders grid
        sliders_grid = QGridLayout()
        sliders_grid.setSpacing(8)

        # Threshold
        self.slider_thresh = self._create_slider(0, 255, 128)
        self.spin_thresh = self._create_spinbox(0, 255, 128, self.slider_thresh)
        sliders_grid.addWidget(QLabel("門檻值 / 下限:"), 0, 0)
        sliders_grid.addWidget(self.slider_thresh, 0, 1)
        sliders_grid.addWidget(self.spin_thresh, 0, 2)

        # Upper threshold
        self.slider_upper = self._create_slider(0, 255, 255)
        self.spin_upper = self._create_spinbox(0, 255, 255, self.slider_upper)
        sliders_grid.addWidget(QLabel("上限門檻:"), 1, 0)
        sliders_grid.addWidget(self.slider_upper, 1, 1)
        sliders_grid.addWidget(self.spin_upper, 1, 2)

        # Erode
        self.slider_erode = self._create_slider(0, 10, 0)
        self.spin_erode = self._create_spinbox(0, 10, 0, self.slider_erode)
        sliders_grid.addWidget(QLabel("侵蝕 (Erode):"), 2, 0)
        sliders_grid.addWidget(self.slider_erode, 2, 1)
        sliders_grid.addWidget(self.spin_erode, 2, 2)

        # Dilate
        self.slider_dilate = self._create_slider(0, 10, 0)
        self.spin_dilate = self._create_spinbox(0, 10, 0, self.slider_dilate)
        sliders_grid.addWidget(QLabel("膨脹 (Dilate):"), 3, 0)
        sliders_grid.addWidget(self.slider_dilate, 3, 1)
        sliders_grid.addWidget(self.spin_dilate, 3, 2)

        # Open
        self.slider_open = self._create_slider(0, 10, 0)
        self.spin_open = self._create_spinbox(0, 10, 0, self.slider_open)
        sliders_grid.addWidget(QLabel("開運算 (Open):"), 4, 0)
        sliders_grid.addWidget(self.slider_open, 4, 1)
        sliders_grid.addWidget(self.spin_open, 4, 2)

        # Close
        self.slider_close = self._create_slider(0, 10, 0)
        self.spin_close = self._create_spinbox(0, 10, 0, self.slider_close)
        sliders_grid.addWidget(QLabel("閉運算 (Close):"), 5, 0)
        sliders_grid.addWidget(self.slider_close, 5, 1)
        sliders_grid.addWidget(self.spin_close, 5, 2)

        ctrl_layout.addLayout(sliders_grid)
        ctrl_layout.addStretch()

        # Action buttons
        btn_load = QPushButton("載入本機圖片測試")
        btn_load.clicked.connect(self._load_local_image)
        btn_apply = QPushButton("儲存設定至配方")
        btn_apply.setObjectName("primaryButton")
        btn_apply.clicked.connect(self._save_to_recipe)

        ctrl_layout.addWidget(btn_load)
        ctrl_layout.addWidget(btn_apply)
        main_layout.addWidget(control_panel)

        # Right Dual Viewport Area
        view_container = QWidget()
        view_layout = QHBoxLayout(view_container)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(8)

        # Left: Original Viewport
        orig_box = QVBoxLayout()
        orig_title = QLabel("原圖 (Original Image)")
        orig_title.setStyleSheet("color: #a1a1aa; font-weight: bold;")
        self.orig_viewport = ImageViewport()
        self.orig_viewport.set_image(self.raw_image)
        self.orig_viewport.fit_in_view()
        orig_box.addWidget(orig_title)
        orig_box.addWidget(self.orig_viewport)
        view_layout.addLayout(orig_box)

        # Right: Processed Binary Viewport
        proc_box = QVBoxLayout()
        proc_title = QLabel("前處理二值化預覽 (Binary Preview)")
        proc_title.setStyleSheet("color: #38bdf8; font-weight: bold;")
        self.proc_viewport = ImageViewport()
        proc_box.addWidget(proc_title)
        proc_box.addWidget(self.proc_viewport)
        view_layout.addLayout(proc_box)

        main_layout.addWidget(view_container, stretch=1)

    def _create_slider(self, min_val: int, max_val: int, default_val: int) -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.valueChanged.connect(self._on_param_changed)
        return slider

    def _create_spinbox(
        self, min_val: int, max_val: int, default_val: int, slider: QSlider
    ) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        spin.setValue(default_val)
        spin.setFixedWidth(55)
        slider.valueChanged.connect(spin.setValue)
        spin.valueChanged.connect(slider.setValue)
        return spin

    def _on_param_changed(self) -> None:
        self._update_preview()

    def _update_preview(self) -> None:
        config = PreprocessSnapshot(
            enabled=True,
            threshold=self.slider_thresh.value(),
            upper_threshold=self.slider_upper.value(),
            use_dual_threshold=self.chk_dual.isChecked(),
            erode_iterations=self.slider_erode.value(),
            dilate_iterations=self.slider_dilate.value(),
            open_iterations=self.slider_open.value(),
            close_iterations=self.slider_close.value(),
        )
        self.processed_image = self.pipeline.apply_preprocess(self.raw_image, config)
        self.proc_viewport.set_image(self.processed_image)
        self.proc_viewport.fit_in_view()

    def _load_local_image(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "選擇影像", "", "Images (*.png *.bmp *.jpg *.jpeg *.tif *.tiff)"
        )
        if file_path:
            img = cv2.imread(file_path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self.raw_image = img
                self.orig_viewport.set_image(self.raw_image)
                self.orig_viewport.fit_in_view()
                self._update_preview()

    def _save_to_recipe(self) -> None:
        recipe = self.main_viewmodel.active_recipe
        idx = self.combo_preset.currentIndex()
        if 0 <= idx < len(recipe.preprocess_snapshots):
            recipe.preprocess_snapshots[idx] = PreprocessSnapshot(
                enabled=True,
                threshold=self.slider_thresh.value(),
                upper_threshold=self.slider_upper.value(),
                use_dual_threshold=self.chk_dual.isChecked(),
                erode_iterations=self.slider_erode.value(),
                dilate_iterations=self.slider_dilate.value(),
                open_iterations=self.slider_open.value(),
                close_iterations=self.slider_close.value(),
            )
            self.main_viewmodel.status_message.emit(f"已儲存 Preprocess {idx + 1} 參數至當前配方！")
