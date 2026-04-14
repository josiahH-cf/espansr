"""Tests for the :coms commands popup and shared trigger catalog."""

import argparse
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt

from espansr.core.command_catalog import COMMANDS_POPUP_TRIGGER, CommandCatalogEntry
from espansr.core.config import Config
from espansr.core.templates import TemplateManager


def test_build_command_catalog_includes_template_and_system_triggers(tmp_path):
    """Catalog includes template triggers plus built-in launcher and popup entries."""
    from espansr.core.command_catalog import build_command_catalog

    manager = TemplateManager(templates_dir=tmp_path / "templates")
    manager.create(
        name="Greeting",
        description="Friendly greeting",
        content="Hello {{name}}",
        trigger=":greet",
        variables=[{"name": "name", "label": "Name"}],
    )

    config = Config()
    config.espanso.launcher_trigger = ":launch"

    entries = build_command_catalog(template_manager=manager, config=config)

    triggers = [entry.trigger for entry in entries]
    assert triggers == sorted(triggers, key=str.lower)
    assert ":greet" in triggers
    assert ":launch" in triggers
    assert COMMANDS_POPUP_TRIGGER in triggers

    greeting = next(entry for entry in entries if entry.trigger == ":greet")
    assert greeting.description == "Friendly greeting"
    assert "Hello [Name]" in greeting.preview


def test_commands_popup_dialog_renders_entries(qtbot):
    """Dialog renders one standardized row widget per entry."""
    from espansr.ui.commands_popup import CommandRowWidget, CommandsPopupDialog

    entries = [
        CommandCatalogEntry(
            trigger=":alpha",
            name="Alpha",
            description="First command",
            preview="alpha output",
            source="template",
        ),
        CommandCatalogEntry(
            trigger=":beta",
            name="Beta",
            description="Second command",
            preview="beta output",
            source="system",
        ),
    ]

    with patch("espansr.ui.commands_popup.get_config", return_value=Config()):
        dialog = CommandsPopupDialog(entries=entries)
        qtbot.addWidget(dialog)

    assert dialog._list.count() == 2
    assert dialog._summary_table.rowCount() == 2
    assert dialog._summary_table.columnCount() == 2
    assert dialog._summary_table.horizontalHeaderItem(0).text() == "Command"
    assert dialog._summary_table.horizontalHeaderItem(1).text() == "Description"
    assert dialog._summary_table.item(0, 0).text() == ":alpha"
    assert dialog._summary_table.item(0, 1).text() == "First command"
    first_widget = dialog._list.itemWidget(dialog._list.item(0))
    assert isinstance(first_widget, CommandRowWidget)
    assert first_widget._trigger_label.text() == ":alpha"
    assert first_widget._preview_text.toPlainText() == "alpha output"


def test_commands_popup_dialog_closes_on_escape(qtbot):
    """Escape closes the commands popup immediately."""
    from espansr.ui.commands_popup import CommandsPopupDialog

    entries = [
        CommandCatalogEntry(
            trigger=":alpha",
            name="Alpha",
            description="First command",
            preview="alpha output",
            source="template",
        )
    ]

    with patch("espansr.ui.commands_popup.get_config", return_value=Config()):
        dialog = CommandsPopupDialog(entries=entries)
        qtbot.addWidget(dialog)

    dialog.show()
    assert dialog.isVisible()

    qtbot.keyClick(dialog, Qt.Key.Key_Escape)
    qtbot.waitUntil(lambda: not dialog.isVisible())


def test_cmd_gui_commands_view_launches_popup():
    """cmd_gui routes commands view to the popup launcher."""
    from espansr.__main__ import cmd_gui

    args = argparse.Namespace(view="commands")

    with (
        patch("espansr.__main__._auto_pull_if_configured"),
        patch("espansr.ui.commands_popup.launch_commands_popup") as mock_popup,
    ):
        result = cmd_gui(args)

    assert result == 0
    mock_popup.assert_called_once()


def test_cmd_gui_main_view_launches_editor():
    """cmd_gui preserves the default full-editor launch path."""
    from espansr.__main__ import cmd_gui

    args = argparse.Namespace(view="main")

    with (
        patch("espansr.__main__._auto_pull_if_configured"),
        patch("espansr.ui.main_window.launch") as mock_launch,
    ):
        result = cmd_gui(args)

    assert result == 0
    mock_launch.assert_called_once()


def test_launch_commands_popup_uses_dialog_exec_when_owning_app():
    """Standalone launch uses the dialog's own event loop so the popup stays open."""
    from espansr.ui.commands_popup import launch_commands_popup

    fake_dialog = MagicMock()
    fake_app = MagicMock()

    with (
        patch("espansr.ui.commands_popup.QApplication") as mock_app_cls,
        patch("espansr.ui.commands_popup.CommandsPopupDialog", return_value=fake_dialog),
    ):
        mock_app_cls.instance.return_value = None
        mock_app_cls.return_value = fake_app

        launch_commands_popup()

    fake_dialog.exec.assert_called_once()
    fake_dialog.show.assert_not_called()
