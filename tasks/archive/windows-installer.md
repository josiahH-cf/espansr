# Tasks: Native Windows Installer (PowerShell)

**Spec:** `/specs/windows-installer.md`

## Status

- Total: 2
- Complete: 2
- Remaining: 0

## Task List

### Task 1: Create `install.ps1` PowerShell installer

- **Files:** `install.ps1`
- **Done when:** `install.ps1` exists, passes `powershell -Command "& { Get-Content install.ps1 }"` lint-level parse, mirrors `install.sh` structure: Python ≥3.11 check → venv creation → pip install → `espansr setup` → PATH setup → smoke test → banner; script is idempotent; no admin elevation required
- **Criteria covered:** AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7
- **Status:** [x] Complete

#### Implementation details

1. Create `install.ps1` with sections mirroring `install.sh`:
   - **Header**: `#Requires -Version 5.1`, strict mode (`Set-StrictMode -Version Latest`, `$ErrorActionPreference = "Stop"`)
   - **Color helpers**: `Info`, `Ok`, `Warn`, `Error` functions using `Write-Host` with ANSI-compatible colors
   - **Python check**: Search for `python`, `python3` in PATH. Verify version ≥3.11 via `python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"`. On failure: print download link and exit.
   - **Venv creation**: `python -m venv .\.venv` if `.\.venv\` doesn't exist; reuse if it does (idempotent)
   - **pip install**: `.\.venv\Scripts\pip install -e .`
   - **Post-install setup**: `.\.venv\Scripts\espansr setup`
   - **PATH setup**: Add `.\.venv\Scripts` to `$env:PATH` for current session. Print instructions for permanent user-level PATH via `[Environment]::SetEnvironmentVariable`. Do NOT auto-modify user PATH.
   - **Smoke test**: `.\.venv\Scripts\espansr list` and `.\.venv\Scripts\espansr status` with visible output
   - **Completion banner**: Green box matching `install.sh` style
2. Verify syntax: `pwsh -NoProfile -Command "& { [System.Management.Automation.Language.Parser]::ParseFile('install.ps1', [ref]$null, [ref]$null) }"` (if pwsh available) or manual inspection

### Task 2: Update README.md with Windows install instructions

- **Files:** `README.md`
- **Done when:** README includes Windows install section with `.\install.ps1` command, prerequisites (Python 3.11+), and manual install alternative; existing Linux/macOS instructions are preserved
- **Criteria covered:** (documentation completeness)
- **Status:** [x] Complete

#### Implementation details

1. Add a Windows section to the Install portion of README, after the existing bash instructions
2. Include prerequisites note about Python 3.11+
3. Include manual install alternative for Windows
4. Run `pytest` to ensure no regressions
