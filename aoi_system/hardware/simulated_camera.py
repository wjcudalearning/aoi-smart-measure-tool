import threading
import time
from pathlib import Path

import cv2
import numpy as np

from aoi_system.hardware.camera_base import CameraDevice


class SimulatedCamera(CameraDevice):
    """Simulated camera generating synthetic test patterns or cycling through local disk images."""

    def __init__(
        self,
        device_id: str = "SIM_CAM",
        name: str = "Simulated AOI Camera",
        width: int = 640,
        height: int = 480,
        fps: float = 30.0,
        image_folder: Path | str | None = None,
    ) -> None:
        super().__init__(device_id=device_id, name=name)
        self.width = width
        self.height = height
        self.fps = fps
        self.image_folder = Path(image_folder) if image_folder else None
        self._image_files: list[Path] = []
        self._current_img_idx: int = 0
        self._grab_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._frame_count: int = 0

        if self.image_folder and self.image_folder.is_dir():
            for ext in ("*.png", "*.bmp", "*.jpg", "*.jpeg", "*.tif", "*.tiff"):
                self._image_files.extend(self.image_folder.glob(ext))
            self._image_files.sort()

    def connect(self) -> bool:
        self._is_connected = True
        return True

    def disconnect(self) -> None:
        if self._is_grabbing:
            self.stop_grabbing()
        self._is_connected = False

    def _generate_synthetic_frame(self) -> np.ndarray:
        frame = np.zeros((self.height, self.width), dtype=np.uint8)
        # Draw a synthetic rectangular target
        pad_x = min(20, self.width // 4)
        pad_y = min(20, self.height // 4)
        w_rect = min(80, max(10, self.width - 2 * pad_x))
        h_rect = min(60, max(10, self.height - 2 * pad_y))
        frame[pad_y : pad_y + h_rect, pad_x : pad_x + w_rect] = 255
        return frame

    def grab_frame(self) -> np.ndarray | None:
        if not self._is_connected:
            return None

        self._frame_count += 1
        if self._image_files:
            file_path = self._image_files[self._current_img_idx % len(self._image_files)]
            self._current_img_idx += 1
            img = cv2.imread(str(file_path), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                if img.shape[0] != self.height or img.shape[1] != self.width:
                    img = cv2.resize(img, (self.width, self.height))
                return img

        return self._generate_synthetic_frame()

    def start_grabbing(self) -> bool:
        if not self._is_connected or self._is_grabbing:
            return False

        self._stop_event.clear()
        self._is_grabbing = True
        self._grab_thread = threading.Thread(target=self._grab_loop, daemon=True)
        self._grab_thread.start()
        return True

    def stop_grabbing(self) -> None:
        if not self._is_grabbing:
            return

        self._stop_event.set()
        if self._grab_thread and self._grab_thread.is_alive():
            self._grab_thread.join(timeout=1.0)
        self._grab_thread = None
        self._is_grabbing = False

    def _grab_loop(self) -> None:
        interval = 1.0 / max(1.0, self.fps)
        while not self._stop_event.is_set():
            t0 = time.perf_counter()
            frame = self.grab_frame()
            if frame is not None:
                self._notify_frame(frame)
            elapsed = time.perf_counter() - t0
            sleep_time = interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
