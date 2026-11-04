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
    settings = yaml.safe_load(clipboard_config.read_text())
    assert settings["backend"] == "Clipboard"
    assert settings["preserve_clipboard"] is True
    assert settings["restore_clipboard_delay"] == 2000
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


def test_a_saved_switch_never_claims_settings_espanso_did_not_load(qtbot, clipboard_config):
    switch = RemotePasteToggle()
    qtbot.addWidget(switch)
    with patch.object(espanso, "restart_espanso", return_value=False):
        with qtbot.waitSignal(switch.status_message) as message:
            switch.setChecked(True)
    assert switch.isChecked()  # saved
    assert message.args[0] == (
        "Remote paste settings saved, but Espanso did not restart, so espansr cannot confirm "
        "it uses them; restart Espanso."
    )
    assert "come back" not in message.args[0]


@pytest.mark.parametrize("revert", [False, True])
def test_cli_reports_a_saved_change_that_espanso_did_not_reload(clipboard_config, capsys, revert):
    assert espanso.apply_remote_desktop_config(restart=False)
    with patch.object(espanso, "restart_espanso", return_value=False):
        assert cli.cmd_configure_remote_desktop(SimpleNamespace(revert=revert)) == 0
    out = capsys.readouterr().out
    assert (
        "Reverted espansr's Espanso settings in default.yml"
        if revert
        else "Espanso remote-desktop host settings in default.yml already as requested "
        "(copied text is set to come back after 2 s)"
    ) in out
    assert "Espanso did not restart, so espansr cannot confirm it uses the saved settings" in out
    assert "restarted after the change" not in out


def test_reload_result_is_reported_once_per_write(clipboard_config):
    espanso.take_reload_result()
    assert espanso.apply_workstation_config(restart=False)
    assert espanso.take_reload_result() is None  # no restart was requested
    with patch.object(espanso, "restart_espanso", return_value=False):
        assert espanso.apply_workstation_config()
    assert espanso.take_reload_result() is False
    assert espanso.take_reload_result() is None  # taken, so never reported twice
    assert espanso.apply_remote_desktop_config(revert=True)
    assert espanso.take_reload_result() is True


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


# The block every earlier release wrote for host mode (it never restored).
EARLIER_HOST = (
    "toggle_key: ALT  # mine\n"
    "# espansr-managed BEGIN (host) - reapply: espansr configure-remote-desktop; "
    "revert: espansr configure-remote-desktop --revert\n"
    "# espansr-prev: backend: Inject\n"
    "win32_exclude_orphan_events: false\n"
    "backend: Clipboard\n"
    "preserve_clipboard: false\n"
    "show_icon: false\n"
    "show_notifications: false\n"
    "key_delay: 30\n"
    "backspace_delay: 30\n"
    "# espansr-managed END\n"
)


def test_auto_brings_an_untouched_earlier_host_block_back_to_restoring(clipboard_config):
    clipboard_config.write_text(EARLIER_HOST, encoding="utf-8")
    with patch.object(espanso, "restart_espanso") as restart:
        assert cli.cmd_configure_remote_desktop(SimpleNamespace(auto=True)) == 0
        restart.assert_called_once()
    text = clipboard_config.read_text(encoding="utf-8")
    settings = yaml.safe_load(text)
    assert settings["preserve_clipboard"] is True
    assert settings["restore_clipboard_delay"] == 2000
    assert settings["backend"] == "Clipboard"
    assert text.startswith("toggle_key: ALT  # mine\n# espansr-managed BEGIN (host)")
    assert "# espansr-prev: backend: Inject\n" in text
    assert espanso.get_managed_default_config_mode() == "host"
    assert espanso.apply_remote_desktop_config(revert=True, restart=False)
    assert (
        clipboard_config.read_text(encoding="utf-8") == "toggle_key: ALT  # mine\nbackend: Inject\n"
    )


