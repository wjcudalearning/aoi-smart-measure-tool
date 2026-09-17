import queue
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from aoi_system.core.models.results import ContinuousInspectionResult
from aoi_system.pipeline.context import InspectionContext


class InspectionSlotWorker:
    """Dedicated background worker executing inspections for a single slot.

    Includes queue isolation, zero-copy memory flow, and non-blocking background image saving.
    """

    def __init__(
        self,
        slot_index: int,
        process_fn: Callable[[InspectionContext], ContinuousInspectionResult],
        max_queue_size: int = 30,
    ) -> None:
        self.slot_index = slot_index
        self._process_fn = process_fn
        self._task_queue: queue.Queue[InspectionContext | None] = queue.Queue(
            maxsize=max_queue_size
        )
        self._save_queue: queue.Queue[tuple[Path, np.ndarray] | None] = queue.Queue(maxsize=100)
        self._worker_thread: threading.Thread | None = None
        self._saver_thread: threading.Thread | None = None
        self._is_running = False
        self._callbacks: list[Callable[[ContinuousInspectionResult], None]] = []

        # Raw image saving options
        self.save_raw_enabled: bool = False
        self.save_directory: Path = Path(f"data/captures/slot_{slot_index}")

    def start(self) -> None:
        if self._is_running:
            return
        self._is_running = True
        self._worker_thread = threading.Thread(
            target=self._run_inspection_loop,
            name=f"InspectionSlotWorker-{self.slot_index}",
            daemon=True,
        )
        self._worker_thread.start()

        self._saver_thread = threading.Thread(
            target=self._run_saver_loop,
            name=f"ImageSaverSlot-{self.slot_index}",
            daemon=True,
        )
        self._saver_thread.start()

    def stop(self) -> None:
        if not self._is_running:
            return
        self._is_running = False
        self._task_queue.put(None)
        self._save_queue.put(None)
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=1.0)
        if self._saver_thread and self._saver_thread.is_alive():
            self._saver_thread.join(timeout=1.0)
        self._worker_thread = None
        self._saver_thread = None

    def submit(self, context: InspectionContext) -> bool:
        """Enqueues frame for inspection. Returns False if queue is full."""
        try:
            self._task_queue.put_nowait(context)
            return True
        except queue.Full:
            logger.warning(f"Slot {self.slot_index} queue is full! Dropping frame.")
            return False

    def register_callback(self, callback: Callable[[ContinuousInspectionResult], None]) -> None:
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unregister_callback(self, callback: Callable[[ContinuousInspectionResult], None]) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _run_inspection_loop(self) -> None:
        while self._is_running:
            try:
                ctx = self._task_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            if ctx is None:
                break

            try:
                result = self._process_fn(ctx)
                ctx.result = result

                # Trigger callbacks
                for cb in self._callbacks:
                    try:
                        cb(result)
                    except Exception as e:
                        logger.error(f"Error in slot {self.slot_index} callback: {e}")

                # Queue async image save if enabled
                if self.save_raw_enabled and ctx.image is not None:
                    timestamp_str = datetime.fromtimestamp(ctx.timestamp).strftime(
                        "%Y%m%d_%H%M%S_%f"
                    )
                    filename = f"slot{self.slot_index}_{timestamp_str}_{result.summary}.png"
                    filepath = self.save_directory / filename
                    try:
                        self._save_queue.put_nowait((filepath, ctx.image))
                    except queue.Full:
                        logger.warning(f"Slot {self.slot_index} save queue full, skipping save.")

            except Exception as ex:
                logger.error(f"Unhandled exception in slot {self.slot_index} worker: {ex}")
            finally:
                self._task_queue.task_done()

    def _run_saver_loop(self) -> None:
        while self._is_running:
            try:
                item = self._save_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            if item is None:
                break

            filepath, img = item
            try:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(filepath), img)
            except Exception as e:
                logger.error(f"Failed to write image {filepath}: {e}")
            finally:
                self._save_queue.task_done()
