from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from aoi_system.communication.modbus_client import ModbusTcpClient
from aoi_system.communication.tcp_socket import TcpSocketServer
from aoi_system.communication.trigger_dispatcher import TriggerDispatcher, TriggerSource


class CommunicationView(QWidget):
    """Industrial communication settings, I/O trigger dispatcher, and protocol activity monitor."""

    def __init__(
        self,
        trigger_dispatcher: TriggerDispatcher | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.dispatcher = trigger_dispatcher or TriggerDispatcher()
        self.modbus_client = ModbusTcpClient(simulation_mode=True)
        self.socket_server = TcpSocketServer(port=8888)

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Left Column: Configuration Panels
        left_column = QVBoxLayout()
        left_column.setSpacing(12)

        # 1. Modbus TCP Panel
        grp_modbus = QGroupBox("🏭 Modbus TCP 客戶端 (PLC 通訊)")
        modbus_layout = QGridLayout(grp_modbus)
        modbus_layout.addWidget(QLabel("PLC 主機 IP:"), 0, 0)
        self.edit_modbus_ip = QLineEdit("127.0.0.1")
        modbus_layout.addWidget(self.edit_modbus_ip, 0, 1)

        modbus_layout.addWidget(QLabel("端口 (Port):"), 1, 0)
        self.edit_modbus_port = QLineEdit("502")
        modbus_layout.addWidget(self.edit_modbus_port, 1, 1)

        self.btn_modbus_connect = QPushButton("連線 PLC")
        self.btn_modbus_connect.clicked.connect(self._on_toggle_modbus)
        self.lbl_modbus_status = QLabel("狀態: 未連線")
        self.lbl_modbus_status.setStyleSheet("color: #ef4444; font-weight: bold;")
        modbus_layout.addWidget(self.btn_modbus_connect, 2, 0)
        modbus_layout.addWidget(self.lbl_modbus_status, 2, 1)

        left_column.addWidget(grp_modbus)

        # 2. TCP Socket Server Panel
        grp_socket = QGroupBox("🤖 產線機械手臂通訊 (TCP/IP ASCII Server)")
        socket_layout = QGridLayout(grp_socket)
        socket_layout.addWidget(QLabel("監聽端口:"), 0, 0)
        self.edit_socket_port = QLineEdit("8888")
        socket_layout.addWidget(self.edit_socket_port, 0, 1)

        self.btn_socket_start = QPushButton("啟動服務端")
        self.btn_socket_start.clicked.connect(self._on_toggle_socket)
        self.lbl_socket_status = QLabel("狀態: 停止")
        self.lbl_socket_status.setStyleSheet("color: #ef4444; font-weight: bold;")
        socket_layout.addWidget(self.btn_socket_start, 1, 0)
        socket_layout.addWidget(self.lbl_socket_status, 1, 1)

        left_column.addWidget(grp_socket)

        # 3. Manual Trigger Simulation
        grp_trigger = QGroupBox("⚡ 檢測觸發排程測試 (Trigger Dispatcher)")
        trig_layout = QHBoxLayout(grp_trigger)

        btn_trig_0 = QPushButton("觸發 Slot 0")
        btn_trig_0.setObjectName("primaryButton")
        btn_trig_0.clicked.connect(lambda: self._fire_trigger(0))

        btn_trig_1 = QPushButton("觸發 Slot 1")
        btn_trig_1.setObjectName("primaryButton")
        btn_trig_1.clicked.connect(lambda: self._fire_trigger(1))

        btn_trig_2 = QPushButton("觸發 Slot 2")
        btn_trig_2.setObjectName("primaryButton")
        btn_trig_2.clicked.connect(lambda: self._fire_trigger(2))

        trig_layout.addWidget(btn_trig_0)
        trig_layout.addWidget(btn_trig_1)
        trig_layout.addWidget(btn_trig_2)

        left_column.addWidget(grp_trigger)
        left_column.addStretch()

        layout.addLayout(left_column, stretch=1)

        # Right Column: Live Comm Log Console
        right_panel = QFrame()
        right_panel.setObjectName("cardPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.addWidget(QLabel("📜 工業通訊即時封包記錄 (Activity Log):"))

        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setStyleSheet(
            "background-color: #0f172a; color: #38bdf8; font-family: monospace; font-size: 11px;"
        )
        right_layout.addWidget(self.log_console)

        btn_clear_log = QPushButton("清除日誌")
        btn_clear_log.clicked.connect(self.log_console.clear)
        right_layout.addWidget(btn_clear_log)

        layout.addWidget(right_panel, stretch=2)

    def _on_toggle_modbus(self) -> None:
        if not self.modbus_client.is_connected:
            self.modbus_client.host = self.edit_modbus_ip.text()
            self.modbus_client.port = int(self.edit_modbus_port.text())
            self.modbus_client.connect()
            self.lbl_modbus_status.setText("狀態: 已連線 (在線)")
            self.lbl_modbus_status.setStyleSheet("color: #10b981; font-weight: bold;")
            self.btn_modbus_connect.setText("斷開 PLC")
            self._log("[Modbus] 連線至 PLC 成功")
        else:
            self.modbus_client.disconnect()
            self.lbl_modbus_status.setText("狀態: 未連線")
            self.lbl_modbus_status.setStyleSheet("color: #ef4444; font-weight: bold;")
            self.btn_modbus_connect.setText("連線 PLC")
            self._log("[Modbus] 斷開 PLC 連線")

    def _on_toggle_socket(self) -> None:
        if not self.socket_server.is_running:
            self.socket_server = TcpSocketServer(port=int(self.edit_socket_port.text()))
            self.socket_server.start()
            self.lbl_socket_status.setText(
                "狀態: 監聽中 (Port " + str(self.socket_server.port) + ")"
            )
            self.lbl_socket_status.setStyleSheet("color: #10b981; font-weight: bold;")
            self.btn_socket_start.setText("停止服務端")
            self._log(f"[TCP Socket] 服務端已在端口 {self.socket_server.port} 啟動")
        else:
            self.socket_server.stop()
            self.lbl_socket_status.setText("狀態: 停止")
            self.lbl_socket_status.setStyleSheet("color: #ef4444; font-weight: bold;")
            self.btn_socket_start.setText("啟動服務端")
            self._log("[TCP Socket] 服務端已停止")

    def _fire_trigger(self, slot: int) -> None:
        self._log(f"[Trigger] 手動發送軟體觸發 -> Slot {slot}")
        self.dispatcher.fire_trigger(slot, TriggerSource.SOFTWARE)

    def _log(self, text: str) -> None:
        self.log_console.append(text)
