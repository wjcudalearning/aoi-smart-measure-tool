from collections.abc import Callable

import numpy as np
from PySide6.QtCore import QObject, Signal

from aoi_system.core.models.recipe import InspectionRecipe
from aoi_system.core.models.results import ContinuousInspectionResult
from aoi_system.hardware.simulated_camera import SimulatedCamera
from aoi_system.pipeline.orchestrator import ContinuousInspectionOrchestrator


class InspectionViewModel(QObject):
    """View model orchestrating 3-slot continuous inspection and UI updates."""

    inspection_completed = Signal(int, object)  # slot_index, ContinuousInspectionResult
    frame_received = Signal(int, object)  # slot_index, np.ndarray
    yield_updated = Signal(int, dict)  # slot_index, stats dict
    running_state_changed = Signal(bool)

    def __init__(self, orchestrator: ContinuousInspectionOrchestrator | None = None) -> None:
        super().__init__()
        self.orchestrator = orchestrator or ContinuousInspectionOrchestrator()
        self._is_running = False

        # Cameras for each slot
        self.cameras: dict[int, SimulatedCamera] = {
            i: SimulatedCamera(device_id=f"SIM_CAM_{i}", name=f"Slot {i} Camera", fps=20.0)
            for i in range(ContinuousInspectionOrchestrator.NUM_SLOTS)
        }

        # Hook orchestrator callbacks to view model signals
        for slot in range(ContinuousInspectionOrchestrator.NUM_SLOTS):
            self.orchestrator.register_slot_callback(
                slot,
                self._make_orchestrator_callback(slot),
            )

    def _make_orchestrator_callback(
        self, slot: int
    ) -> Callable[[ContinuousInspectionResult], None]:
        def cb(res: ContinuousInspectionResult) -> None:
            self._on_orchestrator_result(slot, res)

        return cb

    def _make_camera_callback(self, slot: int) -> Callable[[np.ndarray], None]:
        def cb(frame: np.ndarray) -> None:
            self._on_camera_frame(slot, frame)

        return cb

    def set_slot_recipe(self, slot_index: int, recipe: InspectionRecipe) -> None:
        self.orchestrator.set_slot_recipe(slot_index, recipe)

    def start_all(self) -> None:
        if self._is_running:
            return
        self._is_running = True

        for slot_idx, cam in self.cameras.items():
            cam.connect()
            # Register camera frame hook
            cam.register_frame_callback(self._make_camera_callback(slot_idx))
            cam.start_grabbing()

        self.running_state_changed.emit(True)

    def stop_all(self) -> None:
        if not self._is_running:
            return
        self._is_running = False

        for cam in self.cameras.values():
            cam.stop_grabbing()
            cam.disconnect()

        self.running_state_changed.emit(False)

    def trigger_single_step(self, slot_index: int) -> ContinuousInspectionResult | None:
        """Manually captures and inspects a single frame on specified slot."""
        cam = self.cameras.get(slot_index)
        if not cam:
            return None
        if not cam.is_connected:
            cam.connect()

        frame = cam.grab_frame()
        if frame is not None:
            self.frame_received.emit(slot_index, frame)
            res = self.orchestrator.load_and_judge(
                slot_index, frame, source_name=f"Manual_Slot_{slot_index}"
            )
            self._on_orchestrator_result(slot_index, res)
            return res
        return None

    def reset_slot_yield(self, slot_index: int) -> None:
        self.orchestrator.reset_slot_yield(slot_index)
        stats = self.orchestrator.get_slot_yield(slot_index)
        self.yield_updated.emit(slot_index, stats)

    def _on_camera_frame(self, slot_index: int, frame: np.ndarray) -> None:
        self.frame_received.emit(slot_index, frame)
        self.orchestrator.submit_async(slot_index, frame, source_name=f"Live_Slot_{slot_index}")

    def _on_orchestrator_result(self, slot_index: int, result: ContinuousInspectionResult) -> None:
        self.inspection_completed.emit(slot_index, result)
        stats = self.orchestrator.get_slot_yield(slot_index)
        self.yield_updated.emit(slot_index, stats)
