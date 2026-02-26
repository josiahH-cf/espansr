# Spec: Consolidate Espanso Config Path Resolution and Auto-Clean Stale YAML

**Issue:** #2  
**Status:** Draft

## Description

Ensure `get_espanso_config_dir()` resolves to one canonical Espanso config path and persists it. On startup and before each sync, scan all known Espanso config locations and auto-delete any `automatr-espanso.yml` or `automatr-launcher.yml` files found in non-canonical directories. Update `install.sh` to perform the same cleanup during installation.

## Acceptance Criteria

- [ ] After first successful detection, `get_espanso_config_dir()` persists the resolved path to `config.espanso.config_path` so subsequent calls skip probing
- [ ] A new `clean_stale_espanso_files()` function scans all known Espanso config candidate paths and deletes `automatr-espanso.yml` and `automatr-launcher.yml` from any `match/` directory that is NOT the canonical one
- [ ] `clean_stale_espanso_files()` is called before each `sync_to_espanso()` write and on GUI startup
- [ ] `clean_stale_espanso_files()` never deletes user-authored files — only files named `automatr-espanso.yml` or `automatr-launcher.yml`
- [ ] `install.sh` detects and removes stale `automatr-espanso.yml` files from non-canonical Espanso locations during installation
- [ ] When `config.espanso.config_path` is already set but the directory no longer exists, the resolver falls back to auto-detection and updates the persisted path

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `automatr_espanso/integrations/espanso.py` — add `clean_stale_espanso_files()`, update `get_espanso_config_dir()` to persist, call cleanup before sync |
| **Modify** | `automatr_espanso/ui/main_window.py` (or new GUI entry) — call cleanup on startup |
| **Modify** | `install.sh` — add stale file cleanup step |
| **Create/Modify** | `tests/test_espanso.py` — tests for cleanup and path persistence |

## Constraints

- Only delete files with exact names `automatr-espanso.yml` and `automatr-launcher.yml` — never glob or remove directories
- Cleanup must be silent on permission errors (log a warning, don't crash)
- On WSL2, candidate paths include both Linux-side (`~/.config/espanso`) and Windows-side (`/mnt/c/Users/<user>/.config/espanso`, etc.)
- The persisted path in `config.espanso.config_path` must be re-validated on each startup (directory may have been removed)

## Out of Scope

- Migrating user-authored Espanso files between locations
- Changing how `match/` directory is created
- GUI for manually selecting Espanso config path (can be added later)

## Dependencies

- Issue #1 (shared platform utility module) — `is_wsl2()`, `get_windows_username()` needed by candidate path enumeration

## Notes

- Known Espanso candidate paths on WSL2: `/mnt/c/Users/<user>/.config/espanso`, `/mnt/c/Users/<user>/.espanso`, `/mnt/c/Users/<user>/AppData/Roaming/espanso`
- Known candidate paths on Linux: `~/.config/espanso`, `~/.espanso`
- Known candidate paths on macOS: `~/Library/Application Support/espanso`, `~/.config/espanso`
- The `install.sh` cleanup can reuse the same candidate-list logic in Bash
