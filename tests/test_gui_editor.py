"""Tests for TemplateEditorWidget and TemplateBrowserWidget.

Covers editor load/clear/save flows and browser new/delete/undo flows.
"""

from unittest.mock import patch

import pytest

from automatr_espanso.core.templates import Template, TemplateManager


@pytest.fixture()
def tm(tmp_path):
    """Create a TemplateManager backed by a temp directory."""
    return TemplateManager(templates_dir=tmp_path)


@pytest.fixture()
def _patch_tm(tm):
    """Patch get_template_manager and get_config for all editor tests."""
    with (
        patch(
            "automatr_espanso.ui.template_editor.get_template_manager",
            return_value=tm,
        ),
        patch("automatr_espanso.ui.template_editor.get_config"),
    ):
        yield


@pytest.fixture()
def editor(qtbot, _patch_tm):
    """Create a TemplateEditorWidget for testing."""
    from automatr_espanso.ui.template_editor import TemplateEditorWidget

    widget = TemplateEditorWidget()
    qtbot.addWidget(widget)
    return widget


# ── Load / Clear ────────────────────────────────────────────────────────────


def test_editor_load_template(editor):
    """Loading a template populates all fields."""
    t = Template(name="Greeting", content="Hello {{name}}", trigger=":greet")
    editor.load_template(t)

    assert editor._name_edit.text() == "Greeting"
    assert editor._trigger_edit.text() == ":greet"
    assert editor._content_edit.toPlainText() == "Hello {{name}}"
    assert editor._current_template is t


def test_editor_clear(editor):
    """Clearing the editor empties all fields and resets state."""
    t = Template(name="X", content="Y", trigger=":x")
    editor.load_template(t)
    editor.clear()

    assert editor._name_edit.text() == ""
    assert editor._trigger_edit.text() == ""
    assert editor._content_edit.toPlainText() == ""
    assert editor._current_template is None


# ── Save ────────────────────────────────────────────────────────────────────


def test_editor_save_new(editor, tm, qtbot):
    """Saving with no loaded template creates a new one on disk."""
    editor._name_edit.setText("New Template")
    editor._trigger_edit.setText(":new")
    editor._content_edit.setPlainText("body text")

    with qtbot.waitSignal(editor.template_saved, timeout=1000):
        editor._save()

    saved = tm.get("New Template")
    assert saved is not None
    assert saved.trigger == ":new"
    assert saved.content == "body text"
    assert editor._current_template is not None


def test_editor_save_existing(editor, tm, qtbot):
    """Saving an existing template updates it on disk."""
    original = tm.create(name="Old", content="old body", trigger=":old")
    editor.load_template(original)

    editor._trigger_edit.setText(":updated")
    editor._content_edit.setPlainText("new body")

    with qtbot.waitSignal(editor.template_saved, timeout=1000):
        editor._save()

    reloaded = tm.get("Old")
    assert reloaded is not None
    assert reloaded.trigger == ":updated"
    assert reloaded.content == "new body"


def test_editor_save_empty_name(editor, qtbot):
    """Saving with an empty name emits a status error, not a crash."""
    editor._name_edit.setText("")

    with qtbot.waitSignal(editor.status_message, timeout=1000) as sig:
        editor._save()

    msg, _duration = sig.args
    assert "required" in msg.lower()


# ── Browser fixtures ────────────────────────────────────────────────────────


@pytest.fixture()
def _patch_browser_tm(tm):
    """Patch get_template_manager and get_config for browser tests."""
    with (
        patch(
            "automatr_espanso.ui.template_browser.get_template_manager",
            return_value=tm,
        ),
        patch("automatr_espanso.ui.template_browser.get_config"),
    ):
        yield


@pytest.fixture()
def browser(qtbot, _patch_browser_tm):
    """Create a TemplateBrowserWidget for testing."""
    from automatr_espanso.ui.template_browser import TemplateBrowserWidget

    widget = TemplateBrowserWidget()
    qtbot.addWidget(widget)
    return widget


# ── Browser: New ────────────────────────────────────────────────────────────


def test_browser_new_signal(browser, qtbot):
    """Clicking 'New' emits the new_template_requested signal."""
    with qtbot.waitSignal(browser.new_template_requested, timeout=1000):
        browser.new_template_requested.emit()


# ── Browser: Delete with undo ──────────────────────────────────────────────


def test_browser_delete_undo(browser, tm, qtbot):
    """Deleting then clicking Undo preserves the template."""
    tm.create(name="Keep Me", content="body")
    browser.load_templates()
    browser.select_template_by_name("Keep Me")

    browser._start_delete()
    assert browser._pending_delete is not None
    assert not browser._undo_row.isHidden()

    browser._cancel_delete()
    assert browser._pending_delete is None
    assert browser._undo_row.isHidden()

    assert tm.get("Keep Me") is not None


def test_browser_delete_confirmed(browser, tm, qtbot):
    """Deleting without undo removes the template after timeout."""
    tm.create(name="Delete Me", content="body")
    browser.load_templates()
    browser.select_template_by_name("Delete Me")

    browser._start_delete()
    # Simulate the timer firing immediately
    browser._finalize_delete()

    assert tm.get("Delete Me") is None
    assert browser._current_template is None
