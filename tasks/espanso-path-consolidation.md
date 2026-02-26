# Tasks: Consolidate Espanso Config Path Resolution and Auto-Clean Stale YAML

**Spec:** `/specs/espanso-path-consolidation.md`  
**Branch:** `feat/2-espanso-path-consolidation`

## Task 1 — Write failing tests for path persistence and stale cleanup

**Files:** `tests/test_espanso.py`

- Test `get_espanso_config_dir()` persists resolved path to `config.espanso.config_path` after first detection
- Test `get_espanso_config_dir()` returns persisted path on subsequent calls without re-probing
- Test `get_espanso_config_dir()` falls back to auto-detection when persisted path no longer exists
- Test `clean_stale_espanso_files()` deletes `automatr-espanso.yml` and `automatr-launcher.yml` from non-canonical match dirs
- Test `clean_stale_espanso_files()` does not delete files from the canonical match dir
- Test `clean_stale_espanso_files()` does not delete user-authored files (other `.yml` names)
- Test `clean_stale_espanso_files()` is silent on permission errors (logs warning, doesn't crash)
- Test `clean_stale_espanso_files()` is called before `sync_to_espanso()` write

**Done when:** All tests exist and fail (functions don't exist yet or don't have the new behavior).

## Task 2 — Implement path persistence in `get_espanso_config_dir()`

**Files:** `automatr_espanso/integrations/espanso.py`

- After successful auto-detection, persist resolved path to `config.espanso.config_path`
- When `config.espanso.config_path` is set but directory no longer exists, clear persisted value and re-detect
- Use `save_config()` to persist the updated path

**Done when:** Path persistence tests pass.

## Task 3 — Implement `clean_stale_espanso_files()` and wire into callers

**Files:** `automatr_espanso/integrations/espanso.py`, `automatr_espanso/ui/main_window.py`

- Add `_get_candidate_paths()` helper that returns all known Espanso config candidate directories
- Add `clean_stale_espanso_files()` that scans candidates and removes managed files from non-canonical dirs
- Silent on permission errors (log warning, don't crash)
- Call before `sync_to_espanso()` write
- Call on GUI startup in `MainWindow.__init__()`

**Done when:** All stale cleanup tests pass. Full test suite green.

## Task 4 — Update `install.sh` with stale cleanup step

**Files:** `install.sh`

- Add Bash function to detect and remove stale `automatr-espanso.yml` and `automatr-launcher.yml` from non-canonical Espanso locations
- Call during installation after config directory is detected
- Keep logic consistent with `_get_candidate_paths()` in Python

**Done when:** `install.sh` includes cleanup step. Full test suite green.

## Progress

| Task | Status |
|------|--------|
| 1    | Not started |
| 2    | Not started |
| 3    | Not started |
| 4    | Not started |
