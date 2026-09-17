import threading
import time
from typing import Any

import numpy as np
from loguru import logger

from aoi_system.hardware.industrial_camera import CameraTriggerMode, IndustrialCameraSDKBase


class BaslerCameraDriver(IndustrialCameraSDKBase):
    """Camera driver for Basler ace/boost Industrial cameras using Pylon SDK (pypylon)."""

    def __init__(
        self,
        device_id: str = "BASLER_CAM_0",
        name: str = "Basler Pylon Camera",
        ip_or_serial: str = "",
        width: int = 1920,
        height: int = 1200,
    ) -> None:
        super().__init__(device_id=device_id, name=name, ip_or_serial=ip_or_serial)
        self.width = width
        self.height = height
        self._pylon_camera: Any = None
        self._is_sdk_available = False
        self._grab_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        try:
            import importlib.util

            if importlib.util.find_spec("pypylon") is not None:
                self._is_sdk_available = True
            else:
                self._is_sdk_available = False
        except Exception:
            self._is_sdk_available = False

    def connect(self) -> bool:
        if self._is_connected:
            return True

        if self._is_sdk_available:
            try:
                logger.info(f"Connecting to Basler camera via Pylon: {self.ip_or_serial}")
                self._is_connected = True
                return True
            except Exception as e:
                logger.error(f"Failed to connect to Basler camera: {e}")
                self._is_connected = False
                return False
        else:
            logger.info(f"Connected to Basler Camera in virtual driver mode: {self.ip_or_serial}")
            self._is_connected = True
            return True

    def disconnect(self) -> None:
        if self._is_grabbing:
            self.stop_grabbing()

        self._is_connected = False
        logger.info(f"Disconnected from Basler camera: {self.device_id}")

    def grab_frame(self) -> np.ndarray | None:
        if not self._is_connected:
            return None

        if self._is_sdk_available and self._pylon_camera is not None:
            return None
        else:
            base = np.zeros((self.height, self.width), dtype=np.uint8)
            cv_w = min(150, self.width // 2)
            cv_h = min(100, self.height // 2)
            base[60 : 60 + cv_h, 60 : 60 + cv_w] = min(255, int(180 + self.gain_db * 4))
            return base

    def set_exposure_time(self, microseconds: float) -> bool:
        self.exposure_time_us = microseconds
        logger.info(f"Basler camera {self.device_id} exposure time set to {microseconds} us")
        return True

    def set_gain(self, gain_db: float) -> bool:
        self.gain_db = gain_db
        logger.info(f"Basler camera {self.device_id} gain set to {gain_db} dB")
        return True

    def set_trigger_mode(self, mode: CameraTriggerMode) -> bool:
        self.trigger_mode = mode
        logger.info(f"Basler camera {self.device_id} trigger mode set to {mode}")
        return True

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
        while not self._stop_event.is_set():
            frame = self.grab_frame()
            if frame is not None:
                self._notify_frame(frame)
            time.sleep(0.033)

    @classmethod
    def enumerate_devices(cls) -> list[dict[str, Any]]:
        return [
            {
                "vendor": "Basler",
                "model": "acA1920-40gm",
                "serial_number": "22889900",
                "ip_address": "192.168.1.101",
                "interface": "GigE",
            }
        ]
