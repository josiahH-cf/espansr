"""Busy clipboard retries preserve exact text and prioritize the newest copy."""

from unittest.mock import Mock

import pytest
from PyQt6.QtWidgets import QApplication

from espansr.ui import clipboard


@pytest.fixture(autouse=True)
def reset_writer(qapp):
    writer = getattr(qapp, "_espansr_clipboard_writer", None)
    if writer is not None:
        writer._timer.stop()
        writer._pending = None
    yield
    writer = getattr(qapp, "_espansr_clipboard_writer", None)
    if writer is not None:
        writer._timer.stop()
        writer._pending = None


def test_busy_clipboard_retries_without_blocking_and_keeps_exact_text(qtbot, monkeypatch):
    available = False
    monkeypatch.setattr(clipboard, "_clipboard_available", lambda: available)
    copied = Mock()
    payload = "Résumé 👋\nSecond line. \n\n"
    clipboard.copy_text(payload, on_success=copied)
    assert not copied.called
    assert QApplication.instance()._espansr_clipboard_writer._timer.isActive()
    available = True
    qtbot.waitUntil(lambda: copied.called)
    assert QApplication.clipboard().text() == payload
    copied.assert_called_once_with()


def test_newest_copy_cancels_older_pending_text(qtbot, monkeypatch):
    available = False
    monkeypatch.setattr(clipboard, "_clipboard_available", lambda: available)
    first = Mock()
    second = Mock()
    clipboard.copy_text("Old prompt", on_success=first)
    clipboard.copy_text("Current prompt. ", on_success=second)
    available = True
    qtbot.waitUntil(lambda: second.called)
    assert QApplication.clipboard().text() == "Current prompt. "
    first.assert_not_called()
    second.assert_called_once_with()


def test_permanent_lock_reports_failure_once_and_stops(qtbot, monkeypatch):
    monkeypatch.setattr(clipboard, "_clipboard_available", lambda: False)
    monkeypatch.setattr(clipboard.time, "monotonic", lambda: 10)
    failed = Mock()
    copied = Mock()
    clipboard.copy_text("Cannot copy yet", on_success=copied, on_failure=failed)
    writer = QApplication.instance()._espansr_clipboard_writer
    monkeypatch.setattr(clipboard.time, "monotonic", lambda: 14)
    writer._attempt()
    failed.assert_called_once_with()
    copied.assert_not_called()
    assert not writer._timer.isActive()
    assert writer._pending is None


def test_clipboard_rejecting_a_write_is_retried(qtbot, monkeypatch):
    writes = []
    stored = ""

    class Clipboard:
        def setText(self, text):
            nonlocal stored
            writes.append(text)
            if len(writes) > 1:
                stored = text

        def ownsClipboard(self):
            return False

        def text(self):
            return stored

    monkeypatch.setattr(clipboard, "_clipboard_available", lambda: True)
    monkeypatch.setattr(QApplication, "clipboard", staticmethod(lambda: Clipboard()))
    copied = Mock()
    clipboard.copy_text("Full prompt. ", on_success=copied)
    qtbot.waitUntil(lambda: copied.called)
    assert writes == ["Full prompt. ", "Full prompt. "]
    assert stored == "Full prompt. "
