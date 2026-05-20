"""Regression tests for the Windows PowerShell installer."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _installer_text() -> str:
    return (ROOT / "install.ps1").read_text(encoding="utf-8")


def test_windows_installer_uses_venv_python_for_pip_operations():
    text = _installer_text()

    assert '$VenvPython = Join-Path $VenvScripts "python.exe"' in text
    assert "& $VenvPython -m pip install --quiet --disable-pip-version-check --upgrade pip" in text
    assert "& $VenvPython -m pip install --quiet --disable-pip-version-check -e $ScriptDir" in text
    assert "& $VenvPip install" not in text


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
