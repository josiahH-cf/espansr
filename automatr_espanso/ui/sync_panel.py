"""Sync panel widget for automatr-espanso.

Displays sync status, manual sync button, auto-sync toggle,
and Espanso process availability.
"""

from datetime import datetime
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from automatr_espanso.core.templates import Template


class SyncPanelWidget(QWidget):
    """Panel for managing Espanso sync operations.

    Emits:
        sync_completed(bool): True if the last sync succeeded, False otherwise.
    """

    sync_completed = pyqtSignal(bool)

    AUTO_SYNC_INTERVAL_MS = 5 * 60 * 1000  # 5 minutes

    def __init__(self, parent: Optional[QWidget] = None):
        """Initialize the sync panel."""
        super().__init__(parent)
        self._current_template: Optional[Template] = None

        self._auto_sync_timer = QTimer()
        self._auto_sync_timer.setInterval(self.AUTO_SYNC_INTERVAL_MS)
        self._auto_sync_timer.timeout.connect(self._do_sync)

        self._setup_ui()
        self._load_saved_state()
        self._refresh_espanso_status()

    def _setup_ui(self) -> None:
        """Build the panel layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 10, 10, 10)
        layout.setSpacing(10)

        # ── Selected template info ──────────────────────────────────────────
        template_group = QGroupBox("Selected Template")
        tg_layout = QVBoxLayout(template_group)

        self._template_name_label = QLabel("No template selected")
        self._template_name_label.setStyleSheet("font-weight: bold;")
        tg_layout.addWidget(self._template_name_label)

        trigger_row = QHBoxLayout()
        trigger_row.addWidget(QLabel("Trigger:"))

        self._trigger_label = QLabel("—")
        self._trigger_label.setStyleSheet(
            "font-family: monospace; font-weight: bold; color: #4fc1ff;"
        )
        trigger_row.addWidget(self._trigger_label)
        trigger_row.addStretch()

        self._edit_trigger_btn = QPushButton("Edit Trigger…")
        self._edit_trigger_btn.setObjectName("secondary")
        self._edit_trigger_btn.setEnabled(False)
        self._edit_trigger_btn.clicked.connect(self._open_trigger_editor)
        trigger_row.addWidget(self._edit_trigger_btn)

        tg_layout.addLayout(trigger_row)
        layout.addWidget(template_group)

        # ── Sync controls ───────────────────────────────────────────────────
        sync_group = QGroupBox("Espanso Sync")
        sg_layout = QVBoxLayout(sync_group)

        self._sync_btn = QPushButton("Sync Now")
        self._sync_btn.clicked.connect(self._do_sync)
        sg_layout.addWidget(self._sync_btn)

        self._auto_sync_cb = QCheckBox("Auto-sync every 5 minutes")
        self._auto_sync_cb.stateChanged.connect(self._toggle_auto_sync)
        sg_layout.addWidget(self._auto_sync_cb)

        self._last_sync_label = QLabel("Last sync: never")
        self._last_sync_label.setStyleSheet("color: #808080;")
        sg_layout.addWidget(self._last_sync_label)

        self._sync_status_label = QLabel("Status: idle")
        sg_layout.addWidget(self._sync_status_label)

        layout.addWidget(sync_group)

        # ── Espanso process status ──────────────────────────────────────────
        espanso_group = QGroupBox("Espanso Status")
        eg_layout = QVBoxLayout(espanso_group)

        self._espanso_status_label = QLabel("Checking…")
        eg_layout.addWidget(self._espanso_status_label)

        self._espanso_path_label = QLabel("")
        self._espanso_path_label.setWordWrap(True)
        self._espanso_path_label.setStyleSheet("color: #808080; font-size: 11pt;")
        eg_layout.addWidget(self._espanso_path_label)

        layout.addWidget(espanso_group)

        # ── Activity log ────────────────────────────────────────────────────
        log_label = QLabel("Activity log:")
        log_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(log_label)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(160)
        layout.addWidget(self._log)

        layout.addStretch()

    # ── Public API ────────────────────────────────────────────────────────

    def set_template(self, template: Template) -> None:
        """Update the displayed template info when the user selects one."""
        self._current_template = template
        self._template_name_label.setText(template.name)
        self._trigger_label.setText(template.trigger or "—")
        self._edit_trigger_btn.setEnabled(True)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _load_saved_state(self) -> None:
        """Restore last sync time and auto-sync toggle from config."""
        from automatr_espanso.core.config import get_config

        config = get_config()
        if config.espanso.last_sync:
            self._last_sync_label.setText(f"Last sync: {config.espanso.last_sync}")
        if config.espanso.auto_sync:
            self._auto_sync_cb.setChecked(True)

    def _do_sync(self) -> None:
        """Perform the Espanso sync and update UI."""
        self._sync_status_label.setText("Status: syncing…")
        self._sync_btn.setEnabled(False)
        QApplication_processEvents()

        try:
            from automatr_espanso.integrations.espanso import sync_to_espanso

            success = sync_to_espanso()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if success:
                self._sync_status_label.setText("Status: synced successfully ✓")
                self._last_sync_label.setText(f"Last sync: {now}")
                self._log.append(f"[{now}] Sync successful")

                # Persist last sync time
                from automatr_espanso.core.config import get_config_manager

                get_config_manager().update(**{"espanso.last_sync": now})
            else:
                self._sync_status_label.setText("Status: sync failed ✗")
                self._log.append(f"[{now}] Sync failed — check Espanso config path")

            self.sync_completed.emit(success)

        except Exception as e:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self._sync_status_label.setText("Status: error")
            self._log.append(f"[{now}] Error: {e}")
            self.sync_completed.emit(False)
        finally:
            self._sync_btn.setEnabled(True)

    def _toggle_auto_sync(self, state: int) -> None:
        """Start or stop the auto-sync timer."""
        enabled = Qt.CheckState(state) == Qt.CheckState.Checked
        if enabled:
            self._auto_sync_timer.start()
        else:
            self._auto_sync_timer.stop()

        from automatr_espanso.core.config import get_config_manager

        get_config_manager().update(**{"espanso.auto_sync": enabled})

    def _open_trigger_editor(self) -> None:
        """Open the trigger editor dialog for the current template."""
        if not self._current_template:
            return

        from automatr_espanso.ui.trigger_editor import TriggerEditorDialog

        dialog = TriggerEditorDialog(self._current_template, parent=self)
        if dialog.exec():
            # Reflect the updated trigger in the panel
            self._trigger_label.setText(self._current_template.trigger or "—")

    def _refresh_espanso_status(self) -> None:
        """Detect and display Espanso availability."""
        try:
            from automatr_espanso.integrations.espanso import get_espanso_config_dir

            config_dir = get_espanso_config_dir()
            if config_dir:
                self._espanso_status_label.setText("Espanso: found ✓")
                self._espanso_path_label.setText(str(config_dir))
            else:
                self._espanso_status_label.setText("Espanso: not found")
                self._espanso_path_label.setText(
                    "Install Espanso and restart, or set config path in settings."
                )
        except Exception as e:
            self._espanso_status_label.setText(f"Espanso: error ({e})")


def QApplication_processEvents() -> None:
    """Process pending Qt events to refresh UI before a blocking operation."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        app.processEvents()
