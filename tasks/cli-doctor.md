# Tasks: `espansr doctor` Diagnostic Command

**Spec:** `/specs/cli-doctor.md`

## Status

- Total: 2
- Complete: 2
- Remaining: 0

## Task List

### Task 1: Write failing tests for `cmd_doctor`

- **Files:** `tests/test_doctor.py` (create)
- **Done when:** `pytest tests/test_doctor.py` runs and all tests fail (no implementation yet); covers all 5 acceptance criteria
- **Criteria covered:** AC-1 through AC-5
- **Status:** [x] Complete

#### Test plan

1. Test all-healthy scenario: mock all checks to pass → every line has `[ok]`, exit 0
2. Test Espanso not found: mock `get_espanso_config_dir` → `None`, `shutil.which` → `None` → `[FAIL]` for espanso config, `[FAIL]` for binary, exit 1
3. Test no templates: mock `iter_with_triggers` → empty → `[FAIL]`, exit 1
4. Test validation warnings only (no errors): → `[warn]`, exit 0
5. Test validation errors: → `[FAIL]`, exit 1
6. Test launcher missing: mock `get_match_dir` returns a dir but no launcher file → `[FAIL]`
7. Test subparser registered: parse `doctor` command succeeds

### Task 2: Implement `cmd_doctor` and register subparser

- **Files:** `espansr/__main__.py`
- **Done when:** All tests from Task 1 pass; `espansr doctor --help` works; `ruff check .` clean; all 167 existing tests pass
- **Criteria covered:** AC-1 through AC-5
- **Status:** [x] Complete

#### Implementation details

1. Add `cmd_doctor(args) -> int` to `espansr/__main__.py`
2. Checks in order:
   - Python version (sys.version_info >= 3.11)
   - espansr config dir exists (`get_config_dir()`)
   - Templates found (`iter_with_triggers()` non-empty)
   - Espanso config detected (`get_espanso_config_dir()`)
   - Espanso binary found (`shutil.which("espanso")` or WSL2 check)
   - Launcher file present (`get_match_dir() / "espansr-launcher.yml"`)
   - Template validation (0 errors from `validate_all()`)
3. Register `doctor` subparser and add to handlers dict
4. Exit 0 if no `[FAIL]`, exit 1 otherwise

## Test Strategy

| Criterion | Tested by |
|-----------|-----------|
| AC-1 (7 checks) | Task 1 — all-healthy test verifies 7 output lines |
| AC-2 (status indicators) | Task 1 — assert `[ok]`, `[warn]`, `[FAIL]` prefixes |
| AC-3 (exit codes) | Task 1 — healthy=0, any-fail=1 |
| AC-4 (reuses existing) | Task 2 — code review, no new logic |
| AC-5 (registered in argparse) | Task 1 — subparser test |
