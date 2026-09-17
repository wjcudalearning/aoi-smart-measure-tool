from enum import StrEnum
from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class UserRole(StrEnum):
    OPERATOR = "操作員 (Operator)"
    ENGINEER = "工程師 (Engineer)"
    ADMINISTRATOR = "系統管理員 (Admin)"

    @classmethod
    def from_value(cls, val: Any) -> "UserRole":
        if isinstance(val, cls):
            return val
        if val is None:
            return cls.OPERATOR
        val_str = str(val).strip()
        for item in cls:
            if item.value == val_str or item.name == val_str:
                return item
        # Fallback partial match
        if "admin" in val_str.lower() or "管理員" in val_str:
            return cls.ADMINISTRATOR
        if "engineer" in val_str.lower() or "工程師" in val_str:
            return cls.ENGINEER
        return cls.OPERATOR


class RoleSwitchDialog(QDialog):
    """Security dialog for switching between Operator, Engineer, and Admin roles."""

    PASSWORDS: dict[UserRole, str] = {
        UserRole.OPERATOR: "",
        UserRole.ENGINEER: "1234",
        UserRole.ADMINISTRATOR: "8888",
    }

    def __init__(
        self, current_role: UserRole | str = UserRole.OPERATOR, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("切換操作權限 (Role Switcher)")
        self.setFixedSize(320, 200)
        self.selected_role: UserRole = UserRole.from_value(current_role)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        role_layout = QHBoxLayout()
        role_label = QLabel("選擇身分:")
        self.combo = QComboBox()
        for role in UserRole:
            self.combo.addItem(role.value, role.value)
        self.combo.setCurrentText(self.selected_role.value)
        role_layout.addWidget(role_label)
        role_layout.addWidget(self.combo)
        layout.addLayout(role_layout)

        self.pwd_label = QLabel("輸入驗證密碼:")
        self.pwd_input = QLineEdit()
        self.pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_input.setPlaceholderText("請輸入密碼 (預設: 1234 / 8888)")
        layout.addWidget(self.pwd_label)
        layout.addWidget(self.pwd_input)

        self.combo.currentIndexChanged.connect(self._on_role_changed)
        self._on_role_changed()

        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("確認切換")
        btn_ok.setObjectName("primaryButton")
        btn_ok.clicked.connect(self._validate_and_accept)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def _on_role_changed(self) -> None:
        role = UserRole.from_value(self.combo.currentText())
        if role == UserRole.OPERATOR:
            self.pwd_input.setEnabled(False)
            self.pwd_input.clear()
        else:
            self.pwd_input.setEnabled(True)

    def _validate_and_accept(self) -> None:
        target_role = UserRole.from_value(self.combo.currentText())
        required_pwd = self.PASSWORDS.get(target_role, "")

        if required_pwd:
            input_pwd = self.pwd_input.text().strip()
            if input_pwd != required_pwd:
                QMessageBox.warning(self, "密碼錯誤", "所輸入的權限密碼不正確！")
                return

        self.selected_role = target_role
        self.accept()
