# Bug Log

### BUG-001: WSL resolves Linux Espanso path when Windows path exists
- **Location:** espansr/integrations/espanso.py:get_espanso_config_dir, espansr/core/platform.py:get_platform_config
- **Phase:** 8-maintain (reported during /continue)
- **Severity:** blocking
- **Expected:** In WSL, espansr prefers the Windows Espanso config path when present and sync cleans stale managed files in non-canonical locations.
- **Actual:** Path selection can remain on Linux-side config (or fail to discover Windows-side config when username lookup fails), leading to split sync/conflicts.
- **Fix-as-you-go:** yes
- **Status:** closed
- **Logged:** 2026-03-07
- **Resolved:** 2026-03-07

### BUG-002: WSL install wrapper does not complete Windows Espanso setup reliably
- **Location:** espansr/__main__.py:wsl_install_espanso (CLI flow), install.sh, install.ps1
- **Phase:** 8-maintain (reported during /continue)
- **Severity:** blocking
- **Expected:** Running `espansr wsl-install-espanso` from WSL leads to a fully usable Windows Espanso install with minimal manual follow-up.
- **Actual:** Wrapper can report installation while Windows-side setup still requires manual `.exe` installer completion and interactive steps.
- **Fix-as-you-go:** yes
- **Status:** closed
- **Logged:** 2026-03-08
- **Resolved:** 2026-03-08