@pytest.mark.parametrize(
    "tuned",
    [
        EARLIER_HOST.replace("key_delay: 30", "key_delay: 60"),  # tuned inside the block
        EARLIER_HOST + "restore_clipboard_delay: 4000\n",  # a line the new block would take
        "\ufeffrestore_clipboard_delay: 4000\n" + EARLIER_HOST,  # the same line after a BOM
    ],
    ids=["tuned-block", "user-restore-line", "user-restore-line-after-bom"],
)
def test_auto_keeps_an_earlier_host_block_tuned_on_this_machine(clipboard_config, tuned):
    clipboard_config.write_bytes(tuned.encode("utf-8"))
    with patch.object(espanso, "restart_espanso") as restart:
        assert cli.cmd_configure_remote_desktop(SimpleNamespace(auto=True)) == 0
        restart.assert_not_called()
    assert clipboard_config.read_bytes() == tuned.encode("utf-8")


def test_sync_keeps_a_never_restore_chosen_on_this_machine(clipboard_config):
    # Without a record of the choice, this block equals the earlier defaults.
    with patch.object(espanso, "restart_espanso") as restart:
        assert cli.cmd_configure_remote_desktop(SimpleNamespace(restore_delay=0)) == 0
        chosen = clipboard_config.read_bytes()
        assert cli.cmd_configure_remote_desktop(SimpleNamespace(auto=True)) == 0
        assert restart.call_count == 1
    assert clipboard_config.read_bytes() == chosen
    assert yaml.safe_load(chosen)["preserve_clipboard"] is False
    assert espanso.get_clipboard_restore_behavior()["chosen"] is True
    assert espanso.apply_remote_desktop_config(revert=True, restart=False)
    assert not clipboard_config.exists() or "espansr" not in clipboard_config.read_text()


def test_restore_delay_changes_only_the_restore_in_a_tuned_block(clipboard_config):
    assert espanso.apply_remote_desktop_config(restart=False)
    tuned = clipboard_config.read_text(encoding="utf-8").replace("key_delay: 30", "key_delay: 65")
    clipboard_config.write_text(tuned, encoding="utf-8")
    with patch.object(espanso, "restart_espanso"):
        flags = SimpleNamespace(auto=True, restore_delay=2500)
        assert cli.cmd_configure_remote_desktop(flags) == 0
    settings = yaml.safe_load(clipboard_config.read_text(encoding="utf-8"))
    assert (settings["key_delay"], settings["restore_clipboard_delay"]) == (65, 2500)
    assert settings["preserve_clipboard"] is True


# Files earlier releases wrote before the block layout: a first-line marker,
# then a YAML dump of the user's keys with espansr's merged in.
LEGACY_HOST_NEVER = (
    "# espansr-remote-desktop — managed by espansr; "
    "revert with: espansr configure-remote-desktop --revert\n"
    "toggle_key: ALT\nwin32_exclude_orphan_events: false\nbackend: Clipboard\n"
    "preserve_clipboard: false\nshow_icon: false\nshow_notifications: false\n"
    "key_delay: 30\nbackspace_delay: 30\n"
)
LEGACY_HOST_300MS = (
    "# espansr-remote-desktop — managed by espansr; "
    "revert with: espansr configure-remote-desktop --revert\n"
    "toggle_key: ALT\nbackend: Clipboard\nshow_icon: false\nshow_notifications: false\n"
    "key_delay: 30\nbackspace_delay: 30\n"
)
LEGACY_WORKSTATION_700MS = (
    "# espansr-workstation — managed by espansr; "
    "reapply with: espansr configure-remote-desktop --local\n"
    "toggle_key: ALT\nwin32_exclude_orphan_events: false\npreserve_clipboard: true\n"
    "restore_clipboard_delay: 700\n"
)


@pytest.mark.parametrize(
    ("legacy", "mode", "delay"),
    [
        (LEGACY_HOST_NEVER, "host", 2000),
        (LEGACY_HOST_300MS, "host", 2000),
        (LEGACY_WORKSTATION_700MS, "workstation", 1500),
    ],
    ids=["host-never-restored", "host-espanso-300ms", "workstation-700ms"],
)
def test_auto_brings_untouched_legacy_settings_up_to_date(clipboard_config, legacy, mode, delay):
    clipboard_config.write_text(legacy, encoding="utf-8")
    with patch.object(espanso, "restart_espanso") as restart:
        assert cli.cmd_configure_remote_desktop(SimpleNamespace(auto=True)) == 0
        restart.assert_called_once()
    text = clipboard_config.read_text(encoding="utf-8")
    assert text.startswith(f"toggle_key: ALT\n# espansr-managed BEGIN ({mode})")
    settings = yaml.safe_load(text)
    assert (settings["preserve_clipboard"], settings["restore_clipboard_delay"]) == (True, delay)
    assert "espansr-prev" not in text  # every legacy line was espansr's own
    assert espanso.apply_remote_desktop_config(revert=True, restart=False)
    assert clipboard_config.read_text(encoding="utf-8") == "toggle_key: ALT\n"


