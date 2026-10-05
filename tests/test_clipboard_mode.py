"""Clipboard choices and local tuning survive window, CLI, and sync sessions."""

import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml
from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication, QWidget

from espansr import __main__ as cli
from espansr.core.command_catalog import CommandCatalogEntry
from espansr.integrations import espanso
from espansr.ui.clipboard_mode import RemotePasteToggle


@pytest.fixture
def clipboard_config(tmp_path, monkeypatch):
    config_dir = tmp_path / "espanso"
    (config_dir / "config").mkdir(parents=True)
    monkeypatch.setattr(espanso, "get_espanso_config_dir", lambda: config_dir)
    return config_dir / "config" / "default.yml"


@pytest.mark.parametrize("remote", [False, True])
def test_auto_keeps_custom_clipboard_tuning_byte_for_byte(clipboard_config, remote):
    apply = espanso.apply_remote_desktop_config if remote else espanso.apply_workstation_config
    assert apply()
    text = clipboard_config.read_text(encoding="utf-8")
    text = text.replace("key_delay: 30", "key_delay: 65 # tuned for this host")
    text = text.replace("restore_clipboard_delay: 1500", "restore_clipboard_delay: 3500")
    clipboard_config.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    expected = clipboard_config.read_bytes()
    modified = clipboard_config.stat().st_mtime_ns
    with patch.object(espanso, "restart_espanso") as restart:
        for _ in range(2):
            assert cli.cmd_configure_remote_desktop(SimpleNamespace(auto=True)) == 0
        restart.assert_not_called()
    assert clipboard_config.read_bytes() == expected
    assert clipboard_config.stat().st_mtime_ns == modified


def test_auto_keeps_legacy_host_settings(clipboard_config):
    expected = (
        "# espansr-remote-desktop\nbackend: Clipboard\npreserve_clipboard: false\n"
        "key_delay: 70 # existing remote tuning\n"
    ).encode("utf-8")
    clipboard_config.write_bytes(expected)
    assert cli.cmd_configure_remote_desktop(SimpleNamespace(auto=True)) == 0
    assert clipboard_config.read_bytes() == expected


def test_auto_seeds_workstation_and_explicit_modes_reset_defaults(clipboard_config):
    assert cli.cmd_configure_remote_desktop(SimpleNamespace(auto=True)) == 0
    assert yaml.safe_load(clipboard_config.read_text())["preserve_clipboard"] is True
    assert cli.cmd_configure_remote_desktop(SimpleNamespace()) == 0
    assert yaml.safe_load(clipboard_config.read_text())["preserve_clipboard"] is False
    assert cli.cmd_configure_remote_desktop(SimpleNamespace(local=True)) == 0
    settings = yaml.safe_load(clipboard_config.read_text())
    assert settings["preserve_clipboard"] is True
    assert settings["restore_clipboard_delay"] == 1500


@pytest.mark.parametrize("remote", [False, True])
def test_switch_is_durable_and_does_not_touch_copied_text(qtbot, clipboard_config, remote):
    QApplication.clipboard().setText("Résumé 👋\nExisting copied text. ")
    switch = RemotePasteToggle()
    qtbot.addWidget(switch)
    switch.setChecked(True)
    switch.setChecked(remote)
    expected = clipboard_config.read_bytes()
    assert cli.cmd_configure_remote_desktop(SimpleNamespace(auto=True)) == 0
    reopened = RemotePasteToggle()
    qtbot.addWidget(reopened)
    assert reopened.isChecked() is remote
    assert clipboard_config.read_bytes() == expected
    assert QApplication.clipboard().text() == "Résumé 👋\nExisting copied text. "


def test_opening_and_activating_switch_only_reads_settings(qtbot, clipboard_config):
    assert espanso.apply_workstation_config()
    expected = clipboard_config.read_bytes()
    window = QWidget()
    qtbot.addWidget(window)
    switch = RemotePasteToggle(window)
    window.show()
    assert clipboard_config.read_bytes() == expected
    assert espanso.apply_remote_desktop_config()
    expected = clipboard_config.read_bytes()
    QApplication.sendEvent(window, QEvent(QEvent.Type.WindowActivate))
    assert switch.isChecked()
    assert clipboard_config.read_bytes() == expected


