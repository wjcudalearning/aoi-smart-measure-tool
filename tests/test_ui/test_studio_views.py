import os
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from aoi_system.storage.database.models import InspectionRecordModel
from aoi_system.storage.database.sqlite_db import SqliteInspectionDatabase
from aoi_system.ui.main_window import MainWindow
from aoi_system.ui.views.communication_view import CommunicationView
from aoi_system.ui.views.history_view import HistoryView
from aoi_system.ui.views.task_pipeline_view import TaskPipelineView


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestStudioViews:
    def test_task_pipeline_view(self, qapp) -> None:
        view = TaskPipelineView()
        assert view is not None
        assert len(view._tasks) >= 2

        # Add task
        view.combo_available_tasks.setCurrentText("CircleFitTask")
        view._on_add_task()
        assert any(t.task_type == "CircleFitTask" for t in view._tasks)

        # Move up/down
        view.task_list.setCurrentRow(len(view._tasks) - 1)
        view._on_move_up()
        view._on_move_down()

        # Execute
        view._on_execute_pipeline()
        assert view.combo_buffers.count() > 0

        # Delete
        view.task_list.setCurrentRow(0)
        view._on_delete_task()

    def test_history_view(self, qapp, tmp_path: Path) -> None:
        db_path = tmp_path / "hist_view.db"
        db = SqliteInspectionDatabase(db_path)
        db.insert_record_sync(
            InspectionRecordModel(
                timestamp="2026-09-17T12:00:00",
                slot_index=0,
                recipe_name="Part1",
                overall_grade="A",
                execution_time_ms=1.5,
                measurements_json="{}",
                anomalies_json="[]",
            )
        )

        view = HistoryView(database=db)
        assert view.table.rowCount() == 1
        assert view.card_total.value_label.text() == "1"

        # Filter query
        view.combo_slot.setCurrentText("Slot 0")
        view._refresh_data()
        assert view.table.rowCount() == 1

        db.close()

    def test_communication_view(self, qapp) -> None:
        view = CommunicationView()
        assert view is not None

        # Toggle Modbus (in simulation mode)
        view._on_toggle_modbus()
        assert view.modbus_client.is_connected is True
        view._on_toggle_modbus()
        assert view.modbus_client.is_connected is False

        # Fire test triggers
        view._fire_trigger(0)
        view._fire_trigger(1)

    def test_main_window_tabs(self, qapp) -> None:
        from aoi_system.ui.components.role_dialog import UserRole

        window = MainWindow()
        window.main_vm.set_role(UserRole.ADMINISTRATOR)
        assert window.stack.count() == 8

        # Test switching across all tabs
        for idx in range(8):
            btn = window.nav_btn_group.button(idx)
            if btn:
                btn.click()
            assert window.stack.currentIndex() == idx
