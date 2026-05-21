# install.ps1 - espansr installer for native Windows
#
# Supports: Windows 10/11 with PowerShell 5.1+ or PowerShell 7+
# Prerequisites: Python 3.11+ installed and in PATH
#
# Usage: .\install.ps1

#Requires -Version 5.1

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

# Python version check

function Find-Python {
    $candidates = @("python", "python3")
    $reqParts = $PythonMin -split "\."
    $reqMajor = [int]$reqParts[0]
    $reqMinor = [int]$reqParts[1]

    foreach ($candidate in $candidates) {
        $pythonPath = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($null -eq $pythonPath) { continue }

        try {
            $ver = & $pythonPath.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
            if (-not $ver) { continue }

            $parts = $ver -split "\."
            $major = [int]$parts[0]
            $minor = [int]$parts[1]

            if ($major -gt $reqMajor -or ($major -eq $reqMajor -and $minor -ge $reqMinor)) {
                return $pythonPath.Source
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
function Invoke-WithTimeout {
    param(
        [scriptblock]$ScriptBlock,
        [object[]]$ArgumentList = @(),
        [int]$TimeoutSec = 10
    )
    $job = Start-Job -ScriptBlock $ScriptBlock -ArgumentList $ArgumentList
    $finished = Wait-Job -Job $job -Timeout $TimeoutSec
    if ($null -eq $finished) {
        # Timed out - collect whatever output arrived, then clean up
        Remove-Job -Job $job -Force
        return [PSCustomObject]@{ Output = ""; ExitCode = -1; TimedOut = $true }
    }
    $output = Receive-Job -Job $job 2>&1 | Out-String
    Remove-Job -Job $job -Force
    return [PSCustomObject]@{ Output = $output; ExitCode = 0; TimedOut = $false }
}

function Ensure-EspansoService {
    param([string]$EspansoBin)
    # $script:EspansoJustStarted is set in the outer scope so the smoke test can add a grace period.

    # Registration check
    Info "Checking Espanso startup registration..."
    $checkResult = Invoke-WithTimeout -TimeoutSec 5 -ArgumentList $EspansoBin -ScriptBlock {
        param([string]$Bin)
        & $Bin service check 2>&1 | Out-String
    }
    if ($checkResult.TimedOut) {
        Warn "Espanso service check timed out - skipping registration step"
    }
    elseif ($checkResult.Output -match "registered") {
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
        else {
            Ok "Espanso service registered for startup"
        }
    }

    # Status check
    $statusResult = Invoke-WithTimeout -TimeoutSec 5 -ArgumentList $EspansoBin -ScriptBlock {
        param([string]$Bin)
        & $Bin service status 2>&1 | Out-String
    }
    if (-not $statusResult.TimedOut -and $statusResult.Output -match "running") {
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
        if (-not $pollResult.TimedOut -and $pollResult.Output -match "running") {
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

function Ensure-UserPathEntry {
    param([string]$PathEntry)

    try {
        $userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
        $entries = @()
        if (-not [string]::IsNullOrWhiteSpace($userPath)) {
            $entries = @($userPath -split ";" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        }

        $alreadyPresent = $false
        foreach ($entry in $entries) {
            if ($entry -ieq $PathEntry) {
                $alreadyPresent = $true
                break
            }
        }

        if ($alreadyPresent) {
            Ok "Venv Scripts directory already in Windows user PATH"
            return
        }

        if ([string]::IsNullOrWhiteSpace($userPath)) {
            $newUserPath = $PathEntry
        }
        else {
            $newUserPath = "$PathEntry;$userPath"
        }

        [Environment]::SetEnvironmentVariable("PATH", $newUserPath, "User")
        Ok "Added $PathEntry to Windows user PATH"
    }
    catch {
        Warn "Could not update Windows user PATH automatically: $($_.Exception.Message)"
        Info "To add it manually, run:"
        Write-Host ""
        Write-Host "  [Environment]::SetEnvironmentVariable('PATH', `"$PathEntry;`" + [Environment]::GetEnvironmentVariable('PATH', 'User'), 'User')" -ForegroundColor White
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
Ok "Python: $pyVersion"

$VenvScripts = Join-Path $VenvDir "Scripts"
$VenvPython = Join-Path $VenvScripts "python.exe"
$VenvCmd = Join-Path $VenvScripts "espansr.exe"

# Virtual environment

if (Test-Path $VenvDir) {
    $VenvConfig = Join-Path $VenvDir "pyvenv.cfg"
    if ((Test-Path $VenvConfig) -and (Test-Path $VenvPython)) {
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

# Post-install setup

Info "Running post-install setup..."
& $VenvCmd setup
if ($LASTEXITCODE -eq 0) {
    Ok "Setup complete"
}
else {
    Die "Post-install setup failed. Resolve the message above and rerun .\install.ps1"
}

$EspansoBin = Find-Espanso
$EspansoFound = $null -ne $EspansoBin
$EspansoJustStarted = $false
if ($EspansoFound) {
    Ensure-EspansoService -EspansoBin $EspansoBin
}
else {
    Warn "Espanso binary not found - startup registration skipped"
}

# PATH setup

$SessionPathEntries = $env:PATH -split ";"
if ($SessionPathEntries -contains $VenvScripts) {
    Ok "Venv Scripts directory already in session PATH"
}
else {
    $env:PATH = "$VenvScripts;$env:PATH"
    Ok "Added $VenvScripts to session PATH"
}

Ensure-UserPathEntry -PathEntry $VenvScripts

Info "This updates the Windows user PATH only. WSL PATH and shell aliases are separate."
Info "Open a new terminal for persistent PATH changes to take effect."

if (-not $EspansoFound) {
    Info "Install and start Espanso from https://espanso.org, then run:"
    Write-Host "  espansr setup"
    Write-Host "  espansr doctor"
}

# Smoke test

if ($EspansoJustStarted) {
    Info "Waiting for Espanso service to settle..."
    Start-Sleep -Seconds 2
}

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
Write-Host ""
