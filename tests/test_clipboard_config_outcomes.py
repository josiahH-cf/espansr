"""Clipboard settings: chosen values survive refresh, a delay changes only the
restore, and every outcome is reported as what it is.

Real default.yml files under tmp_path, through the public CLI handler, the
apply/revert helpers, and the GUI switch. Espanso never runs: restarts are the
autouse stub, a mock, or the real restart_espanso driving a fake ``espanso``
script on PATH. This is config-file evidence, not evidence of an expansion.
"""

import os
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from espansr import __main__ as cli
from espansr.integrations import espanso
from espansr.ui.clipboard_mode import RemotePasteToggle

# Taken before the autouse stub replaces it for each test.
REAL_RESTART = espanso.restart_espanso

needs_file_modes = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permission bits that apply to this user",
)

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
CHOICE = "# espansr-restore-delay: {} ms (chosen on this machine; Sync keeps it)"


@pytest.fixture
def config_dir(tmp_path, monkeypatch):
    root = tmp_path / "espanso"
    (root / "config").mkdir(parents=True)
    monkeypatch.setattr(espanso, "get_espanso_config_dir", lambda: root)
    return root


@pytest.fixture
def default_yml(config_dir):
    return config_dir / "config" / "default.yml"


def run(capsys, **flags):
    code = cli.cmd_configure_remote_desktop(SimpleNamespace(**flags))
    return code, capsys.readouterr().out


class read_only:
    """Make a directory (or file) unwritable for the duration of a block."""

    def __init__(self, path, mode=0o555):
        self.path, self.mode = path, mode

    def __enter__(self):
        self.saved = self.path.stat().st_mode & 0o777
        self.path.chmod(self.mode)

    def __exit__(self, *exc):
        self.path.chmod(self.saved)


# ─── An explicit choice survives refresh ─────────────────────────────────────


@pytest.mark.parametrize("flags", [{}, {"local": True}], ids=["host", "workstation"])
def test_a_chosen_never_restore_survives_repeated_auto(default_yml, capsys, flags):
    assert run(capsys, restore_delay=0, **flags)[0] == 0
    chosen = default_yml.read_bytes()
    assert yaml.safe_load(chosen)["preserve_clipboard"] is False
    with patch.object(espanso, "restart_espanso") as restart:
        runs = [run(capsys, auto=True) for _ in range(3)]  # install, Sync and refresh
        restart.assert_not_called()
    assert default_yml.read_bytes() == chosen
    assert [code for code, _ in runs] == [0, 0, 0]
    for _, out in runs:
        assert "Kept existing Espanso" in out and "(nothing changed)" in out
    for _ in range(2):
        change = espanso.upgrade_previous_default_config()
        assert (change.outcome, change.changed) == ("skipped", False)
    assert default_yml.read_bytes() == chosen


@pytest.mark.parametrize("origin", ["applied", "upgraded"])
def test_a_hand_made_opt_out_in_this_release_block_survives_auto(default_yml, capsys, origin):
    if origin == "applied":
        assert run(capsys)[0] == 0
    else:
        default_yml.write_text(EARLIER_HOST, encoding="utf-8")
        assert run(capsys, auto=True)[0] == 0
    text = default_yml.read_text(encoding="utf-8")
    assert "preserve_clipboard: true\n" in text  # this release's default
    text = text.replace("preserve_clipboard: true\n", "preserve_clipboard: false\n")
    text = text.replace("restore_clipboard_delay: 2000\n", "")
    default_yml.write_text(text, encoding="utf-8")
    opted_out = default_yml.read_bytes()
    # Byte for byte the block an earlier release wrote, except for the defaults line.
    assert espanso._block_settings(text.splitlines(True), "host") in (
        espanso._PREVIOUS_MODE_DEFAULTS["host"]
    )
    with patch.object(espanso, "restart_espanso") as restart:
        runs = [run(capsys, auto=True) for _ in range(2)]
    assert default_yml.read_bytes() == opted_out
    restart.assert_not_called()
    for code, out in runs:
        assert code == 0
        assert "Kept existing Espanso remote-desktop host settings (nothing changed)" in out


