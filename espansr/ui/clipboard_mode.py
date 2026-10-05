"""Explicit per-workstation clipboard mode; opening a window changes nothing."""

from PyQt6.QtCore import QEvent, QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QCheckBox

from espansr.integrations import espanso


class RemotePasteToggle(QCheckBox):
    """Use the same persistent Espanso modes as configure-remote-desktop."""

    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Remote paste", parent)
        self.setToolTip(
            "On: use remote-desktop paste settings and leave the expansion on the clipboard. "
            "Off: restore your copied text after expansion. "
            "This workstation's setting survives Sync and reinstall. "
            "RustDesk clipboard sharing must also be enabled in RustDesk."
        )
        self._watched_window = None
        self.refresh()
        self.toggled.connect(self._apply_mode)

    def refresh(self) -> None:
        """Reflect another window or CLI change without reapplying settings."""
        with QSignalBlocker(self):
            self.setChecked(espanso.get_managed_default_config_mode() == "host")
            self.setEnabled(espanso.get_espanso_config_dir() is not None)

    def showEvent(self, event) -> None:
        window = self.window()
        if window is not self._watched_window:
            if self._watched_window is not None:
                self._watched_window.removeEventFilter(self)
            self._watched_window = window
            window.installEventFilter(self)
        self.refresh()
        super().showEvent(event)

    def eventFilter(self, source, event) -> bool:
        if source is self._watched_window and event.type() == QEvent.Type.WindowActivate:
            self.refresh()
        return super().eventFilter(source, event)

    def _apply_mode(self, remote: bool) -> None:
        apply = espanso.apply_remote_desktop_config if remote else espanso.apply_workstation_config
        try:
            saved = apply()
        except Exception:
            saved = False
        self.refresh()
        if saved:
            message = (
                "Remote paste settings saved; expanded text stays on the clipboard."
                if remote
                else "Clipboard preservation saved; your copied text is restored after expansion."
            )
        else:
            message = "Could not change clipboard mode; check Espanso configuration and try again."
        self.status_message.emit(message)
