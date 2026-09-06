# install.ps1 - espansr installer for native Windows
#
# Supports: Windows 10/11 with PowerShell 5.1+ or PowerShell 7+
# Prerequisites: Python 3.11+ installed (on PATH or via the `py` launcher)
#
# Usage: .\install.ps1 [-RemoteDesktop | -LocalOnly]

#Requires -Version 5.1

param(
    [switch]$RemoteDesktop,
    [switch]$LocalOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvDir = Join-Path $ScriptDir ".venv"
$PythonMin = "3.11"

# Color helpers

function Info  { param([string]$Msg) Write-Host "[INFO] $Msg" -ForegroundColor Cyan }
function Ok    { param([string]$Msg) Write-Host "[ OK ] $Msg" -ForegroundColor Green }
function Warn  { param([string]$Msg) Write-Host "[WARN] $Msg" -ForegroundColor Yellow }
function Err   { param([string]$Msg) Write-Host "[ERR ] $Msg" -ForegroundColor Red }

function Die {
    param([string]$Msg)
    Err $Msg
    exit 1
}

if ($RemoteDesktop -and $LocalOnly) {
    Die "-RemoteDesktop and -LocalOnly are mutually exclusive: pass one machine role, or neither for auto."
}

# Python version check

function Test-InsideVenv {
    # A virtual-environment interpreter must never be the base interpreter:
    # the recreate branch below deletes $VenvDir before it is used, and a
    # venv-of-a-venv is not a supported layout.
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $true }
    $full = $Path
    try { $full = [System.IO.Path]::GetFullPath($Path) } catch { }
    if ($full -match '(?i)[\\/]\.venv[\\/]') { return $true }
    $venvRoot = $VenvDir.TrimEnd('\', '/')
    foreach ($separator in @('\', '/')) {
        if ($full.StartsWith($venvRoot + $separator, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }
    return $false
}

function Find-Python {
    $reqParts = $PythonMin -split "\."
    $reqMajor = [int]$reqParts[0]
    $reqMinor = [int]$reqParts[1]

    # Candidates in order: python / python3 on PATH, then the Windows launcher
    # (`py -3`), which finds a registered CPython even when PATH has none.
    $probes = @()
    foreach ($candidate in @("python", "python3")) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -eq $cmd) { continue }
        $probes += ,@($cmd.Source, @())
    }
    $launcher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $launcher) {
        $probes += ,@($launcher.Source, @("-3"))
    }

    foreach ($probe in $probes) {
        $exe = $probe[0]
        $probeArgs = $probe[1]
        try {
            # Resolve the real interpreter first (the launcher forwards to one).
            $resolved = & $exe @probeArgs -c "import sys; print(sys.executable)" 2>$null
            if (-not $resolved) { continue }
            $resolved = "$resolved".Trim()
            if (Test-InsideVenv -Path $resolved) { continue }

            $ver = & $resolved -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if (-not $ver) { continue }

            $parts = "$ver".Trim() -split "\."
            $major = [int]$parts[0]
            $minor = [int]$parts[1]

            if ($major -gt $reqMajor -or ($major -eq $reqMajor -and $minor -ge $reqMinor)) {
                return $resolved
            }
        }
        catch {
            continue
        }
    }

    return $null
}

function Find-Espanso {
    $cmd = Get-Command espanso -ErrorAction SilentlyContinue
    if ($null -ne $cmd) {
        $cmdDir = Split-Path -Parent $cmd.Source
        $daemon = Join-Path $cmdDir "espansod.exe"
        if (Test-Path $daemon) {
            return $daemon
        }
        return $cmd.Source
    }

    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Espanso\espansod.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Espanso\espanso.CMD"),
        (Join-Path $env:LOCALAPPDATA "Programs\Espanso\espanso.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\espanso\espansod.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\espanso\espanso.CMD"),
        (Join-Path $env:LOCALAPPDATA "Programs\espanso\espanso.exe"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\WindowsApps\espanso.exe")
    )

    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path $candidate)) {
            return $candidate
        }
    }

    return $null
}

