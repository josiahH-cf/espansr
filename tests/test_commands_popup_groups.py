"""User-facing discovery, optional links, refresh, and local window persistence."""

from pathlib import Path
from unittest.mock import patch

import pytest
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWidgets import QApplication

from espansr.core.command_catalog import CommandCatalogEntry, build_command_catalog
from espansr.core.config import Config, get_config_path, load_config_fresh, save_config
from espansr.core.templates import Template, TemplateManager
from espansr.core.workflows import load_workflow_catalog
from espansr.ui.commands_popup import CommandsPopupDialog

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def reference(qtbot):
    config = Config()
    catalog = load_workflow_catalog([ROOT / "templates" / "_meta" / "workflows"])
    entries = build_command_catalog(
        TemplateManager(templates_dir=ROOT / "templates"), config, catalog
    )
    with patch("espansr.ui.commands_popup.get_config", return_value=config):
        dialog = CommandsPopupDialog(entries=entries, workflow_catalog=catalog)
    qtbot.addWidget(dialog)
    return dialog


def _group(dialog, group_id):
    for row in range(dialog._groups.count()):
        if dialog._groups.item(row).data(Qt.ItemDataRole.UserRole) == group_id:
            dialog._groups.setCurrentRow(row)
            return
    raise AssertionError(f"Missing group: {group_id}")


def _triggers(dialog):
    return [entry.trigger for entry in dialog._visible_entries()]


def test_browse_reminds_user_of_continue_unblock_and_context_together(reference):
    _group(reference, "keep-moving")
    assert {":continue", ":unblock", ":context"} <= set(_triggers(reference))
    assert "Resume work or clear blockers" in reference._guide_browser.toPlainText()
    assert "Unblock already continues after clarification" in reference._guide_browser.toPlainText()
    reference._summary_table.setCurrentCell(_triggers(reference).index(":unblock"), 0)
    assert "Resolve blockers" in reference._detail_widget._cue_label.text()
    assert reference._detail_widget._copy_prompt_btn.isVisibleTo(reference._detail_widget)


def test_context_litmus_guide_explains_generated_assets_and_optional_context(reference):
    _group(reference, "carry-context")
    assert {":context", ":litmus"} <= set(_triggers(reference))
    guide = reference._guide_browser.toPlainText()
    assert "copying the Litmus command itself does not provide the project evidence" in guide
    assert "Add a generated Context note only when" in guide
    reference._summary_table.setCurrentCell(_triggers(reference).index(":litmus"), 0)
    assert "Draft checks" in reference._detail_widget._cue_label.text()
    assert ":context" in reference._detail_widget._related_label.text()
    assert "essential facts" in reference._detail_widget._related_label.text()


@pytest.mark.parametrize("view", ["Browse", "Recommended", "Favorites", "Recent"])
def test_group_membership_intersects_every_command_view_and_search(reference, view):
    reference._config.discovery.favorite_triggers = [":research", ":unblock"]
    reference._config.discovery.recent_triggers = [":research", ":unblock"]
    _group(reference, "keep-moving")
    reference._view_combo.setCurrentText(view)
    assert ":unblock" in _triggers(reference)
    assert ":research" not in _triggers(reference)
    reference._search_edit.setText("image-generator")
    assert _triggers(reference) == []
    assert reference._empty_label.isVisibleTo(reference._command_page)
    reference._search_everywhere_btn.click()
    assert ":image-generator" in _triggers(reference)
    assert reference._search_edit.text() == "image-generator"


def test_show_all_clears_group_artifact_search_and_favorite_filters(reference):
    _group(reference, "check-work")
    reference._view_combo.setCurrentText("Favorites")
    reference._search_edit.setText("litmus")
    reference._have_combo.setCurrentText("context-packet")
    reference._want_combo.setCurrentText("human-litmus")
    reference._all_btn.click()
    assert len(reference._visible_entries()) == len(reference._entries)
    assert reference._group_id == ""
    assert reference._current_query().text == ""
    assert reference._current_query().have_artifact == ""
    assert reference._current_query().want_artifact == ""


