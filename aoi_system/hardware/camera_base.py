from abc import ABC, abstractmethod
from collections.abc import Callable

import numpy as np


class CameraDevice(ABC):
    """Abstract Base Class defining the hardware abstraction layer for industrial cameras."""

    def __init__(self, device_id: str = "CAM_0", name: str = "Industrial Camera") -> None:
        self.device_id = device_id
        self.name = name
        self._is_connected: bool = False
        self._is_grabbing: bool = False
        self._frame_callbacks: list[Callable[[np.ndarray], None]] = []

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    @property
    def is_grabbing(self) -> bool:
        return self._is_grabbing

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to camera device."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Closes connection to camera device."""
        raise NotImplementedError

    @abstractmethod
    def grab_frame(self) -> np.ndarray | None:
        """Synchronously captures a single frame from the camera."""
        raise NotImplementedError

    @abstractmethod
    def start_grabbing(self) -> bool:
        """Starts continuous asynchronous frame acquisition in background thread."""
        raise NotImplementedError

    @abstractmethod
    def stop_grabbing(self) -> None:
        """Stops continuous acquisition."""
        raise NotImplementedError

    def register_frame_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        """Registers a callback invoked when a new frame is captured in continuous mode."""
        if callback not in self._frame_callbacks:
            self._frame_callbacks.append(callback)

    def unregister_frame_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        """Unregisters an acquisition callback."""
        if callback in self._frame_callbacks:
            self._frame_callbacks.remove(callback)

    def _notify_frame(self, frame: np.ndarray) -> None:
        """Notifies registered listeners with zero-copy or copied frame."""
        for cb in self._frame_callbacks:
            try:
                cb(frame)
            except Exception:
                pass