# Run a command in a background job and wait up to $TimeoutSec seconds.
# Returns a PSCustomObject with Output (string), ExitCode (int), TimedOut (bool).
# ExitCode is the real $LASTEXITCODE of the native command the script block ran.
function Invoke-WithTimeout {
    param(
        [scriptblock]$ScriptBlock,
        [object[]]$ArgumentList = @(),
        [int]$TimeoutSec = 10
    )
    $job = Start-Job -ArgumentList (@($ScriptBlock.ToString()) + $ArgumentList) -ScriptBlock {
        $body = $args[0]
        $rest = @()
        if ($args.Count -gt 1) { $rest = $args[1..($args.Count - 1)] }
        $inner = [scriptblock]::Create($body)
        $global:LASTEXITCODE = 0
        $out = (& $inner @rest 2>&1 | Out-String)
        $code = $global:LASTEXITCODE
        if ($null -eq $code) { $code = 0 }
        [PSCustomObject]@{ Output = $out; ExitCode = [int]$code }
    }
    $finished = Wait-Job -Job $job -Timeout $TimeoutSec
    if ($null -eq $finished) {
        # Timed out - discard whatever arrived, then clean up
        Remove-Job -Job $job -Force
        return [PSCustomObject]@{ Output = ""; ExitCode = -1; TimedOut = $true }
    }
    $result = Receive-Job -Job $job 2>&1 | Where-Object { $_ -is [PSCustomObject] } | Select-Object -Last 1
    Remove-Job -Job $job -Force
    if ($null -eq $result) {
        return [PSCustomObject]@{ Output = ""; ExitCode = 1; TimedOut = $false }
    }
    return [PSCustomObject]@{ Output = [string]$result.Output; ExitCode = [int]$result.ExitCode; TimedOut = $false }
}

# Espanso prints "espanso is running" / "espanso is not running" and
# "espanso is registered ..." / "espanso is NOT registered ...", so a bare
# keyword match would accept the negative form. A line only counts when it
# carries the keyword and no "not".
function Test-PositiveServiceOutput {
    param([string]$Output, [string]$Keyword)
    foreach ($line in ($Output -split "`r?`n")) {
        if ($line -imatch $Keyword -and $line -inotmatch '\bnot\b') { return $true }
    }
    return $false
}

function Ensure-EspansoService {
    param([string]$EspansoBin)
    # $script:EspansoJustStarted is set in the outer scope so setup and the smoke test can add a grace period.

    # Registration check
    Info "Checking Espanso startup registration..."
    $checkResult = Invoke-WithTimeout -TimeoutSec 5 -ArgumentList $EspansoBin -ScriptBlock {
        param([string]$Bin)
        & $Bin service check 2>&1 | Out-String
    }
    if ($checkResult.TimedOut) {
        Warn "Espanso service check timed out - skipping registration step"
    }
    elseif ($checkResult.ExitCode -eq 0 -and (Test-PositiveServiceOutput -Output $checkResult.Output -Keyword 'registered')) {
        Ok "Espanso service registered for startup"
    }
    else {
        Info "Registering Espanso service for startup..."
        $regResult = Invoke-WithTimeout -TimeoutSec 10 -ArgumentList $EspansoBin -ScriptBlock {
            param([string]$Bin)
            & $Bin service register 2>&1 | Out-String
        }
        if ($regResult.TimedOut) {
            Warn "Espanso service register timed out - may need to run 'espanso service register' manually"
        }
        elseif ($regResult.ExitCode -eq 0) {
            Ok "Espanso service registered for startup"
        }
        else {
            Warn "Espanso service register failed (exit $($regResult.ExitCode)): $($regResult.Output.Trim())"
            Info "Run 'espanso service register' manually to start Espanso at login"
        }
    }

    # Status check
    $statusResult = Invoke-WithTimeout -TimeoutSec 5 -ArgumentList $EspansoBin -ScriptBlock {
        param([string]$Bin)
        & $Bin service status 2>&1 | Out-String
    }
    if (-not $statusResult.TimedOut -and $statusResult.ExitCode -eq 0 -and (Test-PositiveServiceOutput -Output $statusResult.Output -Keyword 'running')) {
        Ok "Espanso service running"
        return
    }

    # Fire-and-forget start + poll
    Info "Starting Espanso service..."
    Start-Process -FilePath $EspansoBin -ArgumentList "service", "start" -WindowStyle Hidden
    $script:EspansoJustStarted = $true

    $started = $false
    for ($i = 0; $i -lt 10; $i++) {
        Start-Sleep -Seconds 2
        $pollResult = Invoke-WithTimeout -TimeoutSec 5 -ArgumentList $EspansoBin -ScriptBlock {
            param([string]$Bin)
            & $Bin service status 2>&1 | Out-String
        }
        if (-not $pollResult.TimedOut -and $pollResult.ExitCode -eq 0 -and (Test-PositiveServiceOutput -Output $pollResult.Output -Keyword 'running')) {
            $started = $true
            break
        }
    }

    if ($started) {
        Ok "Espanso service started"
    }
    else {
        Warn "Espanso service start initiated - not reporting running yet"
    }
}

