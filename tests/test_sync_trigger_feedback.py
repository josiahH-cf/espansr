"""Feedback from the `:sync` trigger and `espansr refresh` stays visible:
Windows keeps the PowerShell window open, POSIX prefers a terminal emulator
and otherwise logs to sync.log with a notify-send, and the reinstall ``ok``
shows a Windows balloon notification."""

import shlex
from pathlib import Path
from unittest.mock import patch

import yaml

import espansr.__main__ as cli
from espansr.integrations import espanso


def _which(available: dict):
    """shutil.which stand-in returning paths only for the names in ``available``."""

    def fake(name):
        return available.get(name)

    return fake


def _sync_params(match_dir: Path) -> dict:
    return yaml.safe_load((match_dir / "espansr-sync.yml").read_text(encoding="utf-8"))["matches"][
        0
    ]["vars"][0]["params"]


# ─── Windows: PowerShell window that stays open ───────────────────────────────


def test_windows_sync_trigger_keeps_window_open(tmp_path):
    match_dir = tmp_path / "match"
    match_dir.mkdir()
    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        patch("espansr.integrations.espanso.is_windows", return_value=True),
        patch("shutil.which", return_value=r"C:\Program Files\espansr\espansr.exe"),
    ):
        assert espanso.generate_sync_file() is True

    params = _sync_params(match_dir)
    assert params["shell"] == "powershell"
    assert params["cmd"] == (
        "Start-Process -FilePath 'powershell' -ArgumentList '-NoProfile', '-NoExit', "
        "'-Command', '& ''C:\\Program Files\\espansr\\espansr.exe'' ''sync'''"
    )


def test_windows_console_launch_quotes_single_quotes_in_paths():
    params = espanso._build_windows_console_launch_params(r"C:\O'Brien\espansr.exe", ["sync"])
    assert "-NoExit" in params["cmd"]
    assert "''C:\\O''''Brien\\espansr.exe''" in params["cmd"]


def test_wsl_windows_host_sync_trigger_keeps_window_open(tmp_path):
    match_dir = tmp_path / "match"
    match_dir.mkdir()
    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.is_wsl2", return_value=True),
        patch("espansr.integrations.espanso._is_windows_side_wsl_path", return_value=True),
        patch("espansr.integrations.espanso.get_wsl_distro_name", return_value="Ubuntu"),
        patch("shutil.which", return_value="/home/user/.venv/bin/espansr"),
    ):
        assert espanso.generate_sync_file() is True

    cmd = _sync_params(match_dir)["cmd"]
    assert "-FilePath 'powershell'" in cmd
    assert "'-NoExit'" in cmd
    assert "''wsl.exe'' ''-d'' ''Ubuntu'' ''--'' ''/home/user/.venv/bin/espansr'' ''sync''" in cmd


def test_gui_triggers_still_launch_detached_without_noexit(tmp_path):
    match_dir = tmp_path / "match"
    match_dir.mkdir()
    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        patch("espansr.integrations.espanso.is_windows", return_value=True),
        patch("shutil.which", return_value=r"C:\espansr\espansr.exe"),
        patch("espansr.integrations.espanso._path_exists_safe", return_value=False),
    ):
        assert espanso.generate_launcher_file() is True
    cmd = yaml.safe_load((match_dir / "espansr-launcher.yml").read_text(encoding="utf-8"))[
        "matches"
    ][0]["vars"][0]["params"]["cmd"]
    assert "-NoExit" not in cmd


# ─── POSIX: terminal emulator, else log + notify-send ─────────────────────────


def _generate_posix_sync(tmp_path, available: dict, platform: str = "linux") -> str:
    match_dir = tmp_path / "match"
    match_dir.mkdir(parents=True)
    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        patch("espansr.integrations.espanso.is_windows", return_value=False),
        patch("espansr.integrations.espanso.get_platform", return_value=platform),
        patch("espansr.integrations.espanso.get_config_dir", return_value=tmp_path / "cfg"),
        patch("shutil.which", side_effect=_which({"espansr": "/usr/bin/espansr", **available})),
    ):
        assert espanso.generate_sync_file() is True
    params = _sync_params(match_dir)
    assert "shell" not in params
    return params["cmd"]


