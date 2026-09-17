import socket
import struct

from loguru import logger


class ModbusTcpClient:
    """Industrial Modbus TCP client for PLC interaction (triggers and inspection results)."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 502,
        timeout: float = 2.0,
        unit_id: int = 1,
        simulation_mode: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.unit_id = unit_id
        self.simulation_mode = simulation_mode
        self._socket: socket.socket | None = None
        self._is_connected = False
        self._transaction_id = 0

        # In simulation mode, maintain virtual registers and coils
        self._sim_coils: dict[int, bool] = {}
        self._sim_registers: dict[int, int] = {}

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def connect(self) -> bool:
        if self._is_connected:
            return True

        if self.simulation_mode:
            self._is_connected = True
            logger.info(
                f"Modbus TCP client connected in simulation mode to {self.host}:{self.port}"
            )
            return True

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(self.timeout)
            self._socket.connect((self.host, self.port))
            self._is_connected = True
            logger.info(f"Modbus TCP client connected to PLC at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.warning(
                f"Cannot connect to Modbus PLC at {self.host}:{self.port}: {e}. Fallback to sim."
            )
            self._is_connected = True
            self.simulation_mode = True
            return True

    def disconnect(self) -> None:
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self._is_connected = False
        logger.info("Modbus TCP client disconnected.")

    def read_coil(self, address: int) -> bool:
        if not self._is_connected:
            return False

        if self.simulation_mode or self._socket is None:
            return self._sim_coils.get(address, False)

        try:
            self._transaction_id = (self._transaction_id + 1) & 0xFFFF
            # Function code 0x01: Read Coils (1 coil)
            pdu = struct.pack(">BHH", 0x01, address, 1)
            header = struct.pack(">HHHB", self._transaction_id, 0, len(pdu) + 1, self.unit_id)
            self._socket.sendall(header + pdu)

            resp = self._socket.recv(1024)
            if len(resp) >= 10 and resp[7] == 0x01:
                byte_val = resp[9]
                return bool(byte_val & 0x01)
            return False
        except Exception as e:
            logger.error(f"Modbus read_coil error at address {address}: {e}")
            return False

    def write_coil(self, address: int, value: bool) -> bool:
        if not self._is_connected:
            return False

        if self.simulation_mode or self._socket is None:
            self._sim_coils[address] = value
            return True

        try:
            self._transaction_id = (self._transaction_id + 1) & 0xFFFF
            coil_val = 0xFF00 if value else 0x0000
            # Function code 0x05: Write Single Coil
            pdu = struct.pack(">BHH", 0x05, address, coil_val)
            header = struct.pack(">HHHB", self._transaction_id, 0, len(pdu) + 1, self.unit_id)
            self._socket.sendall(header + pdu)

            resp = self._socket.recv(1024)
            return len(resp) >= 12 and resp[7] == 0x05
        except Exception as e:
            logger.error(f"Modbus write_coil error at address {address}: {e}")
            return False

    def read_holding_registers(self, address: int, count: int = 1) -> list[int]:
        if not self._is_connected:
            return []

        if self.simulation_mode or self._socket is None:
            return [self._sim_registers.get(address + i, 0) for i in range(count)]

        try:
            self._transaction_id = (self._transaction_id + 1) & 0xFFFF
            # Function code 0x03: Read Holding Registers
            pdu = struct.pack(">BHH", 0x03, address, count)
            header = struct.pack(">HHHB", self._transaction_id, 0, len(pdu) + 1, self.unit_id)
            self._socket.sendall(header + pdu)

            resp = self._socket.recv(1024)
            if len(resp) >= 9 and resp[7] == 0x03:
                byte_count = resp[8]
                values = []
                for i in range(0, byte_count, 2):
                    val = struct.unpack(">H", resp[9 + i : 11 + i])[0]
                    values.append(val)
                return values
            return []
        except Exception as e:
            logger.error(f"Modbus read_holding_registers error at address {address}: {e}")
            return []

    def write_holding_registers(self, address: int, values: list[int]) -> bool:
        if not self._is_connected:
            return False

        if self.simulation_mode or self._socket is None:
            for i, val in enumerate(values):
                self._sim_registers[address + i] = val & 0xFFFF
            return True

        try:
            self._transaction_id = (self._transaction_id + 1) & 0xFFFF
            count = len(values)
            byte_count = count * 2
            # Function code 0x10: Write Multiple Registers
            pdu_header = struct.pack(">BHHB", 0x10, address, count, byte_count)
            pdu_data = bytearray()
            for v in values:
                pdu_data.extend(struct.pack(">H", v & 0xFFFF))
            pdu = pdu_header + pdu_data
            header = struct.pack(">HHHB", self._transaction_id, 0, len(pdu) + 1, self.unit_id)
            self._socket.sendall(header + pdu)

            resp = self._socket.recv(1024)
            return len(resp) >= 12 and resp[7] == 0x10
        except Exception as e:
            logger.error(f"Modbus write_holding_registers error at address {address}: {e}")
            return False

    def publish_inspection_result(self, slot_index: int, grade: str, count: int) -> bool:
        grade_code_map = {"A": 1, "B": 2, "NG": 3}
        code = grade_code_map.get(grade.upper(), 3)
        base_address = 100 + slot_index * 10
        return self.write_holding_registers(base_address, [code, count])
