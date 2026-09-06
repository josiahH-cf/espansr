"""Tests for GUI keyboard shortcuts.

Spec: /specs/gui-keyboard-shortcuts.md
Covers: Ctrl+S publish, Ctrl+N clear, Ctrl+I import, Ctrl+F focus search,
Delete/Ctrl+D delete, tooltip shortcut hints.

Strategy: QShortcut does not reliably fire in headless test environments,
so we verify two things per shortcut:
  1. The key sequence is bound correctly (inspecting the QShortcut object).
  2. Emitting the shortcut's `activated` signal calls the expected handler.

Windows come from the shared ``make_window`` factory in ``tests/conftest.py``.
"""

from unittest.mock import patch

from PyQt6.QtGui import QKeySequence

from espansr.core.config import Config

# ── Ctrl+S — Publish ─────────────────────────────────────────────────────────


def test_ctrl_s_triggers_sync(make_window):
    """Ctrl+S shortcut is bound and fires _do_sync."""
    window = make_window(Config())

    assert window._shortcut_sync.key() == QKeySequence(QKeySequence.StandardKey.Save)

    with patch.object(window, "_do_sync") as mock_sync:
        window._shortcut_sync.activated.emit()

    mock_sync.assert_called_once()


# ── Ctrl+N — New template ────────────────────────────────────────────────────


def test_ctrl_n_clears_editor(make_window):
    """Ctrl+N shortcut is bound and clears the editor."""
    window = make_window(Config())

    assert window._shortcut_new.key() == QKeySequence("Ctrl+N")

    with patch.object(window._editor, "clear") as mock_clear:
        window._shortcut_new.activated.emit()

    mock_clear.assert_called_once()


# ── Ctrl+I — Import ──────────────────────────────────────────────────────────


def test_ctrl_i_opens_import_dialog(make_window):
    """Ctrl+I shortcut is bound and triggers import."""
    window = make_window(Config())

    assert window._shortcut_import.key() == QKeySequence("Ctrl+I")

    with patch.object(window, "_do_import") as mock_import:
        window._shortcut_import.activated.emit()

    mock_import.assert_called_once()


# ── Ctrl+F — Focus search ────────────────────────────────────────────────────


def test_ctrl_f_focuses_search(make_window):
    """Ctrl+F shortcut is bound and focuses the browser search field."""
    window = make_window(Config())

    assert window._shortcut_search.key() == QKeySequence(QKeySequence.StandardKey.Find)

    with patch.object(window._browser, "focus_search") as mock_focus:
        window._shortcut_search.activated.emit()

    mock_focus.assert_called_once()


# ── Delete / Ctrl+D — Delete selected ────────────────────────────────────────


def test_delete_triggers_delete(make_window):
    """Delete shortcut is bound and triggers start_delete."""
    window = make_window(Config())

    assert window._shortcut_delete.key() == QKeySequence("Delete")

    with patch.object(window._browser, "start_delete") as mock_del:
        window._shortcut_delete.activated.emit()

    mock_del.assert_called_once()


def test_ctrl_d_triggers_delete(make_window):
    """Ctrl+D shortcut is bound and triggers start_delete."""
    window = make_window(Config())

    assert window._shortcut_delete_alt.key() == QKeySequence("Ctrl+D")

    with patch.object(window._browser, "start_delete") as mock_del:
        window._shortcut_delete_alt.activated.emit()

    mock_del.assert_called_once()


# ── Tooltips include shortcut hints ──────────────────────────────────────────


def test_sync_tooltip_includes_shortcut(make_window):
    """Sync button tooltip mentions Ctrl+S."""
    window = make_window(Config())

    tooltip = window._sync_btn.toolTip()
    assert "Ctrl+S" in tooltip


def test_import_tooltip_includes_shortcut(make_window):
    """Import button tooltip mentions Ctrl+I."""
    window = make_window(Config())

    tooltip = window._import_btn.toolTip()
    assert "Ctrl+I" in tooltip