def test_an_untouched_earlier_block_is_upgraded_once_and_says_how_to_opt_out(default_yml, capsys):
    default_yml.write_text(EARLIER_HOST, encoding="utf-8")
    code, out = run(capsys, auto=True)
    assert code == 0
    assert (
        "[ok]   Updated untouched earlier Espanso remote-desktop host settings in default.yml "
        "(copied text is set to come back after 2 s)"
    ) in out
    assert "[ok]   Espanso restarted after the change and reports running." in out
    assert "'espansr configure-remote-desktop --auto --restore-delay 0'" in out
    upgraded = default_yml.read_bytes()
    assert b"# espansr-defaults: " in upgraded
    code, out = run(capsys, auto=True)
    assert code == 0 and "Kept existing" in out
    assert default_yml.read_bytes() == upgraded


# ─── A delay alone changes only the restore ──────────────────────────────────


def _customize(text: str, newline: str) -> str:
    text = text.replace("key_delay: 30\n", "key_delay: 65  # slower host\n")
    text = text.replace(
        "show_icon: false\n",
        "show_icon: false\n# my note inside the block\nclipboard_threshold: 99\n",
    )
    text = text.replace(
        "restore_clipboard_delay: 2000\n", "restore_clipboard_delay: 3500  # chat\n"
    )
    text = "# my top comment\n" + text + "word_separators: [' ', ',']  # after the block\n"
    return text.replace("\n", newline)


@pytest.mark.parametrize("newline", ["\n", "\r\n"], ids=["lf", "crlf"])
def test_a_delay_alone_changes_only_the_restore_lines_of_a_customized_block(
    default_yml, capsys, newline
):
    default_yml.write_text("backend: Inject\ntoggle_key: ALT\n", encoding="utf-8")
    assert run(capsys)[0] == 0
    default_yml.write_bytes(_customize(default_yml.read_text(encoding="utf-8"), newline).encode())
    before = default_yml.read_bytes().decode().split(newline)
    assert "# espansr-prev: backend: Inject" in before

    code, out = run(capsys, auto=True, restore_delay=2500)

    assert code == 0
    raw = default_yml.read_bytes()
    if newline == "\r\n":
        assert raw.count(b"\n") == raw.count(b"\r\n")
    after = raw.decode().split(newline)
    assert [line for line in after if line != CHOICE.format(2500)] == [
        "restore_clipboard_delay: 2500  # chat" if line.startswith("restore_clipboard") else line
        for line in before
    ]
    assert after.count(CHOICE.format(2500)) == 1
    assert "Saved Espanso remote-desktop host settings in default.yml" in out
    assert "(copied text is set to come back after 2.5 s)" in out


# The review's exact file: an indented comment right after preserve_clipboard.
COMMENTED_HOST = (
    "# outside head\n"
    "toggle_key: ALT\n"
    "# espansr-managed BEGIN (host) - reapply: espansr configure-remote-desktop; "
    "revert: espansr configure-remote-desktop --revert\n"
    "# espansr-defaults: 2026-11 (Sync and reinstall keep this block as it is)\n"
    "win32_exclude_orphan_events: false\n"
    "backend: Clipboard\n"
    "preserve_clipboard: true\n"
    "  # indented restore note\n"
    "restore_clipboard_delay: 2000\n"
    "show_icon: false\n"
    "# unrelated in-block note\n"
    "clipboard_threshold: 99\n"
    "show_notifications: false\n"
    "key_delay: 65  # tuned key delay\n"
    "backspace_delay: 30\n"
    "# espansr-managed END\n"
    "# outside tail\n"
)


def test_a_delay_alone_keeps_an_indented_comment_and_every_other_byte(default_yml, capsys):
    default_yml.write_text(COMMENTED_HOST, encoding="utf-8")

    code, out = run(capsys, auto=True, restore_delay=2500)

    assert code == 0, out
    expected = COMMENTED_HOST.replace(
        "restore_clipboard_delay: 2000\n", "restore_clipboard_delay: 2500\n"
    ).replace(
        "(Sync and reinstall keep this block as it is)\n",
        "(Sync and reinstall keep this block as it is)\n" + CHOICE.format(2500) + "\n",
    )
    assert default_yml.read_text(encoding="utf-8") == expected