@pytest.mark.parametrize("failure", [False, OSError("file locked")])
def test_failed_switch_reflects_saved_mode_and_reports_error(qtbot, clipboard_config, failure):
    assert espanso.apply_workstation_config()
    expected = clipboard_config.read_bytes()
    switch = RemotePasteToggle()
    qtbot.addWidget(switch)
    kwargs = (
        {"side_effect": failure} if isinstance(failure, Exception) else {"return_value": failure}
    )
    with patch.object(espanso, "apply_remote_desktop_config", **kwargs):
        with qtbot.waitSignal(switch.status_message) as message:
            switch.setChecked(True)
    assert not switch.isChecked()
    assert "Could not change" in message.args[0]
    assert clipboard_config.read_bytes() == expected


def test_both_windows_keep_copy_actions_across_clipboard_modes(qtbot, clipboard_config):
    from espansr.ui.commands_popup import CommandsPopupDialog
    from espansr.ui.main_window import MainWindow

    entry = CommandCatalogEntry(
        ":copy-canary", "Copy canary", "", "", "template", content="Résumé 👋\nFull prompt. "
    )
    editor = MainWindow()
    reference = CommandsPopupDialog(entries=[entry])
    reference._show_all()
    reference._summary_table.setCurrentCell(0, 0)
    qtbot.addWidget(editor)
    qtbot.addWidget(reference)
    for remote in (True, False):
        editor._remote_paste_toggle.setChecked(remote)
        reference._remote_paste_toggle.refresh()
        assert reference._remote_paste_toggle.isChecked() is remote
        expected = clipboard_config.read_bytes()
        reference._detail_widget._copy_trigger_btn.click()
        qtbot.waitUntil(lambda: QApplication.clipboard().text() == entry.trigger, timeout=5000)
        reference._detail_widget._copy_prompt_btn.click()
        qtbot.waitUntil(lambda: QApplication.clipboard().text() == entry.content, timeout=5000)
        assert cli.cmd_configure_remote_desktop(SimpleNamespace(auto=True)) == 0
        editor._on_repo_sync_done(0)
        assert editor._remote_paste_toggle.isChecked() is remote
        assert clipboard_config.read_bytes() == expected


@pytest.mark.parametrize("runtime", [None, "C:/Espanso/espansod.exe"])
@pytest.mark.parametrize("remove_stale", [False, True])
def test_windows_publish_reports_failed_reload_when_runtime_is_installed(
    tmp_path, runtime, remove_stale
):
    from espansr.core.templates import TemplateManager

    templates = tmp_path / "templates"
    templates.mkdir()
    matches = tmp_path / "matches"
    matches.mkdir()
    output = matches / "espansr.yml"
    if remove_stale:
        output.write_text("matches:\n  - trigger: ':stale'\n    replace: stale\n", encoding="utf-8")
    else:
        (templates / "copy.json").write_text(
            json.dumps({"name": "Copy", "trigger": ":copy", "content": "Keep this text. "}),
            encoding="utf-8",
        )
    with (
        patch.object(espanso, "get_match_dir", return_value=matches),
        patch.object(espanso, "get_template_manager", return_value=TemplateManager(templates)),
        patch.object(espanso, "is_windows", return_value=True),
        patch.object(espanso, "is_wsl2", return_value=False),
        patch.object(espanso, "restart_espanso", return_value=False),
        patch.object(espanso, "_find_espanso_executable", return_value=runtime),
    ):
        assert espanso.sync_to_espanso(update_bundled=False) is (runtime is None)
    if remove_stale:
        assert not output.exists()
    else:
        assert yaml.safe_load(output.read_text())["matches"][0]["replace"] == "Keep this text. "
