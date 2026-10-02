"""Tests for WSL Espanso install wrapper command."""

from unittest.mock import patch


def test_wsl_install_wrapper_fails_outside_wsl(capsys):
    """Command is WSL2-only and exits non-zero elsewhere."""
    from espansr.__main__ import cmd_wsl_install_espanso

    with patch("espansr.__main__.get_platform", return_value="linux"):
        code = cmd_wsl_install_espanso(None)

    out = capsys.readouterr().out
    assert code == 1
    assert "only supported" in out


def test_wsl_install_wrapper_uses_shared_verified_runtime_installer(capsys):
    """Native Windows and WSL must install and verify the same supported version."""
    from espansr.__main__ import cmd_wsl_install_espanso

    captured = {}

    def _fake_run(cmd, text, check):
        captured["cmd"] = cmd

        class _Result:
            returncode = 0

        return _Result()

    with (
        patch("espansr.__main__.get_platform", return_value="wsl2"),
        patch("subprocess.run", side_effect=_fake_run),
    ):
        code = cmd_wsl_install_espanso(None)

    out = capsys.readouterr().out
    assert code == 0
    assert "completed with verification" in out
    joined = " ".join(captured["cmd"])
    assert "powershell.exe" in captured["cmd"][0]
    assert "$espansoExe = Ensure-EspansoRuntime" in joined
    assert "Espanso-Win-Installer-x86_64.exe" in joined
    assert "Get-EspansoInstallerHash -Path" in joined
    assert "Get-EspansoRuntimeVersion -Executable $espansoExe" in joined
    assert "ACTION_REQUIRED" in joined


def test_wsl_install_wrapper_path_lag_returns_guidance(capsys):
    """PATH/session lag case returns warning guidance and non-zero."""
    from espansr.__main__ import cmd_wsl_install_espanso

    class _Result:
        returncode = 2

    with (
        patch("espansr.__main__.get_platform", return_value="wsl2"),
        patch("subprocess.run", return_value=_Result()),
    ):
        code = cmd_wsl_install_espanso(None)

    out = capsys.readouterr().out
    assert code == 1
    assert "ACTION REQUIRED" in out
    assert "Open a new PowerShell window" in out
    assert "espanso start" in out


def test_wsl_install_wrapper_reports_manual_exe_fallback(capsys):
    """Action-required output includes .exe installer fallback guidance."""
    from espansr.__main__ import cmd_wsl_install_espanso

    class _Result:
        returncode = 2

    with (
        patch("espansr.__main__.get_platform", return_value="wsl2"),
        patch("subprocess.run", return_value=_Result()),
    ):
        code = cmd_wsl_install_espanso(None)

    out = capsys.readouterr().out
    assert code == 1
    assert "complete the Espanso .exe wizard" in out
