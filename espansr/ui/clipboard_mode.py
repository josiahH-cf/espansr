"""Explicit per-workstation clipboard mode; opening a window changes nothing."""

from PyQt6.QtCore import QEvent, QSignalBlocker, pyqtSignal
from PyQt6.QtWidgets import QCheckBox

from espansr.integrations import espanso


def _seconds(mode: str) -> str:
    return f"{espanso.mode_restore_delay_ms(mode) / 1000:g}"


class RemotePasteToggle(QCheckBox):
    """Use the same persistent Espanso modes as configure-remote-desktop."""

    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Remote paste", parent)
        self.setToolTip(
            "On: remote-desktop paste settings, set to bring your copied text back "
            f"{_seconds('host')} s after an expansion. "
            f"Off: workstation settings, set to bring it back after {_seconds('workstation')} s. "
            "An app that pastes later than that pastes your copied text instead of the prompt. "
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
        espanso.take_config_change()  # report only what this switch does
        try:
            saved = apply()
        except Exception:
            saved = False
        change = espanso.take_config_change()
        self.refresh()
        label = "Remote paste" if remote else "Workstation paste"
        if not saved and change is not None and change.error:
            kept = "; default.yml was left as it was" if change.path else ""
            message = f"Could not change clipboard mode ({change.error}){kept}."
        elif not saved:
            message = "Could not change clipboard mode; check Espanso configuration and try again."
        elif change is not None and change.reloaded is False:
            message = (
                f"{label} settings saved, but Espanso did not restart, so espansr cannot "
                "confirm it uses them; restart Espanso."
            )
        else:
            restore = espanso.describe_saved_restore(espanso.get_clipboard_restore_behavior())
            restarted = (
                "; Espanso restarted and reports running"
                if change is not None and change.reloaded is True
                else ""
            )
            message = f"{label} settings saved ({restore}){restarted}."
        self.status_message.emit(message)