def test_posix_sync_prefers_x_terminal_emulator(tmp_path):
    cmd = _generate_posix_sync(
        tmp_path,
        {
            "x-terminal-emulator": "/usr/bin/x-terminal-emulator",
            "gnome-terminal": "/usr/bin/gnome-terminal",
            "notify-send": "/usr/bin/notify-send",
        },
    )
    assert cmd.startswith("nohup /usr/bin/x-terminal-emulator -e sh -c ")
    assert "/usr/bin/espansr sync; printf" in cmd
    assert "Press Enter to close this window" in cmd
    assert "read -r _" in cmd
    assert cmd.endswith(" >/dev/null 2>&1 &")
    assert "sync.log" not in cmd
    assert "notify-send" not in cmd


def test_posix_sync_uses_gnome_terminal_separator(tmp_path):
    cmd = _generate_posix_sync(tmp_path, {"gnome-terminal": "/usr/bin/gnome-terminal"})
    assert cmd.startswith("nohup /usr/bin/gnome-terminal -- sh -c ")


def test_posix_sync_falls_back_to_konsole_then_xterm(tmp_path):
    cmd = _generate_posix_sync(tmp_path, {"konsole": "/usr/bin/konsole", "xterm": "/usr/bin/xterm"})
    assert cmd.startswith("nohup /usr/bin/konsole -e sh -c ")
    cmd = _generate_posix_sync(tmp_path / "second", {"xterm": "/usr/bin/xterm"})
    assert cmd.startswith("nohup /usr/bin/xterm -e sh -c ")


def test_posix_sync_without_terminal_logs_and_notifies(tmp_path):
    cmd = _generate_posix_sync(tmp_path, {"notify-send": "/usr/bin/notify-send"})
    log = shlex.quote(str(tmp_path / "cfg" / "sync.log"))
    assert cmd.startswith("nohup sh -c ")
    # The inner script is itself shell-quoted; check it after unquoting.
    inner = shlex.split(cmd[len("nohup ") : -len(" >/dev/null 2>&1 &")])
    assert inner[:2] == ["sh", "-c"]
    script = inner[2]
    assert f"/usr/bin/espansr sync >>{log} 2>&1" in script
    assert 'notify-send espansr "sync ok"' in script
    assert f'notify-send espansr "sync failed (exit $rc), see "{log}' in script
    assert cmd.endswith(" >/dev/null 2>&1 &")


def test_posix_sync_without_terminal_or_notify_send_only_logs(tmp_path):
    cmd = _generate_posix_sync(tmp_path, {})
    assert "sync.log" in cmd
    assert "notify-send" not in cmd


def test_macos_sync_opens_terminal_via_osascript(tmp_path):
    cmd = _generate_posix_sync(tmp_path, {"xterm": "/opt/X11/bin/xterm"}, platform="macos")
    assert cmd.startswith("nohup osascript -e ")
    assert 'tell application "Terminal" to do script "/usr/bin/espansr sync"' in cmd
    assert 'tell application "Terminal" to activate' in cmd
    assert "xterm" not in cmd


def test_applescript_string_escapes_quotes_and_backslashes():
    assert espanso._applescript_string('a "b" \\c') == '"a \\"b\\" \\\\c"'


# ─── refresh ok notification ──────────────────────────────────────────────────


def test_notify_refresh_ok_shows_windows_balloon(capsys):
    with (
        patch.object(cli, "get_platform", return_value="windows"),
        patch.object(cli.subprocess, "Popen") as popen,
        patch.object(cli.subprocess, "run") as run,
    ):
        cli._notify_refresh_ok()

    assert "[ok]   ok" in capsys.readouterr().out
    run.assert_not_called()
    popen.assert_called_once()
    argv = popen.call_args.args[0]
    assert argv[0] == "powershell"
    assert "-NoProfile" in argv and "-NonInteractive" in argv
    script = argv[-1]
    assert "System.Windows.Forms.NotifyIcon" in script
    assert "ShowBalloonTip" in script
    assert "MessageBox" not in script
    assert popen.call_args.kwargs["stdout"] is cli.subprocess.DEVNULL


def test_notify_refresh_ok_windows_never_raises(capsys):
    with (
        patch.object(cli, "get_platform", return_value="windows"),
        patch.object(cli.subprocess, "Popen", side_effect=OSError("no powershell")),
    ):
        cli._notify_refresh_ok()
    assert "[ok]   ok" in capsys.readouterr().out


def test_notify_refresh_ok_linux_uses_notify_send_when_available():
    with (
        patch.object(cli, "get_platform", return_value="linux"),
        patch.object(cli.shutil, "which", return_value="/usr/bin/notify-send"),
        patch.object(cli.subprocess, "run") as run,
    ):
        cli._notify_refresh_ok()
    run.assert_called_once_with(["notify-send", "espansr", "ok"], check=False)
