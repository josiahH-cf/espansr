"""Espanso restart verification: return codes are checked and the daemon must
report running afterwards (``espansr.integrations.espanso.restart_espanso``
and ``_restart_espanso_wsl2``)."""

import subprocess
from unittest.mock import patch

from espansr.integrations import espanso

# The conftest autouse fixture replaces ``restart_espanso`` with a MagicMock for
# every test; capturing the real function at import time (before any fixture
# runs) lets these tests exercise the actual implementation.
_real_restart_espanso = espanso.restart_espanso


def _cp(argv, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(argv, returncode, stdout=stdout, stderr=stderr)


def _runner(restart_rc=0, status_outputs=("espanso is running\n",), status_rc=None):
    """Build a subprocess.run stand-in: restart returns ``restart_rc``, each
    status call pops the next entry of ``status_outputs``."""
    remaining = list(status_outputs)
    calls = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        command = " ".join(str(part) for part in argv)
        if "restart" in command and "status" not in command:
            return _cp(argv, restart_rc, stderr="boom" if restart_rc else "")
        output = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        rc = status_rc
        if rc is None:
            rc = 0 if espanso._output_reports_running(output) else 1
        return _cp(argv, rc, stdout=output)

    return fake_run, calls


def test_output_reports_running_rejects_negative_form():
    assert espanso._output_reports_running("espanso is running\n") is True
    assert espanso._output_reports_running("espanso is not running\n") is False
    assert espanso._output_reports_running("Warning: x\nespanso is running\n") is True
    assert espanso._output_reports_running("") is False


def test_restart_native_verifies_status(tmp_path):
    fake_run, calls = _runner()
    with (
        patch.object(espanso, "is_wsl2", return_value=False),
        patch.object(espanso, "is_windows", return_value=False),
        patch.object(espanso, "_find_espanso_executable", return_value="/usr/bin/espanso"),
        patch.object(espanso.subprocess, "run", side_effect=fake_run),
        patch("time.sleep"),
    ):
        assert _real_restart_espanso() is True

    assert calls[0] == ["/usr/bin/espanso", "restart"]
    assert calls[1] == ["/usr/bin/espanso", "status"]


def test_restart_native_polls_until_running(capsys):
    not_yet = "espanso is not running\n"
    fake_run, calls = _runner(status_outputs=(not_yet, not_yet, "espanso is running\n"))
    with (
        patch.object(espanso, "is_wsl2", return_value=False),
        patch.object(espanso, "is_windows", return_value=False),
        patch.object(espanso, "_find_espanso_executable", return_value="/usr/bin/espanso"),
        patch.object(espanso.subprocess, "run", side_effect=fake_run),
        patch("time.sleep") as sleep,
    ):
        assert _real_restart_espanso() is True

    assert [c for c in calls if c[-1] == "status"] == [["/usr/bin/espanso", "status"]] * 3
    assert sleep.call_count == 2


def test_restart_native_fails_on_nonzero_exit(capsys):
    fake_run, calls = _runner(restart_rc=2)
    with (
        patch.object(espanso, "is_wsl2", return_value=False),
        patch.object(espanso, "is_windows", return_value=False),
        patch.object(espanso, "_find_espanso_executable", return_value="/usr/bin/espanso"),
        patch.object(espanso.subprocess, "run", side_effect=fake_run),
        patch("time.sleep"),
    ):
        assert _real_restart_espanso() is False

    out = capsys.readouterr().out
    assert "Espanso restart failed (exit 2)" in out
    assert "boom" in out
    assert all(c[-1] != "status" for c in calls)  # no point verifying a failed launch


def test_restart_native_fails_when_status_never_reports_running(capsys):
    fake_run, calls = _runner(status_outputs=("espanso is not running\n",))
    with (
        patch.object(espanso, "is_wsl2", return_value=False),
        patch.object(espanso, "is_windows", return_value=False),
        patch.object(espanso, "_find_espanso_executable", return_value="/usr/bin/espanso"),
        patch.object(espanso.subprocess, "run", side_effect=fake_run),
        patch("time.sleep"),
    ):
        assert _real_restart_espanso() is False

    assert "did not report running" in capsys.readouterr().out
    assert len([c for c in calls if c[-1] == "status"]) == 5


def test_restart_returns_false_silently_without_executable(capsys):
    with (
        patch.object(espanso, "is_wsl2", return_value=False),
        patch.object(espanso, "_find_espanso_executable", return_value=None),
        patch.object(espanso.subprocess, "run") as run,
    ):
        assert _real_restart_espanso() is False
    run.assert_not_called()
    assert capsys.readouterr().out == ""


def test_restart_windows_hides_console_window():
    fake_run, _ = _runner()
    seen = {}

    def recording_run(argv, **kwargs):
        seen.update(kwargs)
        return fake_run(argv, **kwargs)

    with (
        patch.object(espanso, "is_wsl2", return_value=False),
        patch.object(espanso, "is_windows", return_value=True),
        patch.object(espanso, "_find_espanso_executable", return_value=r"C:\espanso\espanso.cmd"),
        patch.object(espanso.subprocess, "run", side_effect=recording_run),
        patch("time.sleep"),
    ):
        assert _real_restart_espanso() is True
    assert seen["creationflags"] == getattr(subprocess, "CREATE_NO_WINDOW", 0)


def test_restart_wsl2_uses_noprofile_and_verifies_status():
    fake_run, calls = _runner()
    with (
        patch.object(espanso, "is_wsl2", return_value=True),
        patch.object(espanso, "is_windows", return_value=False),
        patch.object(espanso.subprocess, "run", side_effect=fake_run),
        patch("time.sleep"),
    ):
        assert _real_restart_espanso() is True

    assert calls[0][:2] == ["powershell.exe", "-NoProfile"]
    assert "espanso restart" in calls[0][-1]
    assert calls[1] == espanso._WSL_STATUS_ARGV


def test_restart_wsl2_reports_failure(capsys):
    fake_run, calls = _runner(restart_rc=1)
    with (
        patch.object(espanso, "is_wsl2", return_value=True),
        patch.object(espanso, "is_windows", return_value=False),
        patch.object(espanso.subprocess, "run", side_effect=fake_run),
        patch("time.sleep"),
    ):
        assert _real_restart_espanso() is False
    assert "Windows PowerShell" in capsys.readouterr().out


def test_restart_handles_subprocess_errors(capsys):
    with (
        patch.object(espanso, "is_wsl2", return_value=True),
        patch.object(espanso, "is_windows", return_value=False),
        patch.object(
            espanso.subprocess, "run", side_effect=subprocess.TimeoutExpired("powershell.exe", 20)
        ),
    ):
        assert _real_restart_espanso() is False
    assert "Espanso restart failed" in capsys.readouterr().out


def test_restart_espanso_wsl2_helper_reports_success_only_when_running(capsys):
    fake_run, calls = _runner(status_outputs=("espanso is running\n",))
    with (
        patch.object(espanso, "is_windows", return_value=False),
        patch.object(espanso.subprocess, "run", side_effect=fake_run),
        patch("time.sleep"),
    ):
        espanso._restart_espanso_wsl2()
    assert "Espanso restarted successfully." in capsys.readouterr().out
    assert all(call[1] == "-NoProfile" for call in calls)
    assert calls[-1] == espanso._WSL_STATUS_ARGV


def test_restart_espanso_wsl2_helper_prints_note_when_not_running(capsys):
    fake_run, _ = _runner(status_outputs=("espanso is not running\n",))
    with (
        patch.object(espanso, "is_windows", return_value=False),
        patch.object(espanso.subprocess, "run", side_effect=fake_run),
        patch("time.sleep"),
    ):
        espanso._restart_espanso_wsl2()
    out = capsys.readouterr().out
    assert "restarted successfully" not in out
    assert "Run 'espanso restart' from Windows PowerShell" in out
