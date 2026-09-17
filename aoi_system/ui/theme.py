"""Modern Industrial Dark Theme and Palette for AOI Vision System."""

COLOR_BG_DARK = "#18181b"
COLOR_BG_PANEL = "#242427"
COLOR_BG_CARD = "#2d2d30"
COLOR_BORDER = "#3f3f46"
COLOR_TEXT_PRIMARY = "#f4f4f5"
COLOR_TEXT_SECONDARY = "#a1a1aa"
COLOR_ACCENT = "#0284c7"
COLOR_ACCENT_HOVER = "#0369a1"

# Industrial Inspection Judgement Colors
COLOR_GRADE_A = "#16a34a"  # Green
COLOR_GRADE_B = "#d97706"  # Amber / Orange
COLOR_GRADE_NG = "#dc2626"  # Red
COLOR_GRADE_READY = "#71717a"  # Gray

DARK_INDUSTRIAL_QSS = f"""
QMainWindow, QWidget {{
    background-color: {COLOR_BG_DARK};
    color: {COLOR_TEXT_PRIMARY};
    font-family: 'Segoe UI', 'Microsoft JhengHei', sans-serif;
    font-size: 10pt;
}}

QFrame#cardPanel {{
    background-color: {COLOR_BG_CARD};
    border: 1px solid {COLOR_BORDER};
    border-radius: 8px;
    padding: 8px;
}}

QPushButton {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {COLOR_BORDER};
    border-color: {COLOR_ACCENT};
}}

QPushButton:pressed {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
}}

QPushButton#primaryButton {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
    border: none;
}}

QPushButton#primaryButton:hover {{
    background-color: {COLOR_ACCENT_HOVER};
}}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    border: 1px solid {COLOR_BORDER};
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: {COLOR_ACCENT};
}}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {COLOR_ACCENT};
}}

QTableWidget {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_PRIMARY};
    gridline-color: {COLOR_BORDER};
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
}}

QTableWidget::item:selected {{
    background-color: {COLOR_ACCENT};
    color: #ffffff;
}}

QHeaderView::section {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_SECONDARY};
    padding: 6px;
    border: 1px solid {COLOR_BORDER};
    font-weight: bold;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: {COLOR_BORDER};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: {COLOR_ACCENT};
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #ffffff;
    border: 2px solid {COLOR_ACCENT};
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}}

QTabWidget::pane {{
    border: 1px solid {COLOR_BORDER};
    background-color: {COLOR_BG_CARD};
    border-radius: 6px;
}}

QTabBar::tab {{
    background-color: {COLOR_BG_PANEL};
    color: {COLOR_TEXT_SECONDARY};
    padding: 8px 16px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {COLOR_BG_CARD};
    color: {COLOR_TEXT_PRIMARY};
    border-bottom: 2px solid {COLOR_ACCENT};
}}

QScrollBar:vertical {{
    background: {COLOR_BG_PANEL};
    width: 8px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical {{
    background: {COLOR_BORDER};
    min-height: 20px;
    border-radius: 4px;
}}

QScrollBar::handle:vertical:hover {{
    background: {COLOR_ACCENT};
}}
"""
