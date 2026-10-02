"""Counters reflect snapshots in both views; copy actions do not increment."""

from PyQt6.QtWidgets import QApplication

from espansr.core.command_catalog import CommandCatalogEntry
from espansr.core.templates import Template
from espansr.core.usage import UsageSnapshot
from espansr.core.workflows import WorkflowCatalog
from espansr.ui.commands_popup import CommandsPopupDialog
from espansr.ui.template_editor import TemplateEditorWidget
from espansr.ui.usage_labels import UsageMonitor

REAL_START = UsageMonitor._start


def test_command_detail_shows_actual_count_and_copy_does_not_increment(qtbot):
    entry = CommandCatalogEntry(
        ":test", "Test", "", "", "template", capability_id="test", content="Hello "
    )
    dialog = CommandsPopupDialog(entries=[entry], workflow_catalog=WorkflowCatalog())
    qtbot.addWidget(dialog)
    dialog._usage_monitor._receive(
        UsageSnapshot(True, "Native expansions", {"template:test": 1234})
    )
    dialog._show_capability_command("test")
    label = dialog._detail_widget._usage_label
    assert label.text() == "Runs: 1,234"
    dialog._detail_widget._copy_prompt_btn.click()
    assert QApplication.clipboard().text() == "Hello "
    assert label.text() == "Runs: 1,234"
    dialog._usage_monitor._receive(UsageSnapshot(reason="Espanso 2.4+ required"))
    assert label.text() == "Runs: unavailable"
    assert "2.4" in label.toolTip()


def test_editor_count_follows_command_when_trigger_changes_and_clears_for_new(qtbot):
    editor = TemplateEditorWidget()
    qtbot.addWidget(editor)
    template = Template(name="Test", content="Hello", trigger=":old", capability_id="test")
    editor._usage_monitor._receive(UsageSnapshot(True, "Native expansions", {"template:test": 7}))
    editor.load_template(template)
    assert editor._usage_label.text() == "Runs: 7"
    template.trigger = ":new"
    editor.load_template(template)
    assert editor._usage_label.text() == "Runs: 7"
    editor.clear()
    assert editor._usage_label.isHidden()


def test_slow_usage_reader_does_not_block_copy(qtbot, monkeypatch):
    from threading import Event

    started = Event()
    finish = Event()

    def slow_reader(_entries, **_options):
        started.set()
        finish.wait(timeout=5)
        return UsageSnapshot(True, "Native expansions", {"template:test": 3})

    monkeypatch.setattr(UsageMonitor, "_start", REAL_START)
    monkeypatch.setattr("espansr.ui.usage_labels.refresh_usage", slow_reader)
    entry = CommandCatalogEntry(
        ":test", "Test", "", "", "template", capability_id="test", content="Copy while loading"
    )
    dialog = CommandsPopupDialog(entries=[entry], workflow_catalog=WorkflowCatalog())
    qtbot.addWidget(dialog)
    dialog._show_capability_command("test")
    try:
        qtbot.waitUntil(started.is_set)
        dialog._detail_widget._copy_prompt_btn.click()
        assert QApplication.clipboard().text() == "Copy while loading"
    finally:
        finish.set()
    qtbot.waitUntil(lambda: dialog._detail_widget._usage_label.text() == "Runs: 3")
