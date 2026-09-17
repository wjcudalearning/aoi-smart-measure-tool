import threading
import time
from collections.abc import Callable
from enum import StrEnum

from loguru import logger

from aoi_system.communication.modbus_client import ModbusTcpClient


class TriggerSource(StrEnum):
    SOFTWARE = "Software"
    HARDWARE_IO = "Hardware_IO"
    PLC_MODBUS = "PLC_Modbus"
    TCP_SOCKET = "TCP_Socket"


class TriggerDispatcher:
    """Coordinates inspection triggers from software, hardware IO, PLC, and TCP socket."""

    def __init__(self, modbus_client: ModbusTcpClient | None = None) -> None:
        self.modbus_client = modbus_client
        self._slot_callbacks: dict[int, list[Callable[[TriggerSource], None]]] = {}
        self._is_polling_plc = False
        self._plc_poll_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._last_coil_states: dict[int, bool] = {}

    def register_slot_trigger_callback(
        self, slot_index: int, callback: Callable[[TriggerSource], None]
    ) -> None:
        if slot_index not in self._slot_callbacks:
            self._slot_callbacks[slot_index] = []
        if callback not in self._slot_callbacks[slot_index]:
            self._slot_callbacks[slot_index].append(callback)

    def unregister_slot_trigger_callback(
        self, slot_index: int, callback: Callable[[TriggerSource], None]
    ) -> None:
        if slot_index in self._slot_callbacks and callback in self._slot_callbacks[slot_index]:
            self._slot_callbacks[slot_index].remove(callback)

    def fire_trigger(self, slot_index: int, source: TriggerSource) -> bool:
        cbs = self._slot_callbacks.get(slot_index, [])
        if not cbs:
            logger.warning(f"No triggers registered for slot {slot_index}")
            return False

        logger.info(f"Firing inspection trigger on slot {slot_index} from source {source.value}")
        for cb in cbs:
            try:
                cb(source)
            except Exception as e:
                logger.error(f"Error executing slot {slot_index} trigger callback: {e}")
        return True

    def start_plc_polling(
        self, slot_coil_map: dict[int, int], poll_interval_sec: float = 0.02
    ) -> None:
        if self._is_polling_plc or not self.modbus_client:
            return

        self._is_polling_plc = True
        self._stop_event.clear()
        self._plc_poll_thread = threading.Thread(
            target=self._plc_poll_worker, args=(slot_coil_map, poll_interval_sec), daemon=True
        )
        self._plc_poll_thread.start()
        logger.info("PLC Modbus trigger polling started.")

    def stop_plc_polling(self) -> None:
        if not self._is_polling_plc:
            return

        self._stop_event.set()
        if self._plc_poll_thread and self._plc_poll_thread.is_alive():
            self._plc_poll_thread.join(timeout=1.0)
        self._is_polling_plc = False
        logger.info("PLC Modbus trigger polling stopped.")

    def _plc_poll_worker(self, slot_coil_map: dict[int, int], poll_interval: float) -> None:
        assert self.modbus_client is not None
        while not self._stop_event.is_set():
            for slot, coil_addr in slot_coil_map.items():
                current_state = self.modbus_client.read_coil(coil_addr)
                last_state = self._last_coil_states.get(coil_addr, False)

                # Rising edge detection
                if current_state and not last_state:
                    self.fire_trigger(slot, TriggerSource.PLC_MODBUS)

                self._last_coil_states[coil_addr] = current_state
            time.sleep(poll_interval)
