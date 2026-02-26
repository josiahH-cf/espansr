# Tasks: Consolidate WSL/Platform Detection into Shared Utility Module

**Spec:** `/specs/wsl-platform-utility.md`  
**Branch:** `feat/1-wsl-platform-utility`

## Task 1 — Write failing tests for platform module

**Files:** `tests/test_platform.py`

- Test `get_platform()` returns `"wsl2"` when `/proc/version` contains "microsoft"
- Test `get_platform()` returns `"linux"` on native Linux
- Test `get_platform()` returns `"macos"` on Darwin
- Test `get_platform()` returns `"windows"` on Windows
- Test `is_wsl2()` returns `True`/`False` correctly
- Test `get_windows_username()` returns username when `cmd.exe` succeeds
- Test `get_windows_username()` returns `None` when `cmd.exe` fails/times out
- Test `get_windows_username()` returns `None` when result is empty

**Done when:** All tests exist and fail (module doesn't exist yet).

## Task 2 — Create `platform.py` and make tests pass

**Files:** `automatr_espanso/core/platform.py`

- Extract `get_platform()` from `config.py`
- Add `is_wsl2()` (calls `get_platform()`)
- Extract `get_windows_username()` from `espanso.py` L89–95
- `get_windows_username()` returns `None` on all failure modes
- Subprocess timeout ≤ 5 seconds

**Done when:** All `test_platform.py` tests pass.

## Task 3 — Refactor callers to import from `platform.py`

**Files:** `config.py`, `espanso.py`, `__main__.py`

- `config.py`: Remove `get_platform()`, `is_windows()` definitions; import from `platform`
- `espanso.py`: Remove all inline `/proc/version` reads and `cmd.exe` calls; import `is_wsl2`, `get_windows_username` from `platform`
- `__main__.py`: Remove inline `/proc/version` read in `cmd_status()`; import `is_wsl2` from `platform`
- All 14 existing tests pass without modification

**Done when:** No `/proc/version` reads or `cmd.exe` calls remain outside `platform.py`. Full test suite green.

## Progress

| Task | Status |
|------|--------|
| 1    | Complete |
| 2    | Complete |
| 3    | Complete |