def test_guide_link_selects_current_trigger_and_clears_filters_without_execution(reference):
    from dataclasses import replace

    reference._entries = [
        (
            replace(entry, trigger=":outcome-checks")
            if entry.capability_id == "human-litmus"
            else entry
        )
        for entry in reference._entries
    ]
    reference._populate_groups()
    _group(reference, "carry-context")
    assert ":outcome-checks" in reference._guide_browser.toPlainText()
    reference._search_edit.setText("nothing matches this particular query")
    QApplication.clipboard().setText("unchanged clipboard")
    with patch("subprocess.run") as run, patch("subprocess.Popen") as popen:
        reference._guide_browser.anchorClicked.emit(QUrl("capability:human-litmus"))
        reference._follow_link("https://example.com")
    assert reference._selected_entry.trigger == ":outcome-checks"
    assert QApplication.clipboard().text() == "unchanged clipboard"
    run.assert_not_called()
    popen.assert_not_called()


def test_keyboard_search_and_selection_only_reveal_details(reference, qtbot):
    reference.show()
    reference.activateWindow()
    qtbot.waitUntil(reference.isActiveWindow)
    reference._scratchpad.setFocus()
    qtbot.keyClick(reference._scratchpad, Qt.Key.Key_F, Qt.KeyboardModifier.ControlModifier)
    qtbot.waitUntil(reference._search_edit.hasFocus)
    reference._search_edit.setText(":continue")
    QApplication.clipboard().setText("unchanged clipboard")
    qtbot.keyClick(reference._search_edit, Qt.Key.Key_Return)
    assert reference._selected_entry.trigger == ":continue"
    assert QApplication.clipboard().text() == "unchanged clipboard"


def test_refresh_reads_new_and_removed_live_templates_without_losing_scratchpad(qtbot):
    manager = TemplateManager()
    context = Template(
        name="Context", trigger=":ctx", content="Context", capability_id="context-reset"
    )
    manager.save(context)
    dialog = CommandsPopupDialog()
    qtbot.addWidget(dialog)
    _group(dialog, "carry-context")
    dialog._scratchpad.setPlainText("keep my draft")
    manager.save(Template(name="Local custom", trigger=":local", content="Custom"))
    context._path.unlink()
    dialog._refresh_btn.click()
    assert dialog._group_id == ""  # removed group has no live commands
    assert ":local" in _triggers(dialog)
    assert ":ctx" not in _triggers(dialog)
    assert dialog._scratchpad.toPlainText() == "keep my draft"
    _group(dialog, "custom")
    assert _triggers(dialog) == [":local"]


def test_switching_processes_repeatedly_keeps_the_diagram_alive(reference):
    reference._search_edit.setText("context")
    for _ in range(3):
        reference._view_combo.setCurrentText("Processes")
        assert not reference._search_edit.isEnabled()
        assert reference._workflow_panel.diagram().node_capabilities()
        reference._view_combo.setCurrentText("Browse")
        assert reference._search_edit.isEnabled()
        assert ":context" in _triggers(reference)


def test_window_preferences_preserve_other_local_changes_and_never_save_scratchpad(reference):
    external = Config()
    external.ui.theme_default_migrated = True
    external.ui.font_size = 17
    external.discovery.favorite_triggers = [":research"]
    external.discovery.recent_triggers = [":gaps"]
    save_config(external)
    reference._scratchpad.setPlainText("scratchpad-only-sentinel")
    reference.show()
    reference._pin_check.setChecked(False)
    assert reference.isVisible()
    assert not bool(reference.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
    reference.reject()
    loaded = load_config_fresh()
    assert loaded.ui.font_size == 17
    assert loaded.discovery.favorite_triggers == [":research"]
    assert loaded.discovery.recent_triggers == [":gaps"]
    assert loaded.discovery.stay_on_top is False
    assert loaded.discovery.window_geometry
    assert "scratchpad-only-sentinel" not in get_config_path().read_text(encoding="utf-8")


def test_reopen_restores_geometry_and_pin_but_starts_with_unfiltered_browse(qtbot):
    config = Config()
    config.ui.theme_default_migrated = True
    save_config(config)
    entries = [CommandCatalogEntry(":local", "Local", "Description", "Preview", "template")]
    first = CommandsPopupDialog(entries=entries)
    qtbot.addWidget(first)
    first.show()
    first.resize(740, 680)
    first.move(15, 25)
    first._pin_check.setChecked(False)
    first._search_edit.setText("local")
    size = first.size()
    first.reject()
    second = CommandsPopupDialog(entries=entries)
    qtbot.addWidget(second)
    assert second.size() == size
    assert second._pin_check.isChecked() is False
    assert second._view_combo.currentText() == "Browse"
    assert second._search_edit.text() == ""
    assert len(second._visible_entries()) == len(entries)
