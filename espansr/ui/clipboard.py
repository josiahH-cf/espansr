"""Copy exact text reliably when remote-desktop clipboard readers hold a lock."""

import ctypes
import logging
import time
from typing import Callable

from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


def _clipboard_available() -> bool:
    if QApplication.platformName().lower() != "windows":
        return True
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    if not user32.OpenClipboard(None):
        return False
    user32.CloseClipboard()
    return True


class _ClipboardWriter(QObject):
    def __init__(self, app):
        super().__init__(app)
        self._pending = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._attempt)

    def copy(self, text: str, on_success, on_failure) -> None:
        self._timer.stop()
        self._pending = (text, time.monotonic() + 3, on_success, on_failure)
        self._attempt()

    def _attempt(self) -> None:
        if self._pending is None:
            return
        request = self._pending
        text, deadline, on_success, on_failure = request
        clipboard = QApplication.clipboard()
        if clipboard is not None and _clipboard_available():
            clipboard.setText(text)
            if clipboard.ownsClipboard() or clipboard.text() == text:
                self._finish(request, on_success)
                return
        if self._pending is not request:
            return
        if time.monotonic() >= deadline:
            self._finish(request, on_failure)
        else:
            self._timer.start()

    def _finish(self, request, callback) -> None:
        if self._pending is not request:
            return
        self._pending = None
        self._timer.stop()
        if callback is not None:
            try:
                callback()
            except RuntimeError:
                # The source window may have closed while the clipboard was busy.
                logger.debug("Clipboard action's source window was closed")


def copy_text(
    text: str,
    *,
    on_success: Callable[[], None] | None = None,
    on_failure: Callable[[], None] | None = None,
) -> None:
    app = QApplication.instance()
    if app is None:
        if on_failure is not None:
            on_failure()
        return
    writer = getattr(app, "_espansr_clipboard_writer", None)
    if writer is None:
        writer = _ClipboardWriter(app)
        app._espansr_clipboard_writer = writer
    writer.copy(text, on_success, on_failure)
