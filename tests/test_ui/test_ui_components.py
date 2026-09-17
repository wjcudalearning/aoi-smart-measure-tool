import numpy as np

from aoi_system.core.models.geometry import (
    BoundingRect,
    Point2D,
    Point2I,
    ReferenceCornerCandidate,
    RotatedRect,
)
from aoi_system.core.models.measurement import MeasureRecord
from aoi_system.core.models.recipe import InspectionRecipe
from aoi_system.ui.components.image_viewport import ImageViewport
from aoi_system.ui.components.role_dialog import RoleSwitchDialog, UserRole
from aoi_system.ui.components.stat_card import StatCard
from aoi_system.ui.main_window import MainWindow
from aoi_system.ui.viewmodels.inspection_viewmodel import InspectionViewModel
from aoi_system.ui.viewmodels.main_viewmodel import MainViewModel


def test_stat_card(qapp):
    card = StatCard("良品率", "99.8%", "合格 / 總量", accent_color="#16a34a")
    assert card.title_label.text() == "良品率"
    assert card.value_label.text() == "99.8%"

    card.set_value("100.0%")
    assert card.value_label.text() == "100.0%"

    card.set_subtitle("更新中")
    assert card.subtitle_label.text() == "更新中"


def test_image_viewport(qapp):
    viewport = ImageViewport()

    # 1. Grayscale image
    gray = np.zeros((100, 100), dtype=np.uint8)
    gray[20:80, 20:80] = 255
    viewport.set_image(gray)
    assert viewport._current_image_shape == (100, 100)

    # 2. BGR image
    bgr = np.zeros((100, 100, 3), dtype=np.uint8)
    bgr[:, :, 0] = 255
    viewport.set_image(bgr)
    assert viewport._current_image_shape == (100, 100)

    # 3. ROI
    roi = BoundingRect(x=10, y=10, width=50, height=50)
    viewport.set_roi(roi)
    assert viewport.roi_item.isVisible() is True

    # 4. Reference corner candidate
    candidate = ReferenceCornerCandidate(
        rotated_rect=RotatedRect(center=Point2D(x=50, y=50), width=30, height=20, angle_degrees=0),
        top_left=Point2I(x=20, y=20),
        top_right=Point2I(x=80, y=20),
        center_point=Point2I(x=50, y=20),
        bounding_rect=roi,
    )
    viewport.draw_reference_corner(candidate)
    assert len(viewport.corner_group.childItems()) > 0

    # 5. Measurements
    records = [MeasureRecord(start_point=Point2I(x=10, y=10), end_point=Point2I(x=90, y=10))]
    viewport.draw_measurements(records, {1: 0.45})
    assert len(viewport.measure_group.childItems()) > 0

    # 6. Clear
    viewport.clear_overlays()
    assert viewport.roi_item.isVisible() is False
    assert len(viewport.corner_group.childItems()) == 0
    assert len(viewport.measure_group.childItems()) == 0


def test_role_switch_dialog(qapp):
    dialog = RoleSwitchDialog(current_role=UserRole.OPERATOR)

    # Select Operator -> no password required
    dialog.combo.setCurrentText(UserRole.OPERATOR.value)
    assert dialog.pwd_input.isEnabled() is False

    # Select Engineer -> password required
    dialog.combo.setCurrentText(UserRole.ENGINEER.value)
    assert dialog.pwd_input.isEnabled() is True
    dialog.pwd_input.setText("1234")
    dialog._validate_and_accept()
    assert dialog.selected_role == UserRole.ENGINEER


def test_main_viewmodel(qapp):
    vm = MainViewModel()
    emitted_roles = []
    vm.role_changed.connect(lambda r: emitted_roles.append(r))

    vm.set_role(UserRole.ENGINEER)
    assert vm.current_role == UserRole.ENGINEER
    assert len(emitted_roles) == 1

    emitted_recipes = []
    vm.recipe_changed.connect(lambda r: emitted_recipes.append(r))
    new_recipe = InspectionRecipe(product_key="TEST_MODEL_X")
    vm.set_active_recipe(new_recipe)
    assert vm.active_recipe.product_key == "TEST_MODEL_X"
    assert len(emitted_recipes) == 1


def test_inspection_viewmodel(qapp):
    vm = InspectionViewModel()

    # Manual single step trigger
    res = vm.trigger_single_step(0)
    assert res is not None
    assert res.slot_index == 0

    # Reset slot yield
    vm.reset_slot_yield(0)
    stats = vm.orchestrator.get_slot_yield(0)
    assert stats["total"] == 0

    # Cleanup
    vm.orchestrator.stop()


def test_main_window_navigation(qapp):
    win = MainWindow()
    assert win.stack.currentIndex() == 0  # Live inspection
    assert win.btn_nav_preprocess.isEnabled() is False

    # Switch to Engineer to enable protected tabs
    win.main_vm.set_role(UserRole.ENGINEER)
    assert win.btn_nav_preprocess.isEnabled() is True

    # Switch to Preprocess view
    win.btn_nav_preprocess.click()
    assert win.stack.currentIndex() == 1

    # Switch to Corner view
    win.btn_nav_corner.click()
    assert win.stack.currentIndex() == 2

    # Switch to Recipe view
    win.btn_nav_recipe.click()
    assert win.stack.currentIndex() == 3

    # Switch to Batch view
    win.btn_nav_batch.click()
    assert win.stack.currentIndex() == 4

    # Role restriction test: switch back to Operator
    win.main_vm.set_role(UserRole.OPERATOR)
    assert win.btn_nav_preprocess.isEnabled() is False
    assert win.stack.currentIndex() == 0  # redirected to Live

    win.inspection_vm.orchestrator.stop()