def test_a_comment_after_an_empty_restore_value_still_counts_as_its_value(default_yml, capsys):
    """Only after a value on the key's own line is an indented comment just a comment."""
    text = COMMENTED_HOST.replace(
        "restore_clipboard_delay: 2000\n", "restore_clipboard_delay:\n  # 2000 below\n  2000\n"
    )
    default_yml.write_text(text, encoding="utf-8")

    assert run(capsys, auto=True, restore_delay=2500)[0] == 0

    settings = yaml.safe_load(default_yml.read_text(encoding="utf-8"))
    assert (settings["restore_clipboard_delay"], settings["key_delay"]) == (2500, 65)
    assert settings["clipboard_threshold"] == 99


def test_a_delay_alone_turns_the_restore_on_in_place(default_yml, capsys):
    assert run(capsys, local=True, restore_delay=0)[0] == 0
    text = default_yml.read_text(encoding="utf-8")
    text = text.replace("preserve_clipboard: false\n", "preserve_clipboard: false  # mine\n")
    text = "toggle_key: ALT\n" + text + "# trailing note\n"
    default_yml.write_text(text, encoding="utf-8")
    before = text.splitlines()

    assert run(capsys, auto=True, restore_delay=1800)[0] == 0

    after = default_yml.read_text(encoding="utf-8").splitlines()
    expected = []
    for line in before:
        if line == CHOICE.format(0):
            expected.append(CHOICE.format(1800))
        elif line.startswith("preserve_clipboard"):
            expected += ["preserve_clipboard: true  # mine", "restore_clipboard_delay: 1800"]
        else:
            expected.append(line)
    assert after == expected
    assert espanso.get_managed_default_config_mode() == "workstation"


def _without(text: str, *prefixes: str) -> str:
    return "".join(line for line in text.splitlines(True) if not line.startswith(prefixes))


_OUTSIDE = "restore_clipboard_delay: 900  # my own line\n"


@pytest.mark.parametrize(
    "shape",
    [
        lambda text: _without(text, "preserve_clipboard:"),
        lambda text: _without(text, "restore_clipboard_delay:"),
        lambda text: _without(text, "preserve_clipboard:", "restore_clipboard_delay:"),
        lambda text: _without(text, "# espansr-managed END"),
        lambda text: _without(text, "restore_clipboard_delay:") + _OUTSIDE,
        lambda text: text.replace(
            "restore_clipboard_delay: 2000", "restore_clipboard_delay:\n  2000"
        ),
    ],
    ids=["no-preserve", "no-delay", "neither", "no-end", "delay-outside", "multi-line"],
)
@pytest.mark.parametrize("delay", [0, 2500])
def test_a_delay_alone_leaves_exactly_one_restore_setting(default_yml, capsys, shape, delay):
    assert run(capsys)[0] == 0
    default_yml.write_text(shape(default_yml.read_text(encoding="utf-8")), encoding="utf-8")
    outside = _OUTSIDE in default_yml.read_text(encoding="utf-8")

    assert run(capsys, auto=True, restore_delay=delay)[0] == 0

    text = default_yml.read_text(encoding="utf-8")
    top_level = [line.split(":", 1)[0] for line in text.splitlines() if line[:1].isalpha()]
    assert top_level.count("preserve_clipboard") == 1
    # Never two restore keys; a user's own line outside the block stays unless
    # the new restore takes it over (then it is kept as an espansr-prev comment).
    assert top_level.count("restore_clipboard_delay") == (1 if delay or outside else 0)
    assert text.splitlines().count(CHOICE.format(delay)) == 1
    settings = yaml.safe_load(text)
    assert settings["preserve_clipboard"] is (delay > 0)
    if delay:
        assert settings["restore_clipboard_delay"] == delay
    if outside:
        own = _OUTSIDE.rstrip("\n")
        assert (own in text.splitlines()) is (delay == 0)
        assert (f"# espansr-prev: {own}" in text.splitlines()) is (delay > 0)
    assert (settings["backend"], settings["key_delay"]) == ("Clipboard", 30)
    assert espanso.get_managed_default_config_mode() == "host"


def test_a_delay_alone_keeps_the_tuning_of_a_legacy_file(default_yml, capsys):
    default_yml.write_text(
        "# espansr-remote-desktop\ntoggle_key: ALT\nwin32_exclude_orphan_events: false\n"
        "backend: Clipboard\npreserve_clipboard: false\nshow_icon: false\n"
        "show_notifications: false\nkey_delay: 70\nbackspace_delay: 45\n",
        encoding="utf-8",
    )
    assert run(capsys, auto=True, restore_delay=2000)[0] == 0
    settings = yaml.safe_load(default_yml.read_text(encoding="utf-8"))
    assert settings["toggle_key"] == "ALT"
    assert (settings["key_delay"], settings["backspace_delay"]) == (70, 45)
    assert (settings["preserve_clipboard"], settings["restore_clipboard_delay"]) == (True, 2000)
    assert espanso.get_managed_default_config_mode() == "host"