# PATH management
#
# The venv Scripts directory is never put on PATH: it would make python, pip,
# and pytest in every new shell resolve to the espansr venv. Instead a small
# launcher, %LOCALAPPDATA%\espansr\bin\espansr.cmd, forwards to the venv's
# espansr.exe and only that directory is appended to the user PATH. The user
# PATH is read and written through the registry so %VAR% entries survive.

function Get-UserPathRaw {
    try {
        $key = Get-Item -Path 'HKCU:\Environment' -ErrorAction Stop
        $value = $key.GetValue('Path', '', 'DoNotExpandEnvironmentNames')
        if ($null -eq $value) { return '' }
        return [string]$value
    }
    catch {
        return ''
    }
}

function Send-EnvironmentChange {
    # Tell Explorer the environment changed so new consoles see the new PATH
    # without a logoff. Best effort: without it the change applies at next logon.
    try {
        if (-not ('EspansrNative.Env' -as [type])) {
            Add-Type -Namespace EspansrNative -Name Env -MemberDefinition @'
[DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);
'@
        }
        $result = [UIntPtr]::Zero
        [void][EspansrNative.Env]::SendMessageTimeout([IntPtr]0xffff, 0x001A, [UIntPtr]::Zero, 'Environment', 2, 5000, [ref]$result)
    }
    catch {
        # Ignored: the registry value is already written.
    }
}

function Set-UserPathRaw {
    param([string]$Value)
    Set-ItemProperty -Path 'HKCU:\Environment' -Name 'Path' -Value $Value -Type ExpandString
    Send-EnvironmentChange
}

