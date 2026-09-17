import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from aoi_system.core.logger import setup_logging
from aoi_system.ui.main_window import MainWindow


def main() -> None:
    # Setup centralized asynchronous loguru logging
    setup_logging()

    # Enable High DPI Scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("AOI Smart Measure Tool")
    app.setOrganizationName("AOI Vision AI")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
