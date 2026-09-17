import numpy as np
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from aoi_system.core.context import InspectionContext
from aoi_system.pipeline.runner import TaskPipelineRunner
from aoi_system.pipeline.tasks.alignment_task import CornerAlignmentTask
from aoi_system.pipeline.tasks.base import VisionTask
from aoi_system.pipeline.tasks.preprocess_task import PreprocessTask
from aoi_system.pipeline.tasks.registry import TaskRegistry
from aoi_system.ui.components.image_viewport import ImageViewport


class TaskPipelineView(QWidget):
    """Modern visual editor for dynamic vision task chains and intermediate buffer inspection."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tasks: list[VisionTask] = []
        self._last_context: InspectionContext | None = None
        self._runner = TaskPipelineRunner()

        self._setup_ui()
        self._load_default_pipeline()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Left Column: Task Chain Control Panel
        left_panel = QFrame()
        left_panel.setObjectName("cardPanel")
        left_panel.setFixedWidth(360)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(10)

        title = QLabel("🛠️ 動態視覺算子管線 (Task Pipeline)")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #38bdf8;")
        left_layout.addWidget(title)

        # Task selection combo
        combo_layout = QHBoxLayout()
        self.combo_available_tasks = QComboBox()
        for t_name in TaskRegistry.list_available_tasks():
            self.combo_available_tasks.addItem(t_name)
        combo_layout.addWidget(self.combo_available_tasks)

        self.btn_add_task = QPushButton("➕ 新增算子")
        self.btn_add_task.setObjectName("primaryButton")
        self.btn_add_task.clicked.connect(self._on_add_task)
        combo_layout.addWidget(self.btn_add_task)
        left_layout.addLayout(combo_layout)

        # Task list widget
        self.task_list = QListWidget()
        left_layout.addWidget(self.task_list)

        # Reorder / Delete buttons
        reorder_layout = QHBoxLayout()
        self.btn_up = QPushButton("▲ 上移")
        self.btn_up.clicked.connect(self._on_move_up)
        self.btn_down = QPushButton("▼ 下移")
        self.btn_down.clicked.connect(self._on_move_down)
        self.btn_delete = QPushButton("🗑️ 刪除")
        self.btn_delete.setStyleSheet("background-color: #ef4444; color: white;")
        self.btn_delete.clicked.connect(self._on_delete_task)

        reorder_layout.addWidget(self.btn_up)
        reorder_layout.addWidget(self.btn_down)
        reorder_layout.addWidget(self.btn_delete)
        left_layout.addLayout(reorder_layout)

        # Execute Pipeline Button
        self.btn_run_pipeline = QPushButton("⚡ 執行任務鏈 (Run Pipeline)")
        self.btn_run_pipeline.setObjectName("primaryButton")
        self.btn_run_pipeline.setStyleSheet(
            "background-color: #10b981; font-weight: bold; padding: 10px; font-size: 13px;"
        )
        self.btn_run_pipeline.clicked.connect(self._on_execute_pipeline)
        left_layout.addWidget(self.btn_run_pipeline)

        layout.addWidget(left_panel)

        # Right Column: Viewport & Intermediate Buffer Switcher
        right_panel = QFrame()
        right_panel.setObjectName("cardPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(8)

        top_bar = QHBoxLayout()
        lbl_buffer = QLabel("中間處理緩衝區 (Buffer):")
        lbl_buffer.setStyleSheet("font-weight: bold; color: #cbd5e1;")
        self.combo_buffers = QComboBox()
        self.combo_buffers.setMinimumWidth(180)
        self.combo_buffers.currentTextChanged.connect(self._on_buffer_changed)
        top_bar.addWidget(lbl_buffer)
        top_bar.addWidget(self.combo_buffers)
        top_bar.addStretch()

        right_layout.addLayout(top_bar)

        self.viewport = ImageViewport()
        right_layout.addWidget(self.viewport, stretch=1)

        layout.addWidget(right_panel, stretch=1)

    def _load_default_pipeline(self) -> None:
        self._tasks.append(PreprocessTask(task_id="step1_thresh", threshold=128))
        self._tasks.append(CornerAlignmentTask(task_id="step2_align"))
        self._refresh_task_list()

    def _refresh_task_list(self) -> None:
        self.task_list.clear()
        for i, t in enumerate(self._tasks):
            item = QListWidgetItem(f"[{i + 1}] {t.task_type} (ID: {t.task_id})")
            self.task_list.addItem(item)

    def _on_add_task(self) -> None:
        t_type = self.combo_available_tasks.currentText()
        if not t_type:
            return
        t_id = f"task_{len(self._tasks) + 1}"
        task = TaskRegistry.create(t_id, t_type)
        self._tasks.append(task)
        self._refresh_task_list()

    def _on_delete_task(self) -> None:
        idx = self.task_list.currentRow()
        if 0 <= idx < len(self._tasks):
            self._tasks.pop(idx)
            self._refresh_task_list()

    def _on_move_up(self) -> None:
        idx = self.task_list.currentRow()
        if idx > 0:
            self._tasks[idx], self._tasks[idx - 1] = self._tasks[idx - 1], self._tasks[idx]
            self._refresh_task_list()
            self.task_list.setCurrentRow(idx - 1)

    def _on_move_down(self) -> None:
        idx = self.task_list.currentRow()
        if 0 <= idx < len(self._tasks) - 1:
            self._tasks[idx], self._tasks[idx + 1] = self._tasks[idx + 1], self._tasks[idx]
            self._refresh_task_list()
            self.task_list.setCurrentRow(idx + 1)

    def _on_execute_pipeline(self) -> None:
        # Create test synthetic frame
        img = np.zeros((300, 300), dtype=np.uint8)
        img[50:250, 50:250] = 200
        ctx = InspectionContext(slot_index=0, raw_image=img)

        self._runner.clear_tasks()
        for t in self._tasks:
            self._runner.add_task(t)

        self._runner.execute(ctx)
        self._last_context = ctx

        # Update available buffers
        self.combo_buffers.clear()
        for key in ctx.images.keys():
            self.combo_buffers.addItem(key)

    def _on_buffer_changed(self, key: str) -> None:
        if not key or not self._last_context:
            return
        img = self._last_context.get_image(key)
        if img is not None:
            self.viewport.set_image(img)
