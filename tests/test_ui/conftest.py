import os

import pytest
from PySide6.QtWidgets import QApplication

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    """Initializes a shared QApplication instance for UI test runs in headless offscreen mode."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
