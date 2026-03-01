"""PyQt6 theme configuration for espansr."""

from PyQt6.QtWidgets import QApplication

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

QToolBar {
    background-color: #252526;
    border-bottom: 1px solid #3c3c3c;
    padding: 4px;
    spacing: 8px;
}

QToolBar QPushButton {
    min-width: 60px;
    padding: 6px 12px;
}

/* Variable editor rows */
VariableRowWidget {
    border: 1px solid #2d2d2d;
    border-radius: 4px;
    padding: 4px;
    margin-bottom: 2px;
}

VariableRowWidget QLineEdit {
    padding: 4px 6px;
}

VariableRowWidget QComboBox {
    padding: 4px 6px;
}

VariableRowWidget QPushButton#danger {
    min-width: 24px;
    max-width: 30px;
    padding: 2px;
    font-weight: bold;
}

/* YAML preview (read-only) */
QPlainTextEdit[readOnly="true"] {
    background-color: #1a1a2e;
    color: #9cdcfe;
    font-family: monospace;
    border: 1px solid #3c3c3c;
}
"""

# Light theme — VS Code "Light Modern" inspired palette
# Background: #f3f3f3  Panel: #ffffff  Text: #1e1e1e  Accent: #0078d4
LIGHT_THEME = """
QMainWindow, QWidget {
    background-color: #f3f3f3;
    color: #1e1e1e;
}

QLabel {
    color: #1e1e1e;
}

QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #c8c8c8;
    border-radius: 4px;
    padding: 6px;
    selection-background-color: #add6ff;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #0078d4;
}

QPushButton {
    background-color: #0078d4;
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #1a86d9;
}

QPushButton:pressed {
    background-color: #005fa3;
}

QPushButton:disabled {
    background-color: #c8c8c8;
    color: #a0a0a0;
}

QPushButton#secondary {
    background-color: #e0e0e0;
    color: #1e1e1e;
}

QPushButton#secondary:hover {
    background-color: #d0d0d0;
}

QPushButton#danger {
    background-color: #c42b1c;
}

QPushButton#danger:hover {
    background-color: #d43b2c;
}

QListWidget {
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #c8c8c8;
    border-radius: 4px;
    outline: none;
}

QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #e8e8e8;
}

QListWidget::item:selected {
    background-color: #c8ddf5;
    color: #1e1e1e;
}

QListWidget::item:hover {
    background-color: #e8e8e8;
}

QTreeWidget {
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #c8c8c8;
    border-radius: 4px;
    outline: none;
}

QTreeWidget::item {
    padding: 4px;
}

QTreeWidget::item:selected {
    background-color: #c8ddf5;
    color: #1e1e1e;
}

QTreeWidget::item:hover {
    background-color: #e8e8e8;
}

QSplitter::handle {
    background-color: #c8c8c8;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

QScrollBar:vertical {
    background-color: #f3f3f3;
    width: 12px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #b0b0b0;
    border-radius: 4px;
    min-height: 20px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #909090;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #f3f3f3;
    height: 12px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #b0b0b0;
    border-radius: 4px;
    min-width: 20px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #909090;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QMenuBar {
    background-color: #ffffff;
    color: #1e1e1e;
    border-bottom: 1px solid #c8c8c8;
}

QMenuBar::item:selected {
    background-color: #e0e0e0;
}

QMenu {
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #c8c8c8;
}

QMenu::item:selected {
    background-color: #c8ddf5;
}

QStatusBar {
    background-color: #0078d4;
    color: #ffffff;
}

QGroupBox {
    border: 1px solid #c8c8c8;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    color: #1e1e1e;
}

QTabWidget::pane {
    border: 1px solid #c8c8c8;
    border-radius: 4px;
}

QTabBar::tab {
    background-color: #e8e8e8;
    color: #1e1e1e;
    padding: 8px 16px;
    border: 1px solid #c8c8c8;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    border-bottom: 2px solid #0078d4;
}

QTabBar::tab:hover:!selected {
    background-color: #d0d0d0;
}

QComboBox {
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #c8c8c8;
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
    background-color: #ffffff;
    color: #1e1e1e;
    border: 1px solid #c8c8c8;
    selection-background-color: #c8ddf5;
}

QCheckBox {
    color: #1e1e1e;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #c8c8c8;
    border-radius: 3px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #0078d4;
    border-color: #0078d4;
}

QToolTip {
    background-color: #f3f3f3;
    color: #1e1e1e;
    border: 1px solid #c8c8c8;
    padding: 4px;
}

QToolBar {
    background-color: #ffffff;
    border-bottom: 1px solid #c8c8c8;
    padding: 4px;
    spacing: 8px;
}

QToolBar QPushButton {
    min-width: 60px;
    padding: 6px 12px;
}

/* Variable editor rows */
VariableRowWidget {
    border: 1px solid #e0e0e0;
    border-radius: 4px;
    padding: 4px;
    margin-bottom: 2px;
}

VariableRowWidget QLineEdit {
    padding: 4px 6px;
}

VariableRowWidget QComboBox {
    padding: 4px 6px;
}

VariableRowWidget QPushButton#danger {
    min-width: 24px;
    max-width: 30px;
    padding: 2px;
    font-weight: bold;
}

/* YAML preview (read-only) */
QPlainTextEdit[readOnly="true"] {
    background-color: #f8f8f8;
    color: #0451a5;
    font-family: monospace;
    border: 1px solid #c8c8c8;
}
"""


def detect_system_theme() -> str:
    """Detect the operating system color scheme preference.

    Tries Qt 6.5+ ``QStyleHints.colorScheme()`` first, then falls back to
    ``QPalette`` window-color luminance.  Returns ``"dark"`` on any failure.

    Returns:
        ``"dark"`` or ``"light"``.
    """
    try:
        app = QApplication.instance()
        if app is None:
            return "dark"

        # Qt 6.5+ exposes colorScheme() on styleHints
        hints = app.styleHints()
        try:
            scheme = hints.colorScheme()
            # Qt.ColorScheme enum: Unknown=0, Light=1, Dark=2
            if scheme.value == 1:
                return "light"
            if scheme.value == 2:
                return "dark"
        except AttributeError:
            pass  # Qt < 6.5 — fall through to palette check

        # Fallback: check palette window color luminance
        palette = app.palette()
        window_color = palette.color(palette.ColorRole.Window)
        luminance = (
            0.299 * window_color.red() + 0.587 * window_color.green() + 0.114 * window_color.blue()
        )
        return "light" if luminance >= 128 else "dark"
    except Exception:
        return "dark"


def get_theme_stylesheet(theme: str = "dark", font_size: int = 13) -> str:
    """Get the stylesheet for the specified theme.

    Args:
        theme: Theme name (``"dark"``, ``"light"``, or ``"auto"``).
            ``"auto"`` resolves to ``"dark"`` or ``"light"`` via system detection.
        font_size: Base font size in points for text content.

    Returns:
        CSS stylesheet string.
    """
    resolved = theme
    if theme == "auto":
        resolved = detect_system_theme()

    base = LIGHT_THEME if resolved == "light" else DARK_THEME

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
