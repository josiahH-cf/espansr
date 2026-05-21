"""Regression tests for the Windows PowerShell installer."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _installer_text() -> str:
    return (ROOT / "install.ps1").read_text(encoding="utf-8")


def test_windows_installer_uses_venv_python_for_pip_operations():
    text = _installer_text()

    assert '$VenvPython = Join-Path $VenvScripts "python.exe"' in text
    assert '$VenvConfig = Join-Path $VenvDir "pyvenv.cfg"' in text
    assert "& $VenvPython -m pip install --quiet --disable-pip-version-check --upgrade pip" in text
    assert "& $VenvPython -m pip install --quiet --disable-pip-version-check -e $ScriptDir" in text
    assert "& $VenvPip install" not in text


def test_windows_installer_recreates_incomplete_existing_venv():
    text = _installer_text()

    assert "Existing venv is incomplete - recreating $VenvDir" in text
    assert "Remove-Item -Recurse -Force $VenvDir" in text
    assert "(Test-Path $VenvConfig) -and (Test-Path $VenvPython)" in text


def test_windows_installer_polls_service_start_long_enough_to_settle():
    text = _installer_text()

    assert "for ($i = 0; $i -lt 10; $i++)" in text
    assert 'Warn "Espanso service start initiated - not reporting running yet"' in text


def test_windows_installer_prefers_espanso_daemon_for_service_output_capture():
    text = _installer_text()

    assert '$daemon = Join-Path $cmdDir "espansod.exe"' in text
    assert "return $daemon" in text
    assert "Programs\\Espanso\\espansod.exe" in text
    assert "Programs\\espanso\\espansod.exe" in text


def test_windows_installer_captures_espanso_service_output_inside_jobs():
    text = _installer_text()

    assert "& $Bin service check 2>&1 | Out-String" in text
    assert "& $Bin service register 2>&1 | Out-String" in text
    assert text.count("& $Bin service status 2>&1 | Out-String") == 2


def test_windows_installer_fails_when_setup_fails():
    text = _installer_text()

    assert "& $VenvCmd setup" in text
    assert (
        'Die "Post-install setup failed. Resolve the message above and rerun .\\install.ps1"'
        in text
    )
    assert 'Warn "Setup completed with warnings"' not in text


def test_windows_installer_persists_venv_scripts_to_user_path():
    text = _installer_text()

    assert "function Ensure-UserPathEntry" in text
    assert '[Environment]::GetEnvironmentVariable("PATH", "User")' in text
    assert '[Environment]::SetEnvironmentVariable("PATH", $newUserPath, "User")' in text
    assert "Ensure-UserPathEntry -PathEntry $VenvScripts" in text


def test_windows_installer_prints_missing_espanso_next_steps():
    text = _installer_text()

    assert "Espanso binary not found - startup registration skipped" in text
    assert "Install and start Espanso from https://espanso.org" in text
    assert "espansr setup" in text
    assert "espansr doctor" in text
