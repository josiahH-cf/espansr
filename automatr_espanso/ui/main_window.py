"""Main window for automatr-espanso."""

import sys
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QSplitter,
    QStatusBar,
)

from automatr_espanso.core.config import get_config, save_config
from automatr_espanso.ui.template_browser import TemplateBrowserWidget
from automatr_espanso.ui.theme import get_theme_stylesheet


class MainWindow(QMainWindow):
    """Main application window for automatr-espanso."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self._config = get_config()
        self.setWindowTitle("Automatr — Espanso Manager")
        self.resize(self._config.ui.window_width, self._config.ui.window_height)
        self._setup_ui()
        self._apply_theme()

    def _setup_ui(self) -> None:
        """Build the two-pane splitter layout."""
        # Import here to avoid circular issues at module level
        from automatr_espanso.ui.sync_panel import SyncPanelWidget

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._browser = TemplateBrowserWidget()
        splitter.addWidget(self._browser)

        self._sync_panel = SyncPanelWidget()
        splitter.addWidget(self._sync_panel)

        sizes = self._config.ui.splitter_sizes
        if len(sizes) >= 2:
            splitter.setSizes(sizes)

        splitter.splitterMoved.connect(self._on_splitter_moved)
        self._browser.template_selected.connect(self._sync_panel.set_template)

        self.setCentralWidget(splitter)
        self._splitter = splitter

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        self._browser.status_message.connect(
            lambda msg, ms: status_bar.showMessage(msg, ms)
        )
        self._sync_panel.sync_completed.connect(self._on_sync_completed)

    def _apply_theme(self) -> None:
        """Apply the configured theme stylesheet."""
        stylesheet = get_theme_stylesheet(
            theme=self._config.ui.theme,
            font_size=self._config.ui.font_size,
        )
        self.setStyleSheet(stylesheet)

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """Persist splitter position when the user drags it."""
        self._config.ui.splitter_sizes = list(self._splitter.sizes())
        save_config(self._config)

    def _on_sync_completed(self, success: bool) -> None:
        """Update status bar after a sync attempt."""
        msg = "Sync successful" if success else "Sync failed — check the log"
        self.statusBar().showMessage(msg, 5000)
        # Refresh browser in case triggers were edited during this session
        self._browser.refresh()

    def closeEvent(self, event) -> None:
        """Persist window geometry on close."""
        self._config.ui.window_width = self.width()
        self._config.ui.window_height = self.height()
        save_config(self._config)
        super().closeEvent(event)


def launch() -> None:
    """Create the QApplication and launch the main window."""
    app: Optional[QApplication] = QApplication.instance()  # type: ignore[assignment]
    if app is None:
        app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
