# install.ps1 — espansr installer for native Windows
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

# ─── Color helpers ────────────────────────────────────────────────────────────

function Info  { param([string]$Msg) Write-Host "[INFO] $Msg" -ForegroundColor Cyan }
function Ok    { param([string]$Msg) Write-Host "[ OK ] $Msg" -ForegroundColor Green }
function Warn  { param([string]$Msg) Write-Host "[WARN] $Msg" -ForegroundColor Yellow }
function Err   { param([string]$Msg) Write-Host "[ERR ] $Msg" -ForegroundColor Red }

function Die {
    param([string]$Msg)
    Err $Msg
    exit 1
}

# ─── Python version check ─────────────────────────────────────────────────────

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

Info "Platform: windows"

$PythonBin = Find-Python
if (-not $PythonBin) {
    Die "Python $PythonMin+ is required. Download from https://www.python.org/downloads/"
}

$pyVersion = & $PythonBin --version
Ok "Python: $pyVersion"

# ─── Virtual environment ──────────────────────────────────────────────────────

if (Test-Path $VenvDir) {
    Info "Using existing venv: $VenvDir"
}
else {
    Info "Creating virtual environment at $VenvDir..."
    & $PythonBin -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Die "Failed to create virtual environment" }
    Ok "Venv created"
}

$VenvPip = Join-Path $VenvDir "Scripts" "pip.exe"
$VenvCmd = Join-Path $VenvDir "Scripts" "espansr.exe"

Info "Upgrading pip..."
& $VenvPip install --quiet --upgrade pip
if ($LASTEXITCODE -ne 0) { Warn "pip upgrade failed — continuing with existing version" }

Info "Installing espansr..."
& $VenvPip install --quiet -e $ScriptDir
if ($LASTEXITCODE -ne 0) { Die "Package installation failed" }
Ok "Package installed"

# ─── Post-install setup ──────────────────────────────────────────────────────

Info "Running post-install setup..."
& $VenvCmd setup
if ($LASTEXITCODE -eq 0) {
    Ok "Setup complete"
}
else {
    Warn "Setup completed with warnings"
}

# ─── PATH setup ──────────────────────────────────────────────────────────────

$VenvScripts = Join-Path $VenvDir "Scripts"

if ($env:PATH -split ";" | Where-Object { $_ -eq $VenvScripts }) {
    Ok "Venv Scripts directory already in session PATH"
}
else {
    $env:PATH = "$VenvScripts;$env:PATH"
    Ok "Added $VenvScripts to session PATH"
}

Info "To make 'espansr' available in all future sessions, run:"
Write-Host ""
Write-Host "  [Environment]::SetEnvironmentVariable('PATH', `"$VenvScripts;`" + [Environment]::GetEnvironmentVariable('PATH', 'User'), 'User')" -ForegroundColor White
Write-Host ""
Info "Then open a new terminal for the change to take effect."

# ─── Smoke test ──────────────────────────────────────────────────────────────

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

# ─── Done ─────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "+================================================+" -ForegroundColor Green
Write-Host "|   espansr installed successfully!               |" -ForegroundColor Green
Write-Host "+================================================+" -ForegroundColor Green
Write-Host ""
Write-Host "  CLI:  espansr sync / status / list"
Write-Host "  GUI:  espansr gui"
Write-Host "  Bin:  $VenvCmd"
Write-Host ""