# ─── Failures are failures, through the public CLI ───────────────────────────


@needs_file_modes
@pytest.mark.parametrize(
    "flags",
    [{}, {"auto": True}, {"revert": True}, {"local": True}, {"auto": True, "restore_delay": 2500}],
    ids=["apply", "auto-upgrade", "revert", "local", "auto-delay"],
)
def test_a_write_that_fails_exits_1_says_so_and_leaves_the_file(default_yml, capsys, flags):
    default_yml.write_text(EARLIER_HOST, encoding="utf-8")
    before = default_yml.read_bytes()
    names = sorted(p.name for p in default_yml.parent.iterdir())
    with patch.object(espanso, "restart_espanso") as restart, read_only(default_yml.parent):
        code, out = run(capsys, **flags)
    assert code == 1
    assert "[ok]" not in out and "Kept existing" not in out
    assert default_yml.read_bytes() == before
    assert sorted(p.name for p in default_yml.parent.iterdir()) == names
    restart.assert_not_called()  # nothing changed, so nothing to reload
    assert f"[FAIL] Could not update {default_yml}: could not " in out
    assert "espansr left the file as it was; no setting changed." in out


@needs_file_modes
@pytest.mark.parametrize("flags", [{}, {"auto": True}, {"revert": True}])
def test_an_unreadable_default_yml_is_a_failure_not_a_kept_file(default_yml, capsys, flags):
    default_yml.write_text(EARLIER_HOST, encoding="utf-8")
    with read_only(default_yml, mode=0o000):
        code, out = run(capsys, **flags)
    assert code == 1
    assert "[ok]" not in out
    assert default_yml.read_text(encoding="utf-8") == EARLIER_HOST
    assert f"[FAIL] Could not update {default_yml}: could not read it (" in out


def test_no_espanso_configuration_is_a_failure(monkeypatch, capsys):
    monkeypatch.setattr(espanso, "get_espanso_config_dir", lambda: None)
    for flags in ({}, {"local": True}, {"auto": True}, {"revert": True}):
        code, out = run(capsys, **flags)
        assert code == 1
        assert "[FAIL] Could not update Espanso config (no Espanso configuration was found)." in out


# ─── Outcomes of the public helpers ──────────────────────────────────────────


@needs_file_modes
def test_apply_and_revert_report_failed_writes_and_no_restart(config_dir, default_yml):
    default_yml.write_text(EARLIER_HOST, encoding="utf-8")
    before = default_yml.read_bytes()
    espanso.take_config_change(), espanso.take_reload_result()
    with patch.object(espanso, "restart_espanso") as restart, read_only(default_yml.parent):
        for apply, kwargs in (
            (espanso.apply_remote_desktop_config, {}),
            (espanso.apply_remote_desktop_config, {"revert": True}),
            (espanso.apply_workstation_config, {}),
            (espanso.apply_remote_desktop_config, {"restore_delay": 0}),
        ):
            assert apply(config_dir=config_dir, **kwargs) is False
            change = espanso.take_config_change()
            assert change.outcome == "failed" and not change.ok and not change.changed
            assert change.error.startswith("could not write it (")
            assert change.reloaded is None and espanso.take_reload_result() is None
        restart.assert_not_called()
    assert default_yml.read_bytes() == before


def test_saved_outcomes_keep_the_file_and_the_restart_apart(config_dir, default_yml):
    with patch.object(espanso, "restart_espanso", return_value=False):
        assert espanso.apply_remote_desktop_config(config_dir=config_dir) is True
    change = espanso.take_config_change()
    assert (change.outcome, change.mode, change.changed, change.reloaded) == (
        "saved",
        "host",
        True,
        False,
    )
    assert espanso.take_config_change() is None  # reported once
    assert espanso.apply_remote_desktop_config(config_dir=config_dir, restart=False) is True
    change = espanso.take_config_change()
    assert (change.outcome, change.changed, change.reloaded) == ("saved", False, None)
    assert espanso.apply_remote_desktop_config(config_dir=config_dir, revert=True) is True
    assert espanso.take_config_change().changed is True
    assert espanso.apply_remote_desktop_config(config_dir=config_dir, revert=True) is True
    assert espanso.take_config_change().changed is False  # nothing left to revert
    change = espanso.configure_default_config("workstation", config_dir, restart=False)
    assert (change.outcome, change.mode, change.changed) == ("saved", "workstation", True)


