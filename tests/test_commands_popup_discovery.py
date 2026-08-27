"""GUI acceptance checks for :coms discovery (ARCH-08, BEH-05/06/07/16/17).

The popup gains a fuzzy search field, artifact selectors, and view switching
(All Commands / Recommended / Processes / Recent / Favorites) while keeping the
complete catalog, previews, scratchpad, and escape behavior intact. Nothing in
the popup executes prompts, shells, models, installers, syncs, or network
actions — selection only ever changes what is displayed or copies text.
"""

from unittest.mock import patch

import pytest

from espansr.core.command_catalog import CommandCatalogEntry
from espansr.core.config import Config
from espansr.core.workflows import WorkflowCatalog, WorkflowEdge, WorkflowManifest, WorkflowNode

pytest.importorskip("PyQt6")


def _entries():
    return [
        CommandCatalogEntry(
            trigger=":research",
            name="Research Report",
            description="research a topic with strong evidence handling",
            preview="You are research...",
            source="template",
            category="analysis",
            stage="research-report",
            capability_id="research-report",
            intent_tags=("research a question", "gather evidence"),
            accepts=("research-question", "rough-intent"),
            produces=("evidence-report",),
            use_when="You need evidence gathered.",
            avoid_when="The evidence already exists.",
            workflows=("evidence-research-cycle",),
            workflow_next=((":gaps", "Challenge the findings independently."),),
            content="You are research, full prompt body.",
        ),
        CommandCatalogEntry(
            trigger=":gaps",
            name="Gap Review",
            description="critical review modes for gaps",
            preview="You are gaps...",
            source="template",
            category="analysis",
            stage="gap-review",
            capability_id="gap-review",
            intent_tags=(
                "challenge completed research",
                "critical review",
                "review already complete work",
            ),
            accepts=("evidence-report",),
            produces=("gap-review",),
            use_when="You have finished material to challenge.",
            avoid_when="Nothing exists to review yet.",
            workflows=("evidence-research-cycle",),
            content="You are gaps, full prompt body.",
        ),
        CommandCatalogEntry(
            trigger=":coms",
            name="Command Reference",
            description="Show a quick popup of triggers.",
            preview="Opens a popup.",
            source="system",
            category="system",
            stage="reference",
        ),
    ]


def _workflow_catalog():
    return WorkflowCatalog(
        workflows=[
            WorkflowManifest(
                id="evidence-research-cycle",
                name="Evidence Research, Challenge, and Presentation",
                description="Research, challenge, present.",
                entry_points=["research-report", "gap-review"],
                nodes=[
                    WorkflowNode(capability="research-report"),
                    WorkflowNode(capability="gap-review"),
                ],
                edges=[
                    WorkflowEdge(
                        source="research-report",
                        target="gap-review",
                        label="Challenge the findings independently.",
                    )
                ],
            )
        ]
    )


def _make_dialog(qtbot, entries=None, config=None):
    from espansr.ui.commands_popup import CommandsPopupDialog

    config = config or Config()
    with (
        patch("espansr.ui.commands_popup.get_config", return_value=config),
        patch("espansr.ui.commands_popup.save_config", return_value=True),
    ):
        dialog = CommandsPopupDialog(
            entries=entries if entries is not None else _entries(),
            workflow_catalog=_workflow_catalog(),
        )
    qtbot.addWidget(dialog)
    return dialog


# ── Full catalog stays the default (BEH-07) ──────────────────────────────────


def test_popup_defaults_to_full_catalog(qtbot):
    dialog = _make_dialog(qtbot)
    assert dialog._view_combo.currentText() == "All Commands"
    assert dialog._list.count() == 3
    assert dialog._summary_table.rowCount() == 3


def test_popup_view_choices(qtbot):
    dialog = _make_dialog(qtbot)
    views = [dialog._view_combo.itemText(i) for i in range(dialog._view_combo.count())]
    assert views == ["All Commands", "Recommended", "Processes", "Recent", "Favorites"]


def test_scratchpad_still_present_and_ephemeral(qtbot):
    dialog = _make_dialog(qtbot)
    dialog._scratchpad.setPlainText("throwaway text")
    assert dialog._scratchpad.toPlainText() == "throwaway text"
    assert not dialog._scratchpad.isReadOnly()


# ── Fuzzy search (BEH-05) ────────────────────────────────────────────────────


def test_search_filters_to_matching_capabilities(qtbot):
    dialog = _make_dialog(qtbot)
    dialog._search_edit.setText("challenge research that is already complete")
    visible = [e.trigger for e in dialog._visible_entries()]
    assert visible[0] == ":gaps"
    dialog._search_edit.setText("")
    assert len(dialog._visible_entries()) == 3


# ── Artifact selectors (BEH-06) ──────────────────────────────────────────────


def test_artifact_selectors_surface_compatible_capability(qtbot):
    dialog = _make_dialog(qtbot)
    dialog._have_combo.setCurrentText("evidence-report")
    dialog._want_combo.setCurrentText("gap-review")
    visible = [e.trigger for e in dialog._visible_entries()]
    assert visible[0] == ":gaps"


def test_clearing_selectors_restores_full_catalog(qtbot):
    dialog = _make_dialog(qtbot)
    dialog._have_combo.setCurrentText("evidence-report")
    dialog._have_combo.setCurrentText("")
    assert len(dialog._visible_entries()) == 3


# ── Card metadata (use_when / avoid_when / process info) ─────────────────────