@pytest.mark.parametrize(
    "kept",
    [
        LEGACY_WORKSTATION_700MS.replace("700", "900"),  # tuned on this machine
        LEGACY_WORKSTATION_700MS.replace("700", "1500"),  # already today's behavior
        LEGACY_HOST_NEVER.replace("key_delay: 30", "key_delay: 70"),  # tuned host
    ],
    ids=["tuned-workstation", "current-workstation", "tuned-host"],
)
def test_auto_keeps_legacy_settings_that_are_not_an_earlier_default(clipboard_config, kept):
    clipboard_config.write_bytes(kept.encode("utf-8"))
    with patch.object(espanso, "restart_espanso") as restart:
        assert cli.cmd_configure_remote_desktop(SimpleNamespace(auto=True)) == 0
        restart.assert_not_called()
    assert clipboard_config.read_bytes() == kept.encode("utf-8")


def test_restore_delay_sets_or_disables_the_restore_per_machine(clipboard_config):
    def run(**flags):
        return cli.cmd_configure_remote_desktop(SimpleNamespace(**flags))

    def settings():
        return yaml.safe_load(clipboard_config.read_text(encoding="utf-8"))

    assert run(restore_delay=3000) == 0  # plain: host mode
    assert (settings()["backend"], settings()["restore_clipboard_delay"]) == ("Clipboard", 3000)
    assert run(local=True, restore_delay=0) == 0
    assert settings()["preserve_clipboard"] is False
    assert "restore_clipboard_delay" not in settings()
    assert run(auto=True, restore_delay=2500) == 0  # keeps the workstation mode
    assert espanso.get_managed_default_config_mode() == "workstation"
    assert (settings()["preserve_clipboard"], settings()["restore_clipboard_delay"]) == (True, 2500)
    tuned = clipboard_config.read_bytes()
    assert run(auto=True) == 0  # a tuned delay survives Sync and reinstall
    assert clipboard_config.read_bytes() == tuned


@pytest.mark.parametrize(
    "flags",
    [{"revert": True, "restore_delay": 100}, {"restore_delay": -1}, {"restore_delay": 10001}],
)
def test_restore_delay_rejects_revert_and_out_of_range_values(clipboard_config, flags, capsys):
    assert espanso.apply_workstation_config(restart=False)
    before = clipboard_config.read_bytes()
    assert cli.cmd_configure_remote_desktop(SimpleNamespace(**flags)) == 2
    assert clipboard_config.read_bytes() == before
    assert "--restore-delay cannot be used" in capsys.readouterr().out


def test_restore_delay_parses_with_each_mode_flag():
    parser = cli._build_parser()
    for argv in ([], ["--local"], ["--auto"]):
        args = parser.parse_args(["configure-remote-desktop", *argv, "--restore-delay", "1800"])
        assert args.restore_delay == 1800
    assert parser.parse_args(["configure-remote-desktop"]).restore_delay is None
    with pytest.raises(SystemExit):
        parser.parse_args(["configure-remote-desktop", "--restore-delay", "soon"])


@pytest.mark.parametrize(("remote", "seconds"), [(True, "2"), (False, "1.5")])
def test_switch_message_says_when_copied_text_returns(qtbot, clipboard_config, remote, seconds):
    start = espanso.apply_workstation_config if remote else espanso.apply_remote_desktop_config
    assert start(restart=False)
    switch = RemotePasteToggle()
    qtbot.addWidget(switch)
    assert switch.isChecked() is not remote
    with qtbot.waitSignal(switch.status_message) as message:
        switch.setChecked(remote)
    assert message.args[0] == (
        f"{'Remote' if remote else 'Workstation'} paste settings saved (copied text is set to "
        f"come back after {seconds} s); Espanso restarted and reports running."
    )
    assert "set to bring your copied text back 2 s after an expansion" in switch.toolTip()
    assert "set to bring it back after 1.5 s" in switch.toolTip()
    assert "pastes your copied text instead of the prompt" in switch.toolTip()
