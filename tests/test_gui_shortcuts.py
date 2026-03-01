"""Tests for GUI keyboard shortcuts.

Spec: /specs/gui-keyboard-shortcuts.md
Covers: Ctrl+S sync, Ctrl+N clear, Ctrl+I import, Ctrl+F focus search,
Delete/Ctrl+D delete, tooltip shortcut hints.
"""

import contextlib
from unittest.mock import patch

import pytest

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence

from espansr.core.config import Config
from espansr.core.templates import Template, TemplateManager

# ── Helpers ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tm(tmp_path):
    """Real TemplateManager backed by a temp directory."""
    return TemplateManager(templates_dir=tmp_path / "templates")


def _make_window(qtbot, config, tm=None, tmp_path=None):
    """Create a patched MainWindow for shortcut tests."""
    from espansr.ui.main_window import MainWindow

    tm_patch = (
        patch(
            "espansr.ui.template_browser.get_template_manager",
            return_value=tm,
        )
        if tm is not None
        else patch("espansr.ui.template_browser.get_template_manager")
    )

    with contextlib.ExitStack() as stack:
        stack.enter_context(patch("espansr.ui.main_window.get_config", return_value=config))
        stack.enter_context(patch("espansr.ui.main_window.get_config_manager"))
        stack.enter_context(patch("espansr.ui.template_browser.get_config"))
        stack.enter_context(patch("espansr.ui.template_editor.get_config"))
        stack.enter_context(
            patch(
                "espansr.integrations.espanso.get_match_dir",
                return_value=None,
            )
        )
        stack.enter_context(
            patch(
                "espansr.integrations.espanso.get_espanso_config_dir",
                return_value=tmp_path,
            )
        )
        stack.enter_context(
            patch(
                "espansr.integrations.espanso._get_candidate_paths",
                return_value=[],
            )
        )
        stack.enter_context(tm_patch)

        window = MainWindow()
        qtbot.addWidget(window)

    return window


# ── Ctrl+S — Sync Now ────────────────────────────────────────────────────────


def test_ctrl_s_triggers_sync(qtbot, tmp_path):
    """Ctrl+S fires _do_sync (same as clicking the Sync button)."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with patch.object(window, "_do_sync") as mock_sync:
        qtbot.keyClick(window, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)

    mock_sync.assert_called_once()


# ── Ctrl+N — New template ────────────────────────────────────────────────────


def test_ctrl_n_clears_editor(qtbot, tmp_path):
    """Ctrl+N clears the editor (creates a new template)."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with patch.object(window._editor, "clear") as mock_clear:
        qtbot.keyClick(window, Qt.Key.Key_N, Qt.KeyboardModifier.ControlModifier)

    mock_clear.assert_called_once()


# ── Ctrl+I — Import ──────────────────────────────────────────────────────────


def test_ctrl_i_opens_import_dialog(qtbot, tmp_path):
    """Ctrl+I triggers the import action."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with patch.object(window, "_do_import") as mock_import:
        qtbot.keyClick(window, Qt.Key.Key_I, Qt.KeyboardModifier.ControlModifier)

    mock_import.assert_called_once()


# ── Ctrl+F — Focus search ────────────────────────────────────────────────────


def test_ctrl_f_focuses_search(qtbot, tmp_path):
    """Ctrl+F focuses the browser search field."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with patch.object(window._browser, "focus_search") as mock_focus:
        qtbot.keyClick(window, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)

    mock_focus.assert_called_once()


# ── Delete / Ctrl+D — Delete selected ────────────────────────────────────────


def test_delete_triggers_delete(qtbot, tmp_path):
    """Delete key triggers start_delete on the browser."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with patch.object(window._browser, "start_delete") as mock_del:
        qtbot.keyClick(window, Qt.Key.Key_Delete)

    mock_del.assert_called_once()


def test_ctrl_d_triggers_delete(qtbot, tmp_path):
    """Ctrl+D triggers start_delete on the browser."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    with patch.object(window._browser, "start_delete") as mock_del:
        qtbot.keyClick(window, Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)

    mock_del.assert_called_once()


# ── Tooltips include shortcut hints ──────────────────────────────────────────


def test_sync_tooltip_includes_shortcut(qtbot, tmp_path):
    """Sync button tooltip mentions Ctrl+S."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    tooltip = window._sync_btn.toolTip()
    assert "Ctrl+S" in tooltip


def test_import_tooltip_includes_shortcut(qtbot, tmp_path):
    """Import button tooltip mentions Ctrl+I."""
    window = _make_window(qtbot, Config(), tmp_path=tmp_path)

    tooltip = window._import_btn.toolTip()
    assert "Ctrl+I" in tooltip
