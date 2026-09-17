import sys
import threading
import time
from typing import Any

import cv2
import numpy as np
from loguru import logger

from aoi_system.hardware.camera_base import CameraDevice


class OpenCvCameraDriver(CameraDevice):
    """Camera driver for standard USB UVC and DirectShow cameras via OpenCV VideoCapture."""

    def __init__(
        self,
        device_index: int = 0,
        device_id: str = "USB_CAM_0",
        name: str = "OpenCV USB Camera",
        width: int = 1280,
        height: int = 720,
        fps: float = 30.0,
    ) -> None:
        super().__init__(device_id=device_id, name=name)
        self.device_index = device_index
        self.width = width
        self.height = height
        self.fps = fps
        self._cap: Any = None
        self._grab_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def connect(self) -> bool:
        if self._is_connected:
            return True

        backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
        try:
            self._cap = cv2.VideoCapture(self.device_index, backend)
            if not self._cap.isOpened():
                # Fallback to standard backend
                self._cap = cv2.VideoCapture(self.device_index)

            if self._cap.isOpened():
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self._cap.set(cv2.CAP_PROP_FPS, self.fps)
                self._is_connected = True
                logger.info(f"OpenCV Camera (index {self.device_index}) connected.")
                return True
            else:
                logger.warning(f"Failed to open OpenCV camera at index {self.device_index}")
                self._is_connected = False
                return False
        except Exception as e:
            logger.error(f"Error opening OpenCV camera {self.device_index}: {e}")
            self._is_connected = False
            return False

    def disconnect(self) -> None:
        if self._is_grabbing:
            self.stop_grabbing()

        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

        self._is_connected = False
        logger.info(f"OpenCV Camera (index {self.device_index}) disconnected.")

    def grab_frame(self) -> np.ndarray | None:
        if not self._is_connected or self._cap is None:
            return None

        try:
            ret, frame = self._cap.read()
            if ret and frame is not None:
                return np.asarray(frame)
            return None
        except Exception as e:
            logger.error(f"Error grabbing frame from camera {self.device_index}: {e}")
            return None

    def set_resolution(self, width: int, height: int) -> bool:
        self.width = width
        self.height = height
        if self._cap is not None and self._cap.isOpened():
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            return True
        return False

    def set_fps(self, fps: float) -> bool:
        self.fps = fps
        if self._cap is not None and self._cap.isOpened():
            self._cap.set(cv2.CAP_PROP_FPS, fps)
            return True
        return False

    def start_grabbing(self) -> bool:
        if not self._is_connected or self._is_grabbing:
            return False

        self._is_grabbing = True
        self._stop_event.clear()
        self._grab_thread = threading.Thread(target=self._acquisition_worker, daemon=True)
        self._grab_thread.start()
        return True

    def stop_grabbing(self) -> None:
        if not self._is_grabbing:
            return

        self._stop_event.set()
        if self._grab_thread and self._grab_thread.is_alive():
            self._grab_thread.join(timeout=1.0)
        self._is_grabbing = False

    def _acquisition_worker(self) -> None:
        interval = 1.0 / max(1.0, self.fps)
        while not self._stop_event.is_set():
            t0 = time.perf_counter()
            frame = self.grab_frame()
            if frame is not None:
                self._notify_frame(frame)
            elapsed = time.perf_counter() - t0
            sleep_time = max(0.001, interval - elapsed)
            time.sleep(sleep_time)
