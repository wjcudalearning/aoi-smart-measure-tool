from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from aoi_system.algorithms.backend.manager import BackendManager, DeviceBackend
from aoi_system.core.models.recipe import InspectionRecipe
from aoi_system.ui.components.role_dialog import RoleSwitchDialog, UserRole
from aoi_system.ui.theme import DARK_INDUSTRIAL_QSS
from aoi_system.ui.viewmodels.inspection_viewmodel import InspectionViewModel
from aoi_system.ui.viewmodels.main_viewmodel import MainViewModel
from aoi_system.ui.views.batch_verify_view import BatchVerifyView
from aoi_system.ui.views.communication_view import CommunicationView
from aoi_system.ui.views.corner_view import CornerView
from aoi_system.ui.views.history_view import HistoryView
from aoi_system.ui.views.live_inspection_view import LiveInspectionView
from aoi_system.ui.views.preprocess_view import PreprocessView
from aoi_system.ui.views.recipe_editor_view import RecipeEditorView
from aoi_system.ui.views.task_pipeline_view import TaskPipelineView


class MainWindow(QMainWindow):
    """Modern Dark Industrial AOI Inspection System Main Window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AOI 智慧尺寸量測與品質判定系統 (AOI Smart Measure Tool)")
        self.resize(1366, 820)
        self.setStyleSheet(DARK_INDUSTRIAL_QSS)

        # View Models & Backend
        self.main_vm = MainViewModel()
        self.inspection_vm = InspectionViewModel()
        self.backend_mgr = BackendManager()

        self._setup_ui()
        self._setup_connections()
        self._on_role_changed(self.main_vm.current_role)

    def _setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("cardPanel")
        sidebar.setFixedWidth(210)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 16, 10, 16)
        sidebar_layout.setSpacing(8)

        # Brand / Logo
        logo_label = QLabel("⚡ AOI VISION AI")
        logo_label.setStyleSheet(
            "font-size: 16px; font-weight: 900; color: #38bdf8; letter-spacing: 1px;"
        )
        sub_logo = QLabel("Industrial Precision v0.1")
        sub_logo.setStyleSheet("font-size: 10px; color: #71717a; margin-bottom: 12px;")
        sidebar_layout.addWidget(logo_label)
        sidebar_layout.addWidget(sub_logo)

        # Navigation Buttons Group
        self.nav_btn_group = QButtonGroup(self)
        self.nav_btn_group.setExclusive(True)

        self.btn_nav_live = self._create_nav_button("📡 即時檢測看板", 0)
        self.btn_nav_preprocess = self._create_nav_button("🔬 影像前處理調校", 1)
        self.btn_nav_corner = self._create_nav_button("📐 基準角定位標定", 2)
        self.btn_nav_recipe = self._create_nav_button("📝 檢測配方編輯", 3)
        self.btn_nav_batch = self._create_nav_button("📊 批次多圖走查", 4)
        self.btn_nav_pipeline = self._create_nav_button("🛠️ 算子管線編排", 5)
        self.btn_nav_history = self._create_nav_button("📈 歷程與品質分析", 6)
        self.btn_nav_comm = self._create_nav_button("🌐 工業通訊與IO", 7)

        sidebar_layout.addWidget(self.btn_nav_live)
        sidebar_layout.addWidget(self.btn_nav_preprocess)
        sidebar_layout.addWidget(self.btn_nav_corner)
        sidebar_layout.addWidget(self.btn_nav_recipe)
        sidebar_layout.addWidget(self.btn_nav_batch)
        sidebar_layout.addWidget(self.btn_nav_pipeline)
        sidebar_layout.addWidget(self.btn_nav_history)
        sidebar_layout.addWidget(self.btn_nav_comm)
        sidebar_layout.addStretch()

        # Role & User info at bottom of sidebar
        role_frame = QFrame()
        role_frame.setObjectName("cardPanel")
        role_layout = QVBoxLayout(role_frame)
        role_layout.setContentsMargins(8, 8, 8, 8)

        self.label_role = QLabel(f"身分: {self.main_vm.current_role.value}")
        self.label_role.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        btn_switch_role = QPushButton("🔑 切換權限")
        btn_switch_role.clicked.connect(self._open_role_dialog)

        role_layout.addWidget(self.label_role)
        role_layout.addWidget(btn_switch_role)
        sidebar_layout.addWidget(role_frame)

        root_layout.addWidget(sidebar)

        # 2. Right Main Content Area
        content_container = QWidget()
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Top Bar
        top_bar = QFrame()
        top_bar.setFixedHeight(46)
        top_bar.setStyleSheet("background-color: #1f1f23; border-bottom: 1px solid #3f3f46;")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 16, 0)

        self.label_active_recipe = QLabel("當前配方: DEFAULT_RECIPE")
        self.label_active_recipe.setStyleSheet("font-weight: bold; color: #f4f4f5;")

        # GPU / CPU backend badge
        is_cuda = self.backend_mgr.current_backend == DeviceBackend.CUDA
        backend_txt = "🟢 GPU: CUDA / CuPy 加速" if is_cuda else "🔵 CPU: NumPy 運算"
        self.label_backend = QLabel(backend_txt)
        self.label_backend.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: 500;")

        top_layout.addWidget(self.label_active_recipe)
        top_layout.addStretch()
        top_layout.addWidget(self.label_backend)
        content_layout.addWidget(top_bar)

        # Stacked Pages
        self.stack = QStackedWidget()
        self.view_live = LiveInspectionView(self.inspection_vm)
        self.view_preprocess = PreprocessView(self.main_vm)
        self.view_corner = CornerView(self.main_vm)
        self.view_recipe = RecipeEditorView(self.main_vm)
        self.view_batch = BatchVerifyView(self.main_vm)
        self.view_pipeline = TaskPipelineView()
        self.view_history = HistoryView()
        self.view_comm = CommunicationView()

        self.stack.addWidget(self.view_live)  # Index 0
        self.stack.addWidget(self.view_preprocess)  # Index 1
        self.stack.addWidget(self.view_corner)  # Index 2
        self.stack.addWidget(self.view_recipe)  # Index 3
        self.stack.addWidget(self.view_batch)  # Index 4
        self.stack.addWidget(self.view_pipeline)  # Index 5
        self.stack.addWidget(self.view_history)  # Index 6
        self.stack.addWidget(self.view_comm)  # Index 7

        content_layout.addWidget(self.stack, stretch=1)
        root_layout.addWidget(content_container, stretch=1)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系統就緒 (System Ready)")

    def _create_nav_button(self, text: str, page_index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setFixedHeight(40)
        btn.setStyleSheet(
            "QPushButton { text-align: left; padding-left: 14px; font-size: 13px; border: none; } "
            "QPushButton:checked { background-color: #0284c7; color: white; font-weight: bold; } "
            "QPushButton:hover:!checked { background-color: #27272a; }"
        )
        if page_index == 0:
            btn.setChecked(True)
        self.nav_btn_group.addButton(btn, page_index)
        btn.clicked.connect(lambda: self.stack.setCurrentIndex(page_index))
        return btn

    def _setup_connections(self) -> None:
        self.main_vm.role_changed.connect(self._on_role_changed)
        self.main_vm.recipe_changed.connect(self._on_recipe_changed)
        self.main_vm.status_message.connect(self.status_bar.showMessage)

    def _on_role_changed(self, role: UserRole) -> None:
        self.label_role.setText(f"身分: {role.value}")
        # Restrict UI tabs if Operator
        is_operator = role == UserRole.OPERATOR
        self.btn_nav_preprocess.setEnabled(not is_operator)
        self.btn_nav_corner.setEnabled(not is_operator)
        self.btn_nav_recipe.setEnabled(not is_operator)
        self.btn_nav_batch.setEnabled(not is_operator)
        if is_operator and self.stack.currentIndex() != 0:
            self.btn_nav_live.click()

    def _on_recipe_changed(self, recipe: InspectionRecipe) -> None:
        self.label_active_recipe.setText(f"當前配方: {recipe.product_key}")
        # Sync to all slots in inspection viewmodel
        for slot in range(3):
            self.inspection_vm.set_slot_recipe(slot, recipe)

    def _open_role_dialog(self) -> None:
        dialog = RoleSwitchDialog(self.main_vm.current_role, self)
        if dialog.exec():
            self.main_vm.set_role(dialog.selected_role)
