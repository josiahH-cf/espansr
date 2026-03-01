# Spec: Consolidate WSL/Platform Detection into Shared Utility Module

**Issue:** #1  
**Status:** Complete

## Description

Extract all platform and WSL2 detection logic from `config.py` and `espanso.py` into a single `espansr/core/platform.py` module. This module becomes the sole source of truth for `get_platform()`, `is_wsl2()`, and `get_windows_username()` across the Python codebase. The refactor eliminates three separate `/proc/version` reads and two independent `cmd.exe` subprocess calls.

## Acceptance Criteria

- [x] A new `espansr/core/platform.py` module exports `get_platform()`, `is_wsl2()`, and `get_windows_username()`
- [x] `config.py` imports `get_platform` from `platform.py` instead of defining its own; no `/proc/version` read remains in `config.py`
- [x] `espanso.py` imports `is_wsl2` and `get_windows_username` from `platform.py` instead of inline detection; no `/proc/version` read or `cmd.exe` call remains in `espanso.py`
- [x] `get_windows_username()` returns `None` (not raises) when `cmd.exe` is unavailable, times out, or returns empty output
- [x] `__main__.py` `cmd_status()` imports from `platform.py` instead of doing its own `/proc/version` read
- [x] All 14 existing tests pass without modification

## Affected Areas

| Area | Files |
|------|-------|
| **Create** | `espansr/core/platform.py` |
| **Modify** | `espansr/core/config.py` — remove `get_platform()`, `is_windows()`, import from platform |
| **Modify** | `espansr/integrations/espanso.py` — remove inline WSL2 checks, import from platform |
| **Modify** | `espansr/__main__.py` — `cmd_status()` uses platform module |
| **Create** | `tests/test_platform.py` — unit tests for the new module |

## Constraints

- Pure refactor — no behavior change to any public function
- `install.sh` is Bash and cannot import Python; its WSL2 detection stays as-is but should remain logically consistent with `platform.py`
- `get_windows_username()` subprocess timeout must be ≤5 seconds (current behavior)

## Out of Scope

- Changing Espanso config path resolution logic (that's Issue #2)
- Modifying `install.sh` (Bash duplication is accepted)
- Adding caching/memoization for platform results (can be added later if needed)

## Dependencies

None — this is the foundation issue.

## Notes

Current duplication locations:
- `config.py` L14–38: `get_platform()` reads `/proc/version`
- `config.py` L41–43: `is_windows()` calls `get_platform()`
- `espanso.py` L79–86: inline `/proc/version` read for WSL2
- `espanso.py` L89–95: `cmd.exe` subprocess for Windows username
- `espanso.py` L196–202: inline `/proc/version` read in `sync_to_espanso()`
- `espanso.py` L244–250: inline `/proc/version` read in `restart_espanso()`
- `__main__.py` L46–52: inline `/proc/version` read in `cmd_status()`
