"""Main window for automatr-espanso."""

import base64
import sys
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import QByteArray, Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QMainWindow,
    QPushButton,
    QSplitter,
    QStatusBar,
    QToolBar,
)

from automatr_espanso.core.config import get_config, get_config_manager, save_config
from automatr_espanso.ui.template_browser import TemplateBrowserWidget
from automatr_espanso.ui.template_editor import TemplateEditorWidget
from automatr_espanso.ui.theme import get_theme_stylesheet

AUTO_SYNC_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes


class MainWindow(QMainWindow):
    """Main application window for automatr-espanso."""

    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        self._config = get_config()
        self.setWindowTitle("Automatr — Espanso Manager")
        self._setup_ui()
        self._apply_theme()
        self._restore_geometry()
        self._clean_stale_espanso_files()
        self._check_launcher()
        self._restore_last_template()

    def _setup_ui(self) -> None:
        """Build toolbar, splitter (browser | editor), and status bar."""
        # Toolbar
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        self._sync_btn = QPushButton("Sync Now")
        self._sync_btn.clicked.connect(self._do_sync)
        toolbar.addWidget(self._sync_btn)

        self._auto_sync_cb = QCheckBox("Auto-sync")
        self._auto_sync_cb.setChecked(self._config.espanso.auto_sync)
        self._auto_sync_cb.stateChanged.connect(self._toggle_auto_sync)
        toolbar.addWidget(self._auto_sync_cb)

        # Auto-sync timer
        self._auto_sync_timer = QTimer(self)
        self._auto_sync_timer.setInterval(AUTO_SYNC_INTERVAL_MS)
        self._auto_sync_timer.timeout.connect(self._do_sync)
        if self._config.espanso.auto_sync:
            self._auto_sync_timer.start()

        # Splitter: browser | editor
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        self._browser = TemplateBrowserWidget()
        self._splitter.addWidget(self._browser)

        self._editor = TemplateEditorWidget()
        self._splitter.addWidget(self._editor)

        sizes = self._config.ui.splitter_sizes
        if len(sizes) >= 2:
            self._splitter.setSizes(sizes)

        self._splitter.splitterMoved.connect(self._on_splitter_moved)
        self.setCentralWidget(self._splitter)

        # Status bar
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        # Wire signals
        self._browser.template_selected.connect(self._editor.load_template)
        self._browser.new_template_requested.connect(self._editor.clear)
        self._editor.template_saved.connect(self._on_template_saved)
        self._browser.status_message.connect(
            lambda msg, ms: status_bar.showMessage(msg, ms)
        )
        self._editor.status_message.connect(
            lambda msg, ms: status_bar.showMessage(msg, ms)
        )

    def _apply_theme(self) -> None:
        """Apply the configured theme stylesheet."""
        stylesheet = get_theme_stylesheet(
            theme=self._config.ui.theme,
            font_size=self._config.ui.font_size,
        )
        self.setStyleSheet(stylesheet)

    def _restore_geometry(self) -> None:
        """Restore window geometry from config."""
        ui = self._config.ui
        if ui.window_geometry:
            self.restoreGeometry(QByteArray(base64.b64decode(ui.window_geometry)))
        else:
            self.resize(ui.window_width, ui.window_height)
            if ui.window_x >= 0 and ui.window_y >= 0:
                self.move(ui.window_x, ui.window_y)
        if ui.window_maximized:
            self.showMaximized()

    def _restore_last_template(self) -> None:
        """Restore the last-selected template from config."""
        name = self._config.ui.last_template
        if name:
            self._browser.select_template_by_name(name)

    def _clean_stale_espanso_files(self) -> None:
        """Remove automatr-managed files from non-canonical Espanso dirs."""
        from automatr_espanso.integrations.espanso import clean_stale_espanso_files

        clean_stale_espanso_files()

    def _check_launcher(self) -> None:
        """Show a status bar tip if the launcher trigger file is missing."""
        from automatr_espanso.integrations.espanso import get_match_dir

        match_dir = get_match_dir()
        if match_dir is None:
            return

        launcher = match_dir / "automatr-launcher.yml"
        if not launcher.exists():
            trigger = self._config.espanso.launcher_trigger or ":aopen"
            self.statusBar().showMessage(
                f"Tip: Type '{trigger}' anywhere after syncing to launch this GUI. "
                f"Run 'automatr-espanso sync' or use install.sh to enable it.",
                8000,
            )

    # ── Sync ────────────────────────────────────────────────────────────────

    def _do_sync(self) -> None:
        """Perform the Espanso sync and update status bar."""
        self._sync_btn.setEnabled(False)
        try:
            from automatr_espanso.integrations.espanso import sync_to_espanso

            success = sync_to_espanso()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if success:
                self.statusBar().showMessage("Sync successful", 5000)
                get_config_manager().update(**{"espanso.last_sync": now})
                self._browser.refresh()
            else:
                self.statusBar().showMessage("Sync failed", 5000)
        except Exception as e:
            self.statusBar().showMessage(f"Sync error: {e}", 5000)
        finally:
            self._sync_btn.setEnabled(True)

    def _toggle_auto_sync(self, state: int) -> None:
        """Start or stop the auto-sync timer."""
        enabled = Qt.CheckState(state) == Qt.CheckState.Checked
        if enabled:
            self._auto_sync_timer.start()
        else:
            self._auto_sync_timer.stop()
        get_config_manager().update(**{"espanso.auto_sync": enabled})

    # ── Callbacks ───────────────────────────────────────────────────────────

    def _on_template_saved(self, template) -> None:
        """Refresh browser after a template is saved."""
        self._browser.refresh()
        self._browser.select_template_by_name(template.name)

    def _on_splitter_moved(self, pos: int, index: int) -> None:
        """Persist splitter position when the user drags it."""
        self._config.ui.splitter_sizes = list(self._splitter.sizes())
        save_config(self._config)

    def closeEvent(self, event) -> None:
        """Persist window geometry and state on close."""
        ui = self._config.ui
        ui.window_width = self.width()
        ui.window_height = self.height()
        ui.window_x = self.x()
        ui.window_y = self.y()
        ui.window_maximized = self.isMaximized()
        ui.window_geometry = base64.b64encode(
            self.saveGeometry().data()
        ).decode()
        ui.splitter_sizes = list(self._splitter.sizes())
        t = self._browser.get_current_template()
        ui.last_template = t.name if t else ""
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
