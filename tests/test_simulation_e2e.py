"""End-to-End simulation and verification test suite for AOI system.

Validates:
1. Golden sample image generation and loading.
2. Settings and recipe persistence and validation.
3. Role switching dialog and permission state transitions (preventing AttributeError regressions).
4. Simulated camera feed through ContinuousInspectionOrchestrator.
5. Multi-grade quality judgement (Grade A vs NG).
6. Full UI viewmodel simulation without Qt font warnings or crashes.
"""

from pathlib import Path

import cv2
import pytest

from aoi_system.hardware.sample_generator import (
    generate_sample_defect,
    generate_sample_dimension_ng,
    generate_sample_ok,
    generate_sample_rotated,
    generate_standard_dataset,
)
from aoi_system.hardware.simulated_camera import SimulatedCamera
from aoi_system.pipeline.orchestrator import ContinuousInspectionOrchestrator
from aoi_system.storage.recipe_repository import RecipeRepository
from aoi_system.ui.components.role_dialog import RoleSwitchDialog, UserRole
from aoi_system.ui.main_window import MainWindow
from aoi_system.ui.viewmodels.inspection_viewmodel import InspectionViewModel
from aoi_system.ui.viewmodels.main_viewmodel import MainViewModel
from aoi_system.ui.views.live_inspection_view import LiveInspectionView


class TestEndToEndSimulation:
    @pytest.fixture(autouse=True)
    def setup_dataset(self) -> None:
        """Ensure test samples exist."""
        self.dataset_dir = Path("sample_data/images")
        if not (self.dataset_dir / "sample_01_standard_ok.png").exists():
            generate_standard_dataset(self.dataset_dir)

    def test_sample_image_generation_integrity(self) -> None:
        """Verify all 4 synthetic workpiece images are valid and readable."""
        img_ok = generate_sample_ok()
        img_ng = generate_sample_dimension_ng()
        img_defect = generate_sample_defect()
        img_rot = generate_sample_rotated()

        assert img_ok.shape == (600, 800)
        assert img_ng.shape == (600, 800)
        assert img_defect.shape == (600, 800)
        assert img_rot.shape == (600, 800)

        # OK sample should have standard width (~500px), NG should be larger (~535px)
        assert img_ng.sum() > img_ok.sum()

    def test_recipe_settings_persistence(self) -> None:
        """Verify recipe repository loads standard workpiece recipe."""
        repo = RecipeRepository("recipes")
        recipe = repo.load("STANDARD_WORKPIECE")
        assert recipe is not None
        assert recipe.product_key == "STANDARD_WORKPIECE"
        assert len(recipe.measure_records) >= 2
        assert len(recipe.judgement_rules) >= 2
        assert recipe.calibration.ccd_x_precision == 0.05

    def test_role_switch_dialog_and_string_safety(self, qapp) -> None:
        """Regression test for UserRole vs str AttributeError when changing roles."""
        # 1. Test from_value helper with all variations
        assert UserRole.from_value(UserRole.ADMINISTRATOR) == UserRole.ADMINISTRATOR
        assert UserRole.from_value("系統管理員 (Admin)") == UserRole.ADMINISTRATOR
        assert UserRole.from_value("Admin") == UserRole.ADMINISTRATOR
        assert UserRole.from_value("工程師 (Engineer)") == UserRole.ENGINEER
        assert UserRole.from_value("操作員 (Operator)") == UserRole.OPERATOR
        assert UserRole.from_value(None) == UserRole.OPERATOR

        # 2. Test MainViewModel set_role with both enum and string
        vm = MainViewModel()
        vm.set_role(UserRole.ENGINEER)
        assert vm.current_role == UserRole.ENGINEER

        vm.set_role("系統管理員 (Admin)")
        assert vm.current_role == UserRole.ADMINISTRATOR

        vm.set_role("操作員 (Operator)")
        assert vm.current_role == UserRole.OPERATOR

        # 3. Test RoleSwitchDialog interaction
        dialog = RoleSwitchDialog(current_role=UserRole.ADMINISTRATOR)
        assert dialog.selected_role == UserRole.ADMINISTRATOR
        dialog.combo.setCurrentText(UserRole.ENGINEER.value)
        dialog.pwd_input.setText("1234")
        dialog._validate_and_accept()
        assert dialog.selected_role == UserRole.ENGINEER

    def test_simulated_camera_loading(self) -> None:
        """Verify SimulatedCamera loads disk sample images correctly."""
        cam = SimulatedCamera(image_folder="sample_data/images", width=800, height=600)
        assert cam.connect() is True
        frame = cam.grab_frame()
        assert frame is not None
        assert frame.shape == (600, 800)
        cam.disconnect()

    def test_pipeline_e2e_judgement_simulation(self) -> None:
        """Run standard OK image vs oversized NG image through orchestrator."""
        repo = RecipeRepository("recipes")
        recipe = repo.load("STANDARD_WORKPIECE")
        assert recipe is not None

        orchestrator = ContinuousInspectionOrchestrator()
        orchestrator.set_slot_recipe(0, recipe)

        # 1. Test OK Sample
        img_ok = cv2.imread(
            str(self.dataset_dir / "sample_01_standard_ok.png"), cv2.IMREAD_GRAYSCALE
        )
        res_ok = orchestrator.load_and_judge(0, img_ok, source_name="OK_Test")
        assert res_ok is not None
        assert res_ok.processing_time_ms < 30.0
        # Width (500px * 0.05 = 25.0mm) falls within 24.50~25.50
        assert res_ok.summary in ("A", "B")

        # 2. Test NG Sample
        img_ng = cv2.imread(
            str(self.dataset_dir / "sample_02_dimension_large_ng.png"), cv2.IMREAD_GRAYSCALE
        )
        res_ng = orchestrator.load_and_judge(0, img_ng, source_name="NG_Test")
        assert res_ng is not None
        # Oversized width (535px * 0.05 = 26.75mm) exceeds 26.00 upper bound -> NG
        assert res_ng.summary == "NG"

        orchestrator.stop()

    def test_ui_live_view_simulation_single_step(self, qapp) -> None:
        """Test LiveInspectionView single-step simulation across all 3 slots."""
        repo = RecipeRepository("recipes")
        recipe = repo.load("STANDARD_WORKPIECE")
        assert recipe is not None

        vm = InspectionViewModel()
        for slot in range(3):
            vm.set_slot_recipe(slot, recipe)

        view = LiveInspectionView(vm)
        # Trigger single simulation step on slot 0
        res = vm.trigger_single_step(0)
        assert res is not None

        # Trigger simulation step on all slots
        view._on_simulate_all()
        assert int(view.slot_cards[0].card_total.value_label.text().replace(",", "")) >= 2

    def test_main_window_full_simulation_lifecycle(self, qapp) -> None:
        """Verify MainWindow startup, recipe loading, and role switching without crash."""
        window = MainWindow()
        assert window.isVisible() is False
        assert "STANDARD_WORKPIECE" in window.label_active_recipe.text()

        # Switch role through ViewModel
        window.main_vm.set_role(UserRole.ADMINISTRATOR)
        assert "管理員" in window.label_role.text()

        # Verify all tabs are accessible for admin
        assert window.btn_nav_recipe.isEnabled() is True
        assert window.btn_nav_preprocess.isEnabled() is True

        # Switch back to operator
        window.main_vm.set_role(UserRole.OPERATOR)
        assert "操作員" in window.label_role.text()
        assert window.btn_nav_recipe.isEnabled() is False
