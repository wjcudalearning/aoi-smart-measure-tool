import socket
import struct
import time
from unittest.mock import MagicMock, patch

from aoi_system.communication.modbus_client import ModbusTcpClient
from aoi_system.communication.tcp_socket import TcpSocketServer
from aoi_system.communication.trigger_dispatcher import TriggerDispatcher, TriggerSource


class TestIndustrialCommunication:
    def test_modbus_client_simulation(self) -> None:
        client = ModbusTcpClient(host="127.0.0.1", port=502, simulation_mode=True)
        assert client.connect() is True
        assert client.is_connected is True

        # Write & Read coils
        assert client.write_coil(0, True) is True
        assert client.read_coil(0) is True
        assert client.write_coil(0, False) is True
        assert client.read_coil(0) is False

        # Write & Read holding registers
        assert client.write_holding_registers(100, [1, 25, 300]) is True
        regs = client.read_holding_registers(100, 3)
        assert regs == [1, 25, 300]

        # Publish inspection result helper
        assert client.publish_inspection_result(slot_index=0, grade="A", count=42) is True
        assert client.publish_inspection_result(slot_index=1, grade="B", count=10) is True
        assert client.publish_inspection_result(slot_index=2, grade="NG", count=5) is True
        regs = client.read_holding_registers(100, 3)
        assert regs[0] == 1  # 1 for 'A'
        assert regs[1] == 42  # count

        client.disconnect()
        assert client.is_connected is False

    def test_modbus_client_real_socket_mock(self) -> None:
        with patch("socket.socket") as mock_sock_cls:
            mock_sock = MagicMock()
            mock_sock_cls.return_value = mock_sock

            # Fake response for read_coil:
            # transaction_id(2), proto(2), len(2), unit(1), func(1), byte_count(1), val(1)
            fake_read_coil_resp = struct.pack(">HHHBBBB", 1, 0, 4, 1, 1, 1, 0x01)
            # Fake response for write_coil
            fake_write_coil_resp = struct.pack(">HHHBBHH", 1, 0, 6, 1, 5, 0, 0xFF00)
            # Fake response for read_holding_registers
            fake_read_regs_resp = struct.pack(">HHHBBBHH", 1, 0, 7, 1, 3, 4, 1234, 5678)
            # Fake response for write_holding_registers
            fake_write_regs_resp = struct.pack(">HHHBBHH", 1, 0, 6, 1, 16, 100, 2)

            mock_sock.recv.side_effect = [
                fake_read_coil_resp,
                fake_write_coil_resp,
                fake_read_regs_resp,
                fake_write_regs_resp,
            ]

            client = ModbusTcpClient(host="192.168.1.50", port=502, simulation_mode=False)
            assert client.connect() is True
            assert client.read_coil(0) is True
            assert client.write_coil(0, True) is True
            assert client.read_holding_registers(100, 2) == [1234, 5678]
            assert client.write_holding_registers(100, [1234, 5678]) is True

            client.disconnect()

    def test_tcp_socket_server_commands(self) -> None:
        trigger_called = []
        server = TcpSocketServer(
            host="127.0.0.1",
            port=0,
            trigger_handler=lambda slot: trigger_called.append(slot) or True,
        )
        assert server.start() is True
        port = server.port
        assert port > 0

        # Connect client socket
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(2.0)
        client.connect(("127.0.0.1", port))

        # Send PING
        client.sendall(b"PING\n")
        resp = client.recv(1024).decode("utf-8").strip()
        assert resp == "PONG"

        # Send STATUS
        client.sendall(b"STATUS\n")
        resp = client.recv(1024).decode("utf-8").strip()
        assert "READY" in resp

        # Send TRIGGER
        client.sendall(b"TRIGGER 1\n")
        resp = client.recv(1024).decode("utf-8").strip()
        assert "ACK_TRIGGER 1 OK" in resp
        assert 1 in trigger_called

        # Set & Query RESULT?
        server.set_slot_result(1, "GRADE_A")
        client.sendall(b"RESULT? 1\n")
        resp = client.recv(1024).decode("utf-8").strip()
        assert "RESULT 1 GRADE=GRADE_A" in resp

        # Unknown command
        client.sendall(b"INVALID_CMD\n")
        resp = client.recv(1024).decode("utf-8").strip()
        assert "ERR UNKNOWN_COMMAND" in resp

        client.close()
        server.stop()

    def test_trigger_dispatcher(self) -> None:
        mock_modbus = MagicMock(spec=ModbusTcpClient)
        states = [False, True, True, True, True, True, True]
        mock_modbus.read_coil.side_effect = lambda addr: states.pop(0) if states else False

        dispatcher = TriggerDispatcher(modbus_client=mock_modbus)
        triggered_slots: list[tuple[int, TriggerSource]] = []

        def handle_slot(src: TriggerSource) -> None:
            triggered_slots.append((0, src))

        dispatcher.register_slot_trigger_callback(slot_index=0, callback=handle_slot)

        # Software trigger
        assert dispatcher.fire_trigger(slot_index=0, source=TriggerSource.SOFTWARE) is True
        assert len(triggered_slots) == 1
        assert triggered_slots[0] == (0, TriggerSource.SOFTWARE)

        # Start PLC Polling (rising edge will fire)
        dispatcher.start_plc_polling(slot_coil_map={0: 10}, poll_interval_sec=0.01)
        time.sleep(0.06)
        dispatcher.stop_plc_polling()

        assert any(t[1] == TriggerSource.PLC_MODBUS for t in triggered_slots)

        # Unregister callback
        dispatcher.unregister_slot_trigger_callback(0, handle_slot)
        assert dispatcher.fire_trigger(slot_index=0, source=TriggerSource.SOFTWARE) is False