@needs_file_modes
def test_upgrade_outcomes_are_skipped_saved_or_failed(config_dir, default_yml):
    assert espanso.upgrade_previous_default_config(config_dir).outcome == "skipped"  # no file
    default_yml.write_text(EARLIER_HOST, encoding="utf-8")
    with read_only(default_yml.parent):
        change = espanso.upgrade_previous_default_config(config_dir)
    assert (change.outcome, change.changed) == ("failed", False)
    assert change.error.startswith("could not write it (")
    assert default_yml.read_text(encoding="utf-8") == EARLIER_HOST
    change = espanso.upgrade_previous_default_config(config_dir, restart=False)
    assert (change.outcome, change.mode, change.changed) == ("saved", "host", True)
    change = espanso.upgrade_previous_default_config(config_dir, restart=False)
    assert (change.outcome, change.changed) == ("skipped", False)


# ─── The real restart path, with a fake espanso on PATH ──────────────────────


@pytest.fixture
def fake_espanso(tmp_path, monkeypatch):
    """Point the real restart_espanso at a scripted ``espanso`` (native, non-WSL path)."""
    if sys.platform == "win32":
        pytest.skip("the stand-in espanso is a POSIX shell script")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setattr(espanso, "is_wsl2", lambda: False)
    monkeypatch.setattr(espanso, "is_windows", lambda: False)
    monkeypatch.setattr(espanso, "restart_espanso", REAL_RESTART)
    monkeypatch.setattr(time, "sleep", lambda seconds: None)

    def install(restart_exit: int, status: str) -> None:
        script = bin_dir / "espanso"
        script.write_text(
            "#!/bin/sh\n"
            f'case "$1" in\n  restart) exit {restart_exit} ;;\n'
            f"  status) echo '{status}' ;;\nesac\n",
            encoding="utf-8",
        )
        script.chmod(0o755)

    return install


@pytest.mark.parametrize(
    ("restart_exit", "status", "why"),
    [
        (1, "espanso is running", "Espanso restart failed (exit 1)"),
        (0, "espanso is not running", "Espanso did not report running after the restart"),
    ],
    ids=["restart-fails", "never-reports-running"],
)
def test_a_failed_restart_is_reported_apart_from_the_saved_file(
    default_yml, capsys, fake_espanso, restart_exit, status, why
):
    fake_espanso(restart_exit, status)
    code, out = run(capsys)
    assert code == 0  # the file holds the requested settings
    assert yaml.safe_load(default_yml.read_text(encoding="utf-8"))["preserve_clipboard"] is True
    assert why in out  # restart_espanso's own reason
    assert "restarted after the change" not in out
    assert (
        "[ok]   Saved Espanso remote-desktop host settings in default.yml "
        "(copied text is set to come back after 2 s)"
    ) in out
    assert (
        "[warn] Espanso did not restart, so espansr cannot confirm it uses the saved settings"
    ) in out


def test_a_confirmed_restart_is_reported_as_such(default_yml, capsys, fake_espanso):
    fake_espanso(0, "espanso is running")
    code, out = run(capsys, local=True)
    assert code == 0
    assert "[ok]   Saved Espanso workstation settings in default.yml" in out
    assert "[ok]   Espanso restarted after the change and reports running." in out
    assert "[warn]" not in out


# ─── The GUI switch reports a real failed write ──────────────────────────────


@needs_file_modes
def test_a_switch_that_cannot_write_says_why_and_keeps_the_saved_mode(qtbot, default_yml):
    assert espanso.apply_workstation_config()
    before = default_yml.read_bytes()
    switch = RemotePasteToggle()
    qtbot.addWidget(switch)
    with read_only(default_yml.parent):
        with qtbot.waitSignal(switch.status_message) as message:
            switch.setChecked(True)
    assert not switch.isChecked()  # still the saved workstation mode
    assert message.args[0].startswith("Could not change clipboard mode (could not write it (")
    assert message.args[0].endswith("); default.yml was left as it was.")
    assert default_yml.read_bytes() == before
