from unittest.mock import MagicMock, patch

import numpy as np

from aoi_system.hardware.basler_camera import BaslerCameraDriver
from aoi_system.hardware.hikrobot_camera import HikrobotCameraDriver
from aoi_system.hardware.industrial_camera import CameraTriggerMode
from aoi_system.hardware.opencv_camera import OpenCvCameraDriver
from aoi_system.hardware.simulated_camera import SimulatedCamera


class TestCameraDrivers:
    def test_simulated_camera_lifecycle(self, tmp_path) -> None:
        cam = SimulatedCamera(device_id="SIM_0", width=120, height=80, fps=60.0)
        assert not cam.is_connected
        assert cam.connect() is True
        assert cam.is_connected is True

        frame = cam.grab_frame()
        assert frame is not None
        assert frame.shape == (80, 120)

        # Frame callback in continuous grabbing
        received = []
        cam.register_frame_callback(lambda f: received.append(f))
        assert cam.start_grabbing() is True
        assert cam.is_grabbing is True
        import time

        time.sleep(0.08)
        cam.stop_grabbing()
        assert cam.is_grabbing is False
        assert len(received) > 0

        cam.disconnect()
        assert not cam.is_connected

    def test_opencv_camera_driver_with_mock(self) -> None:
        with patch("cv2.VideoCapture") as mock_cap_cls:
            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = True
            mock_frame = np.ones((100, 100, 3), dtype=np.uint8) * 120
            mock_cap.read.return_value = (True, mock_frame)
            mock_cap_cls.return_value = mock_cap

            driver = OpenCvCameraDriver(device_index=0)
            assert driver.connect() is True
            assert driver.is_connected is True

            frame = driver.grab_frame()
            assert frame is not None
            assert frame.shape == (100, 100, 3)

            driver.set_resolution(1280, 720)
            driver.set_fps(30.0)

            # Continuous grabbing
            frames = []
            driver.register_frame_callback(lambda f: frames.append(f))
            assert driver.start_grabbing() is True
            import time

            time.sleep(0.06)
            driver.stop_grabbing()
            assert len(frames) > 0

            driver.disconnect()
            assert driver.is_connected is False

    def test_opencv_camera_driver_failed_open(self) -> None:
        with patch("cv2.VideoCapture") as mock_cap_cls:
            mock_cap = MagicMock()
            mock_cap.isOpened.return_value = False
            mock_cap_cls.return_value = mock_cap

            driver = OpenCvCameraDriver(device_index=999)
            assert driver.connect() is False
            assert driver.grab_frame() is None

    def test_hikrobot_camera_driver_fallback_and_params(self) -> None:
        driver = HikrobotCameraDriver(device_id="HIK_01", ip_or_serial="192.168.1.10")
        assert driver.name == "Hikrobot MVS Camera"
        # SDK might not be installed in test environment, so fallback is supported
        driver.set_exposure_time(15000.0)
        assert driver.exposure_time_us == 15000.0
        driver.set_gain(6.0)
        assert driver.gain_db == 6.0
        driver.set_trigger_mode(CameraTriggerMode.SOFTWARE)
        assert driver.trigger_mode == CameraTriggerMode.SOFTWARE

        devices = HikrobotCameraDriver.enumerate_devices()
        assert isinstance(devices, list)

        # Connection and grabbing in simulated/mock mode
        assert driver.connect() is True
        f = driver.grab_frame()
        assert f is not None
        driver.disconnect()

    def test_basler_camera_driver_fallback_and_params(self) -> None:
        driver = BaslerCameraDriver(device_id="BASLER_01", ip_or_serial="23456789")
        assert driver.name == "Basler Pylon Camera"
        driver.set_exposure_time(8000.0)
        assert driver.exposure_time_us == 8000.0
        driver.set_gain(3.5)
        assert driver.gain_db == 3.5
        driver.set_trigger_mode(CameraTriggerMode.HARDWARE_LINE1)
        assert driver.trigger_mode == CameraTriggerMode.HARDWARE_LINE1

        devices = BaslerCameraDriver.enumerate_devices()
        assert isinstance(devices, list)

        assert driver.connect() is True
        f = driver.grab_frame()
        assert f is not None
        driver.disconnect()