def test_row_widget_shows_guidance_and_process_info(qtbot):
    from espansr.ui.commands_popup import CommandRowWidget

    entry = _entries()[0]
    widget = CommandRowWidget(entry)
    qtbot.addWidget(widget)
    assert "You need evidence gathered." in widget._use_when_label.text()
    assert "The evidence already exists." in widget._avoid_when_label.text()
    assert widget._use_when_label.isVisibleTo(widget)
    assert "evidence-research-cycle" in widget._process_label.text()
    assert ":gaps" in widget._process_label.text()


def test_row_widget_hides_empty_guidance(qtbot):
    from espansr.ui.commands_popup import CommandRowWidget

    entry = _entries()[2]  # system entry with no metadata
    widget = CommandRowWidget(entry)
    qtbot.addWidget(widget)
    assert not widget._use_when_label.isVisibleTo(widget)
    assert not widget._avoid_when_label.isVisibleTo(widget)
    assert not widget._process_label.isVisibleTo(widget)


# ── Direct actions (BEH-16: display and copy only) ───────────────────────────


def test_copy_trigger_action_copies_to_clipboard(qtbot):
    from PyQt6.QtWidgets import QApplication

    dialog = _make_dialog(qtbot)
    entry = _entries()[0]
    with (
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
    ):
        dialog._copy_trigger(entry)
    assert QApplication.clipboard().text() == ":research"


def test_copy_prompt_action_copies_full_content(qtbot):
    from PyQt6.QtWidgets import QApplication

    dialog = _make_dialog(qtbot)
    entry = _entries()[0]
    with (
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
    ):
        dialog._copy_prompt(entry)
    assert QApplication.clipboard().text() == "You are research, full prompt body."


def test_send_to_scratchpad_places_trigger(qtbot):
    dialog = _make_dialog(qtbot)
    entry = _entries()[0]
    with (
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
    ):
        dialog._send_to_scratchpad(entry)
    assert ":research" in dialog._scratchpad.toPlainText()


def test_row_widget_exposes_action_buttons(qtbot):
    from espansr.ui.commands_popup import CommandRowWidget

    widget = CommandRowWidget(_entries()[0])
    qtbot.addWidget(widget)
    for name in ("_copy_trigger_btn", "_copy_prompt_btn", "_scratchpad_btn", "_packet_btn"):
        assert hasattr(widget, name), name


def test_popup_actions_never_execute_processes(qtbot):
    """BEH-16: no popup action shells out, syncs, or launches another prompt."""
    import subprocess

    dialog = _make_dialog(qtbot)
    entry = _entries()[0]
    with (
        patch.object(subprocess, "run") as run_mock,
        patch.object(subprocess, "Popen") as popen_mock,
        patch("espansr.ui.commands_popup.save_config", return_value=True),
    ):
        dialog._copy_trigger(entry)
        dialog._send_to_scratchpad(entry)
        dialog._search_edit.setText("research")
        dialog._have_combo.setCurrentText("evidence-report")
        dialog._view_combo.setCurrentText("Recommended")
    run_mock.assert_not_called()
    popen_mock.assert_not_called()


# ── Favorites and recents ────────────────────────────────────────────────────


def test_favorite_toggle_persists_to_config(qtbot):
    config = Config()
    dialog = _make_dialog(qtbot, config=config)
    with patch("espansr.ui.commands_popup.save_config", return_value=True) as save_mock:
        dialog._toggle_favorite(":research")
    assert ":research" in config.discovery.favorite_triggers
    save_mock.assert_called()
    with (
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
    ):
        dialog._toggle_favorite(":research")
    assert ":research" not in config.discovery.favorite_triggers


def test_copy_records_recent_usage(qtbot):
    config = Config()
    dialog = _make_dialog(qtbot, config=config)
    with (
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
    ):
        dialog._copy_trigger(_entries()[0])
    assert config.discovery.recent_triggers[0] == ":research"


def test_recent_view_lists_recent_triggers(qtbot):
    config = Config()
    config.discovery.recent_triggers = [":gaps"]
    dialog = _make_dialog(qtbot, config=config)
    dialog._view_combo.setCurrentText("Recent")
    assert [e.trigger for e in dialog._visible_entries()] == [":gaps"]


def test_favorites_view_lists_favorites(qtbot):
    config = Config()
    config.discovery.favorite_triggers = [":research"]
    dialog = _make_dialog(qtbot, config=config)
    dialog._view_combo.setCurrentText("Favorites")
    assert [e.trigger for e in dialog._visible_entries()] == [":research"]


# ── Processes view ───────────────────────────────────────────────────────────


def test_processes_view_shows_workflow_information(qtbot):
    dialog = _make_dialog(qtbot)
    dialog._view_combo.setCurrentText("Processes")
    assert dialog._list.count() >= 1
    # The summary table shows the workflow rather than commands in this view.
    texts = [
        dialog._summary_table.item(row, 0).text() for row in range(dialog._summary_table.rowCount())
    ]
    assert any("evidence-research-cycle" in t for t in texts)


# ── Preserved behavior ───────────────────────────────────────────────────────


def test_escape_still_closes_dialog(qtbot):
    from PyQt6.QtCore import Qt

    dialog = _make_dialog(qtbot)
    dialog.show()
    qtbot.keyClick(dialog, Qt.Key.Key_Escape)
    qtbot.waitUntil(lambda: not dialog.isVisible())


def test_all_commands_view_keeps_three_column_summary(qtbot):
    dialog = _make_dialog(qtbot)
    assert dialog._summary_table.columnCount() == 3
    headers = [dialog._summary_table.horizontalHeaderItem(i).text() for i in range(3)]
    assert headers == ["Command", "Workflow", "Description"]
