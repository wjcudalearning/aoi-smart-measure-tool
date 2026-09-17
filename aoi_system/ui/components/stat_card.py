from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class StatCard(QFrame):
    """Industrial numeric KPI and status display card."""

    def __init__(
        self,
        title: str,
        initial_value: str = "0",
        subtitle: str = "",
        accent_color: str = "#0284c7",
    ) -> None:
        super().__init__()
        self.setObjectName("cardPanel")
        self.accent_color = accent_color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "color: #a1a1aa; font-size: 11px; font-weight: 600; text-transform: uppercase;"
        )

        self.value_label = QLabel(initial_value)
        self.value_label.setStyleSheet(
            f"color: {accent_color}; font-size: 22px; font-weight: bold;"
        )
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet("color: #71717a; font-size: 11px;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        if subtitle:
            layout.addWidget(self.subtitle_label)

    def set_value(self, value: str, color: str | None = None) -> None:
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")

    def set_subtitle(self, subtitle: str) -> None:
        self.subtitle_label.setText(subtitle)
