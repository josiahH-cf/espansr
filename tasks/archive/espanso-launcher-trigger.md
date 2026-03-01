# Tasks: Ship Espanso Launcher Trigger for Hotkey-Style GUI Launch

**Spec:** `/specs/espanso-launcher-trigger.md`
**Branch:** `feat/5-espanso-launcher-trigger`

## Task 1 — Write failing tests for launcher generation

**File:** `tests/test_launcher.py`

- Test `generate_launcher_file()` writes valid Espanso v2 shell trigger YAML
- Test launcher uses config trigger (`:launch` override)
- Test WSL2 command uses `wsl.exe -d DISTRO`
- Test WSL2 without distro name omits `-d` flag
- Test returns False when no match dir found
- Test fallback to `sys.executable` when `shutil.which` returns None
- Test accepts explicit `match_dir` parameter
- Test `_MANAGED_FILES` includes `espansr-launcher.yml`
- Test GUI first-run tip when launcher file is missing
- Test no tip when launcher file already exists

**Done when:** All tests exist and fail (generate_launcher_file doesn't exist yet).

## Task 2 — Implement `generate_launcher_file()` and config field

**Files:** `espansr/integrations/espanso.py`, `espansr/core/config.py`

- Add `launcher_trigger: str = ":aopen"` to `EspansoConfig`
- Add `generate_launcher_file(match_dir=None)` to espanso.py
- Build platform-specific shell command (WSL2 vs native)
- Resolve binary path via `shutil.which()` with `sys.executable` fallback
- Write Espanso v2 shell trigger YAML

**Done when:** Launcher generation tests pass.

## Task 3 — Wire into GUI (first-run tip) and install.sh

**Files:** `espansr/ui/main_window.py`, `install.sh`

- Add `_check_launcher()` to MainWindow — show status bar tip if launcher file missing
- Add `generate_launcher` step to `install.sh`
- Ensure launcher file is in `_MANAGED_FILES` for stale cleanup

**Done when:** GUI tip tests pass. Full test suite green.

## Progress

| Task | Status |
|------|--------|
| 1    | Complete |
| 2    | Complete |
| 3    | Complete |
