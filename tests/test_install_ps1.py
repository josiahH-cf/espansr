"""Regression tests for the Windows PowerShell installer."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _installer_text() -> str:
    return (ROOT / "install.ps1").read_text(encoding="utf-8")


def test_windows_installer_records_install_metadata_for_refresh():
    text = _installer_text()

    assert (
        "& $VenvCmd record-install --installer install.ps1 "
        "--repo-dir $ScriptDir --venv-dir $VenvDir" in text
    )
    assert "espansr refresh" in text


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


def test_windows_installer_probes_existing_venv_interpreter():
    """A venv whose base Python moved still has python.exe; it must be probed."""
    text = _installer_text()

    assert '& $VenvPython -c "import sys"' in text
    assert "$venvUsable = ($LASTEXITCODE -eq 0)" in text
    assert text.index('& $VenvPython -c "import sys"') < text.index(
        "Existing venv is incomplete - recreating $VenvDir"
    )


def test_windows_installer_find_python_skips_venvs_and_tries_py_launcher():
    text = _installer_text()

    assert "function Test-InsideVenv" in text
    assert r"[\\/]\.venv[\\/]" in text
    assert "if (Test-InsideVenv -Path $resolved) { continue }" in text
    assert "Get-Command py -ErrorAction SilentlyContinue" in text
    assert '@("-3")' in text
    assert "import sys; print(sys.executable)" in text
    # python / python3 are probed before the launcher.
    assert text.index('@("python", "python3")') < text.index("Get-Command py ")


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


def test_windows_installer_writes_launcher_cmd_shim():
    """`espansr` reaches PATH through %LOCALAPPDATA%\\espansr\\bin\\espansr.cmd,
    rewritten on every install so it tracks the venv path."""
    text = _installer_text()

    assert '$LauncherDir = Join-Path $LocalAppData "espansr\\bin"' in text
    assert '$LauncherCmd = Join-Path $LauncherDir "espansr.cmd"' in text
    assert "New-Item -ItemType Directory -Force -Path $LauncherDir" in text
    assert "Write-LauncherCmd -Path $LauncherCmd -Target $VenvCmd" in text
    assert '$content = "@`"$Target`" %*`r`n"' in text


def test_windows_installer_never_puts_venv_scripts_on_path():
    """Putting .venv\\Scripts on PATH hijacks python/pip/pytest in every shell."""
    text = _installer_text()

    assert "Ensure-UserPathEntry -PathEntry $VenvScripts" not in text
    assert '$env:PATH = "$VenvScripts;$env:PATH"' not in text
    assert '[Environment]::SetEnvironmentVariable("PATH", $newUserPath, "User")' not in text
    assert "Ensure-UserPathEntry\n" in text  # called without a venv argument


def test_windows_installer_persists_launcher_dir_via_registry_appended():
    """The user PATH is read/written through the registry so %VAR% entries
    survive, and the launcher directory is appended, never prepended."""
    text = _installer_text()

    assert "function Ensure-UserPathEntry" in text
    assert "GetValue('Path', '', 'DoNotExpandEnvironmentNames')" in text
    assert (
        "Set-ItemProperty -Path 'HKCU:\\Environment' -Name 'Path' -Value $Value -Type ExpandString"
        in text
    )
    # Append at the end: the launcher dir is added after every kept entry.
    update = text[text.index("function Update-PathEntries") :]
    update = update[: update.index("\n}\n")]
    assert update.rstrip().endswith("$kept += $LauncherDir\n    return $kept")
    assert "$LauncherDir;" not in text


def test_windows_installer_removes_legacy_venv_scripts_path_entries():
    text = _installer_text()

    assert "function Test-LegacyVenvScriptsEntry" in text
    assert r"'(?i)\\espansr\\\.venv\\Scripts$'" in text
    assert "if (Test-LegacyVenvScriptsEntry -Entry $entry) { continue }" in text
    assert "Removed legacy venv Scripts entry from Windows user PATH" in text
    # The current session PATH is repaired the same way.
    assert '$env:PATH = ((Update-PathEntries -Entries @($env:PATH -split ";")) -join ";")' in text


def test_windows_installer_starts_espanso_before_setup():
    """Setup publishes into Espanso's config dir, which exists only once Espanso
    has run; detection and service start must therefore precede setup."""
    text = _installer_text()

    start_idx = text.index("Ensure-EspansoService -EspansoBin $EspansoBin")
    settle_idx = text.index("Waiting for Espanso service to settle")
    setup_idx = text.index("& $VenvCmd setup")
    assert start_idx < setup_idx
    assert settle_idx < setup_idx
    # The smoke tests still run after setup.
    assert setup_idx < text.index("Running smoke test...")


def test_windows_installer_service_detection_excludes_negative_output():
    """'espanso is not running' / 'NOT registered' must not read as positive."""
    text = _installer_text()

    assert "function Test-PositiveServiceOutput" in text
    assert r"-inotmatch '\bnot\b'" in text
    assert "Test-PositiveServiceOutput -Output $checkResult.Output -Keyword 'registered'" in text
    assert "Test-PositiveServiceOutput -Output $statusResult.Output -Keyword 'running'" in text
    assert "Test-PositiveServiceOutput -Output $pollResult.Output -Keyword 'running'" in text
    assert '-match "registered"' not in text
    assert '-match "running"' not in text


def test_windows_installer_timeout_wrapper_returns_real_exit_code():
    text = _installer_text()

    assert "$global:LASTEXITCODE" in text
    assert "ExitCode = [int]$code" in text
    assert "ExitCode = 0; TimedOut = $false" not in text
    assert "$checkResult.ExitCode -eq 0" in text
    assert "$statusResult.ExitCode -eq 0" in text
    assert "$pollResult.ExitCode -eq 0" in text


def test_windows_installer_checks_service_register_result():
    text = _installer_text()

    assert "elseif ($regResult.ExitCode -eq 0)" in text
    assert "Espanso service register failed (exit $($regResult.ExitCode))" in text


def test_windows_installer_rejects_conflicting_role_flags():
    text = _installer_text()

    assert "if ($RemoteDesktop -and $LocalOnly)" in text
    assert 'Die "-RemoteDesktop and -LocalOnly are mutually exclusive' in text
    guard_idx = text.index("if ($RemoteDesktop -and $LocalOnly)")
    assert guard_idx < text.index("$PythonBin = Find-Python")


def test_windows_installer_prints_missing_espanso_next_steps():
    text = _installer_text()

    assert "Espanso binary not found - startup registration skipped" in text
    assert "Install and start Espanso from https://espanso.org" in text
    assert "espansr setup" in text
    assert "espansr doctor" in text


def test_windows_installer_runs_non_interactive_resolution_smoke():
    """Symmetry with install.sh: prove the persistent user-PATH entry (the
    launcher directory) is reachable from a fresh process, the way RDP-spawned
    processes will see it.
    """
    text = _installer_text()

    assert "Verifying non-interactive command resolution" in text
    assert '[Environment]::GetEnvironmentVariable("PATH", "User")' in text
    assert "Get-Command espansr" in text
    assert "Non-interactive: 'espansr' resolves via persistent user PATH" in text
    # The smoke runs after the launcher dir was persisted.
    assert text.index("Ensure-UserPathEntry\n") < text.index(
        "Verifying non-interactive command resolution"
    )


def test_windows_installer_configures_espanso_backend_by_role():
    """install.ps1 configures the Espanso backend by machine role, automatically.

    Default (--auto) applies the workstation tuning unless the machine is a
    declared remote-desktop host; -RemoteDesktop and -LocalOnly force a role.
    Runs after record-install so a failure never blocks `espansr refresh`.
    """
    text = _installer_text()

    assert "[switch]$RemoteDesktop" in text
    assert "[switch]$LocalOnly" in text
    assert "if ($RemoteDesktop)" in text
    assert "& $VenvCmd configure-remote-desktop --auto" in text
    assert "& $VenvCmd configure-remote-desktop --local" in text
    assert text.index("record-install") < text.index("configure-remote-desktop")