function Test-LegacyVenvScriptsEntry {
    # Older installers prepended <repo>\.venv\Scripts to the user PATH.
    param([string]$Entry)
    $trimmed = $Entry.TrimEnd('\', '/')
    if ($trimmed -ieq $VenvScripts.TrimEnd('\', '/')) { return $true }
    if ($trimmed -match '(?i)\\espansr\\\.venv\\Scripts$') { return $true }
    return $false
}

function Update-PathEntries {
    # Drop legacy venv Scripts entries and append the launcher directory at the END.
    param([string[]]$Entries)
    $kept = @()
    foreach ($entry in $Entries) {
        if ([string]::IsNullOrWhiteSpace($entry)) { continue }
        if (Test-LegacyVenvScriptsEntry -Entry $entry) { continue }
        if ($entry.TrimEnd('\', '/') -ieq $LauncherDir.TrimEnd('\', '/')) { continue }
        $kept += $entry
    }
    $kept += $LauncherDir
    return $kept
}

function Write-LauncherCmd {
    # Rewritten on every install so it always tracks the current venv path.
    param([string]$Path, [string]$Target)
    $content = "@`"$Target`" %*`r`n"
    $encoding = [System.Text.Encoding]::ASCII
    if ($content -match '[^\x00-\x7F]') {
        # cmd.exe reads batch files in the OEM code page.
        try {
            $oem = [System.Globalization.CultureInfo]::CurrentCulture.TextInfo.OEMCodePage
            $encoding = [System.Text.Encoding]::GetEncoding($oem)
        }
        catch {
            $encoding = [System.Text.Encoding]::Default
        }
    }
    [System.IO.File]::WriteAllText($Path, $content, $encoding)
}

function Ensure-UserPathEntry {
    try {
        $userPath = Get-UserPathRaw
        $entries = @()
        if (-not [string]::IsNullOrWhiteSpace($userPath)) {
            $entries = @($userPath -split ";")
        }
        $legacy = @($entries | Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and (Test-LegacyVenvScriptsEntry -Entry $_) })
        $newUserPath = ((Update-PathEntries -Entries $entries) -join ";")

        if ($newUserPath -eq $userPath) {
            Ok "Launcher directory already in Windows user PATH"
            return
        }

        Set-UserPathRaw -Value $newUserPath
        if ($legacy.Count -gt 0) {
            Ok "Removed legacy venv Scripts entry from Windows user PATH: $($legacy -join ', ')"
        }
        Ok "Appended $LauncherDir to Windows user PATH"
    }
    catch {
        Warn "Could not update Windows user PATH automatically: $($_.Exception.Message)"
        Info "To add it manually, run:"
        Write-Host ""
        Write-Host "  [Environment]::SetEnvironmentVariable('PATH', [Environment]::GetEnvironmentVariable('PATH', 'User') + `";$LauncherDir`", 'User')" -ForegroundColor White
        Write-Host ""
    }
}

Info "Platform: windows"
Info "Install target: native Windows PowerShell"
Info "Windows PowerShell and WSL are separate environments. This installer only configures Windows."

$PythonBin = Find-Python
if (-not $PythonBin) {
    Die "Python $PythonMin+ is required. Download from https://www.python.org/downloads/"
}

$pyVersion = & $PythonBin --version
Ok "Python: $pyVersion ($PythonBin)"

$VenvScripts = Join-Path $VenvDir "Scripts"
$VenvPython = Join-Path $VenvScripts "python.exe"
$VenvCmd = Join-Path $VenvScripts "espansr.exe"

$LocalAppData = $env:LOCALAPPDATA
if ([string]::IsNullOrWhiteSpace($LocalAppData)) {
    $LocalAppData = Join-Path $env:USERPROFILE "AppData\Local"
}
$LauncherDir = Join-Path $LocalAppData "espansr\bin"
$LauncherCmd = Join-Path $LauncherDir "espansr.cmd"

# Virtual environment

if (Test-Path $VenvDir) {
    $VenvConfig = Join-Path $VenvDir "pyvenv.cfg"
    $venvUsable = $false
    if ((Test-Path $VenvConfig) -and (Test-Path $VenvPython)) {
        # Probe the interpreter: a venv whose base Python moved or was removed
        # still has python.exe but cannot run anything.
        try {
            & $VenvPython -c "import sys" 2>$null
            $venvUsable = ($LASTEXITCODE -eq 0)
        }
        catch {
            $venvUsable = $false
        }
    }
    if ($venvUsable) {
        Info "Using existing venv: $VenvDir"
    }
    else {
        Warn "Existing venv is incomplete - recreating $VenvDir"
        Remove-Item -Recurse -Force $VenvDir
        Info "Creating virtual environment at $VenvDir..."
        & $PythonBin -m venv $VenvDir
        if ($LASTEXITCODE -ne 0) { Die "Failed to create virtual environment" }
        Ok "Venv created"
    }
}
else {
    Info "Creating virtual environment at $VenvDir..."
    & $PythonBin -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Die "Failed to create virtual environment" }
    Ok "Venv created"
}

Info "Upgrading pip..."
& $VenvPython -m pip install --quiet --disable-pip-version-check --upgrade pip
if ($LASTEXITCODE -ne 0) { Warn "pip upgrade failed - continuing with existing version" }

Info "Installing espansr..."
& $VenvPython -m pip install --quiet --disable-pip-version-check -e $ScriptDir
if ($LASTEXITCODE -ne 0) { Die "Package installation failed" }
Ok "Package installed"

# Espanso must be detected and running BEFORE setup: setup publishes the
# launcher, commands popup, sync trigger, and templates into Espanso's config
# directory, which only exists once Espanso has run at least once.

$EspansoBin = Find-Espanso
$EspansoFound = $null -ne $EspansoBin
$EspansoJustStarted = $false
if ($EspansoFound) {
    Ensure-EspansoService -EspansoBin $EspansoBin
}
else {
    Warn "Espanso binary not found - startup registration skipped"
}

if ($EspansoJustStarted) {
    Info "Waiting for Espanso service to settle..."
    Start-Sleep -Seconds 2
}

# Launcher + PATH setup (before setup so `espansr setup` reports the launcher state)

try {
    New-Item -ItemType Directory -Force -Path $LauncherDir | Out-Null
    Write-LauncherCmd -Path $LauncherCmd -Target $VenvCmd
    Ok "Launcher written: $LauncherCmd"
}
catch {
    Warn "Could not write the launcher at $LauncherCmd`: $($_.Exception.Message)"
}

$env:PATH = ((Update-PathEntries -Entries @($env:PATH -split ";")) -join ";")
Ok "Session PATH: launcher directory appended, legacy venv Scripts entries removed"

Ensure-UserPathEntry

Info "This updates the Windows user PATH only. WSL PATH and shell aliases are separate."
Info "Open a new terminal for persistent PATH changes to take effect."

# Post-install setup

Info "Running post-install setup..."
& $VenvCmd setup
if ($LASTEXITCODE -eq 0) {
    Ok "Setup complete"
}
else {
    Die "Post-install setup failed. Resolve the message above and rerun .\install.ps1"
}

# Record install metadata for `espansr refresh`
# Persist the platform, repository folder, installer, and venv so that
# `espansr refresh` can later rerun this PowerShell installer.
Info "Recording install metadata for 'espansr refresh'..."
& $VenvCmd record-install --installer install.ps1 --repo-dir $ScriptDir --venv-dir $VenvDir
if ($LASTEXITCODE -eq 0) {
    Ok "Install metadata recorded"
}
else {
    Warn "Could not record install metadata; 'espansr refresh' will fall back to auto-detection"
}

# Espanso backend is role-based and configured automatically. Default (--auto)
# applies the clipboard-preserving workstation tuning, unless this machine was
# declared a remote-desktop host (-RemoteDesktop), which stays sticky across
# reinstalls and `espansr refresh`. -LocalOnly forces workstation mode.
if ($RemoteDesktop) {
    Info "Configuring Espanso for remote-desktop HOST mode (clipboard backend)..."
    & $VenvCmd configure-remote-desktop
    if ($LASTEXITCODE -eq 0) {
        Ok "Espanso remote-desktop host config applied"
    }
    else {
        Warn "Could not apply remote-desktop Espanso config (continuing)"
    }
}
elseif ($LocalOnly) {
    Info "Tuning Espanso for local workstation use (clipboard preserved)..."
    & $VenvCmd configure-remote-desktop --local
    if ($LASTEXITCODE -eq 0) {
        Ok "Espanso workstation config applied (clipboard preserved)"
    }
    else {
        Warn "Could not apply local Espanso config (continuing)"
    }
}
else {
    Info "Configuring Espanso backend (auto: workstation unless a remote-desktop host)..."
    & $VenvCmd configure-remote-desktop --auto
    if ($LASTEXITCODE -eq 0) {
        Ok "Espanso backend configured"
    }
    else {
        Warn "Could not configure Espanso backend (continuing)"
    }
}

# Non-interactive resolution smoke test — confirms `espansr` is reachable in
# a fresh process that does not inherit our session PATH mutation. Mirrors
# the POSIX installer's non-interactive smoke and proves the persistent
# user-PATH entry (the launcher directory) works the same way RDP-spawned
# processes will see it.
Info "Verifying non-interactive command resolution..."
$resolveResult = Invoke-WithTimeout -TimeoutSec 5 -ScriptBlock {
    $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
    $machinePath = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    $env:PATH = "$userPath;$machinePath"
    Get-Command espansr -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}
if (-not $resolveResult.TimedOut -and -not [string]::IsNullOrWhiteSpace($resolveResult.Output)) {
    Ok "Non-interactive: 'espansr' resolves via persistent user PATH ($($resolveResult.Output.Trim()))"
}
else {
    Warn "Non-interactive: 'espansr' did not resolve via persistent user PATH"
    Info "Open a new terminal window or reboot, then rerun .\install.ps1 if needed"
}

if (-not $EspansoFound) {
    Info "Install and start Espanso from https://espanso.org, then run:"
    Write-Host "  espansr setup"
    Write-Host "  espansr doctor"
}

# Smoke test

Info "Running smoke test..."

& $VenvCmd list
if ($LASTEXITCODE -eq 0) {
    Ok "CLI: espansr list - OK"
}
else {
    Die "Smoke test failed: 'espansr list' exited non-zero"
}

& $VenvCmd status
if ($LASTEXITCODE -eq 0) {
    Ok "CLI: espansr status - OK"
}
else {
    Warn "espansr status returned non-zero (Espanso may not be installed)"
}

# Done

Write-Host ""
Write-Host "+================================================+" -ForegroundColor Green
Write-Host "|   espansr installed successfully!               |" -ForegroundColor Green
Write-Host "+================================================+" -ForegroundColor Green
Write-Host ""
Write-Host "  CLI:  espansr publish / status / list / doctor"
Write-Host "  GUI:  espansr gui"
Write-Host "  Bin:  $VenvCmd"
Write-Host "  Launcher: $LauncherCmd (on the user PATH)"
Write-Host "  Reinstall: espansr refresh"
Write-Host ""
