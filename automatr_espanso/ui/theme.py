"""PyQt6 theme configuration for automatr-espanso."""

# Dark theme stylesheet
DARK_THEME = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #d4d4d4;
}

QLabel {
    color: #d4d4d4;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 6px;
    selection-background-color: #264f78;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #0078d4;
}

QPushButton {
    background-color: #0e639c;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #1177bb;
}

QPushButton:pressed {
    background-color: #0d5a8c;
}

QPushButton:disabled {
    background-color: #3c3c3c;
    color: #808080;
}

QPushButton#secondary {
    background-color: #3c3c3c;
    color: #d4d4d4;
}

QPushButton#secondary:hover {
    background-color: #4c4c4c;
}

QPushButton#danger {
    background-color: #c42b1c;
}

QPushButton#danger:hover {
    background-color: #d43b2c;
}

QListWidget {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    outline: none;
}

QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #2d2d2d;
}

QListWidget::item:selected {
    background-color: #094771;
    color: #ffffff;
}

QListWidget::item:hover {
    background-color: #2a2d2e;
}

QTreeWidget {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    outline: none;
}

QTreeWidget::item {
    padding: 4px;
}

QTreeWidget::item:selected {
    background-color: #094771;
    color: #ffffff;
}

QTreeWidget::item:hover {
    background-color: #2a2d2e;
}

QSplitter::handle {
    background-color: #3c3c3c;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #5a5a5a;
    border-radius: 4px;
    min-height: 20px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #6a6a6a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #1e1e1e;
    height: 12px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #5a5a5a;
    border-radius: 4px;
    min-width: 20px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #6a6a6a;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QMenuBar {
    background-color: #252526;
    color: #d4d4d4;
    border-bottom: 1px solid #3c3c3c;
}

QMenuBar::item:selected {
    background-color: #3c3c3c;
}

QMenu {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
}

QMenu::item:selected {
    background-color: #094771;
}

QStatusBar {
    background-color: #007acc;
    color: #ffffff;
}

QGroupBox {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #d4d4d4;
}

QTabWidget::pane {
    border: 1px solid #3c3c3c;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #2d2d2d;
    color: #d4d4d4;
    padding: 8px 16px;
    border: 1px solid #3c3c3c;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #1e1e1e;
    border-bottom: 2px solid #0078d4;
}

QTabBar::tab:hover:!selected {
    background-color: #3c3c3c;
}

QComboBox {
    background-color: #2d2d2d;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 6px;
    min-width: 100px;
}

QComboBox:hover {
    border: 1px solid #0078d4;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    selection-background-color: #094771;
}

QCheckBox {
    color: #d4d4d4;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3c3c3c;
    border-radius: 3px;
    background-color: #2d2d2d;
}

QCheckBox::indicator:checked {
    background-color: #0078d4;
    border-color: #0078d4;
}

QToolTip {
    background-color: #252526;
    color: #d4d4d4;
    border: 1px solid #3c3c3c;
    padding: 4px;
}
"""

# Light theme (for future use)
LIGHT_THEME = """
QMainWindow, QWidget {
    background-color: #ffffff;
    color: #1e1e1e;
}

/* TODO: Complete light theme */
"""


def get_theme_stylesheet(theme: str = "dark", font_size: int = 13) -> str:
    """Get the stylesheet for the specified theme.

    Args:
        theme: Theme name ("dark" or "light").
        font_size: Base font size in points for text content.

    Returns:
        CSS stylesheet string.
    """
    base = LIGHT_THEME if theme == "light" else DARK_THEME

    font_css = f"""
    QTreeWidget, QTreeWidget::item {{
        font-size: {font_size}pt;
    }}
    QPlainTextEdit, QTextEdit {{
        font-size: {font_size}pt;
    }}
    QLineEdit {{
        font-size: {font_size}pt;
    }}
    QListWidget, QListWidget::item {{
        font-size: {font_size}pt;
    }}
    QComboBox {{
        font-size: {font_size}pt;
    }}
    """

    return font_css + base
