from abc import abstractmethod
from enum import StrEnum
from typing import Any

from aoi_system.hardware.camera_base import CameraDevice


class CameraTriggerMode(StrEnum):
    CONTINUOUS = "Continuous"
    SOFTWARE = "Software"
    HARDWARE_LINE1 = "HardwareLine1"


class IndustrialCameraSDKBase(CameraDevice):
    """Base interface for industrial vision SDK integration (e.g. Basler Pylon, Hikrobot MVS)."""

    def __init__(
        self,
        device_id: str,
        name: str = "Industrial Vision Camera",
        ip_or_serial: str = "",
    ) -> None:
        super().__init__(device_id=device_id, name=name)
        self.ip_or_serial = ip_or_serial
        self.exposure_time_us: float = 10000.0
        self.gain_db: float = 0.0
        self.trigger_mode: CameraTriggerMode = CameraTriggerMode.CONTINUOUS

    @abstractmethod
    def set_exposure_time(self, microseconds: float) -> bool:
        """Sets sensor exposure duration in microseconds."""
        raise NotImplementedError

    @abstractmethod
    def set_gain(self, gain_db: float) -> bool:
        """Sets analog/digital gain in dB."""
        raise NotImplementedError

    @abstractmethod
    def set_trigger_mode(self, mode: CameraTriggerMode) -> bool:
        """Configures acquisition trigger source."""
        raise NotImplementedError

    @classmethod
    def enumerate_devices(cls) -> list[dict[str, Any]]:
        """Scans network and USB buses to detect connected industrial cameras."""
        return []
