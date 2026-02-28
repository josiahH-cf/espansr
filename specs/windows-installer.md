# Feature: Native Windows Installer (PowerShell)

**Status:** Complete

## Description

The espansr Python codebase supports native Windows (`get_platform()` returns `"windows"`, `_get_candidate_paths()` includes `%APPDATA%/espanso` and `~/.espanso`), but there is no installer that can run on native Windows. The bash `install.sh` requires a Unix shell and cannot execute on Windows outside of WSL.

This spec covers creating a PowerShell installer (`install.ps1`) that provides the same installation experience on native Windows that `install.sh` provides on Linux, macOS, and WSL2. The installer must produce a working `espansr` command in a PowerShell or Command Prompt session.

This feature depends on `/specs/install-first-run.md` being implemented first, because:
1. The `espansr setup` command (introduced by that spec) centralizes post-install logic in Python — `install.ps1` delegates to it, avoiding bash-to-PowerShell duplication
2. The `PlatformConfig` (introduced by that spec) defines Windows paths in one place — `install.ps1` does not need to duplicate path construction

## Acceptance Criteria

- [x] **AC-1**: A `install.ps1` PowerShell script exists in the repo root that can be run via `.\install.ps1` in a Windows PowerShell 5.1+ or PowerShell 7+ session
- [x] **AC-2**: `install.ps1` checks for Python ≥3.11, creates a venv at `.\.venv\`, installs the package via `pip install -e .`, and delegates post-install setup to `espansr setup`
- [x] **AC-3**: `install.ps1` sets up a shell alias or adds the venv `Scripts` directory to the session/user PATH so that `espansr` is usable after install
- [x] **AC-4**: `install.ps1` performs a smoke test by running `espansr list` and `espansr status` with visible output
- [x] **AC-5**: After a fresh `.\install.ps1`, the same acceptance criteria from `/specs/install-first-run.md` AC-9 hold: `espansr list` returns at least one triggered template
- [x] **AC-6**: `install.ps1` handles Python not being found with a clear error message and download link
- [x] **AC-7**: `install.ps1` is idempotent — running it a second time reuses the existing venv and does not duplicate aliases or templates

## Affected Areas

| Area | Files | Change type |
|------|-------|-------------|
| Installer | `install.ps1` | Create — new PowerShell installer |
| Documentation | `README.md` | Modify — add Windows install instructions |

## Constraints

- **No new Python dependencies**: the PowerShell script only calls Python/pip and `espansr setup`
- **No admin elevation required**: the installer should work without `Run as Administrator` (venv + user-level PATH)
- **PowerShell 5.1 compatible**: must work on the version bundled with Windows 10/11, not just PowerShell 7
- **No Chocolatey/Scoop/winget dependency**: do not require a package manager to install espansr
- **Idempotent**: safe to re-run without side effects
- **No system deps step**: unlike Linux, native Windows does not need xcb/system packages for PyQt6 — the script is simpler than `install.sh`

## Out of Scope

- WSL2 installation (already handled by `install.sh`)
- Installing Python itself (provide a download link on failure)
- Installing Espanso (upstream tool)
- Creating a Windows `.msi` or `.exe` installer package
- Adding to Windows Store or winget manifest
- PyPI publishing
- GUI-specific Windows configuration (DPI scaling, etc.)
- Any changes to the Python codebase (all Windows support is already in `PlatformConfig` from the prerequisite spec)

## Dependencies

- **`/specs/install-first-run.md` must be implemented first** — `install.ps1` calls `espansr setup` which is created by that spec
- `PlatformConfig` in `espansr/core/platform.py` must include Windows paths (created by the prerequisite spec)

## Notes

### Script structure

`install.ps1` mirrors the thin `install.sh` structure (post-prerequisite):

1. **Python check**: find `python3` or `python` in PATH, verify version ≥3.11. On failure: print `"Python 3.11+ is required. Download from https://www.python.org/downloads/"` and exit.
2. **Venv creation**: `python -m venv .\.venv` if `.\.venv\` does not exist.
3. **pip install**: `.\.venv\Scripts\pip install -e .`
4. **Post-install setup**: `.\.venv\Scripts\espansr setup` — this handles templates, Espanso detection, launcher, and stale cleanup via the Python platform module.
5. **PATH setup**: Add `.\.venv\Scripts\` to the current session's `$env:PATH`. Optionally offer to add to user-level PATH permanently via `[Environment]::SetEnvironmentVariable`.
6. **Smoke test**: `.\.venv\Scripts\espansr list` and `.\.venv\Scripts\espansr status` with visible output.
7. **Completion banner**.

### Windows PATH considerations

Unlike bash aliases in `~/.bashrc`, Windows has two PATH options:
- **Session-only**: `$env:PATH += ";$PWD\.venv\Scripts"` — works immediately, lost on close
- **User-level permanent**: `[Environment]::SetEnvironmentVariable("PATH", ...)` — persists across sessions but requires a new terminal to take effect

The installer should do the session-only approach by default and inform the user how to make it permanent. Do NOT modify the system-level PATH (requires admin).

### PyQt6 on Windows

PyQt6 wheels for Windows include all necessary DLLs — no system package installation step is needed (unlike Linux where xcb libs must be installed via apt). This makes the Windows installer simpler than the Linux one.

### Espanso on Windows

On native Windows, Espanso typically installs to `%APPDATA%\espanso`. The `PlatformConfig` for `"windows"` already includes this path in `espanso_candidate_dirs`. The `espansr setup` command handles detection automatically.

### Testing

The PowerShell installer itself cannot be tested via pytest (it's a `.ps1` script, not Python). Testing strategy:
- Manual testing on a Windows machine or Windows CI runner
- The `espansr setup` command it delegates to IS tested via pytest (from the prerequisite spec)
- Consider adding a GitHub Actions Windows runner to CI matrix as a follow-up (tracked in CI Hardening backlog)
