# Tasks: Cross-Platform Installer Architecture

**Spec:** `/specs/install-first-run.md`

## Status

- Total: 4
- Complete: 2
- Remaining: 2

## Task List

### Task 1: Centralize platform paths into PlatformConfig

- **Files:** `espansr/core/platform.py`, `espansr/core/config.py`, `espansr/integrations/espanso.py`, `tests/test_platform.py`
- **Done when:** `grep -rn "import platform" espansr/` returns only `espansr/core/platform.py`; `PlatformConfig` dataclass and `get_platform_config()` exist and return correct paths for all 4 platforms; `get_config_dir()` and `_get_candidate_paths()` delegate to `get_platform_config()`; all 126 existing tests pass; new `PlatformConfig` tests pass
- **Criteria covered:** AC-1, AC-2, AC-3, AC-4, AC-11
- **Status:** [x] Complete
2. Add `get_platform_config()` factory that calls `get_platform()` once and maps to paths (see spec Notes for exact path table)
3. In `espansr/core/config.py`:
   - Remove `import platform` (L8)
   - Rewrite `get_config_dir()` to use `get_platform_config().espansr_config_dir.parent` as `base` and `get_platform_config().espansr_config_dir` as `config_dir`
   - Keep the `_migrate_config_dir(base)` call intact
   - **Before removing the re-export on L14**: grep for `from espansr.core.config import get_platform` and `from espansr.core.config import is_windows` across all `.py` files. If any exist in tests or source, update those imports to `from espansr.core.platform import ...`. Then remove L14.
4. In `espansr/integrations/espanso.py`:
   - Remove `import platform` (L8)
   - Replace the body of `_get_candidate_paths()` with: `return get_platform_config().espanso_candidate_dirs`
   - Add `from espansr.core.platform import get_platform_config` to imports (keep existing `is_wsl2`, `get_windows_username`, `get_wsl_distro_name` imports — they're used elsewhere in espanso.py)
5. In `tests/test_platform.py`:
   - Add tests for `get_platform_config()` with mocked `get_platform()` return values for each of: `"linux"`, `"macos"`, `"wsl2"`, `"windows"`
   - Assert `espansr_config_dir` and `espanso_candidate_dirs` match the spec table
   - For WSL2: mock `get_windows_username()` to return `"testuser"` and verify `/mnt/c/Users/testuser/...` paths appear in candidates
   - For WSL2: mock `get_windows_username()` to return `None` and verify `/mnt/c/` paths are absent
6. Run full test suite: `pytest`
7. Run lint: `ruff check .`
8. Verify: `grep -rn "import platform" espansr/` returns only `espansr/core/platform.py`

### Task 2: Add `espansr setup` command and bundled starter template

- **Files:** `espansr/__main__.py`, `templates/espansr_help.json` (new), `tests/test_setup.py` (new)
- **Done when:** `espansr setup` runs successfully in a tmp dir environment, copies the bundled template, detects/skips Espanso, prints a summary; `espansr list` shows the template after setup; re-running `espansr setup` does not duplicate templates; all tests pass
- **Status:** [x] Complete

#### Implementation details

1. Create `templates/espansr_help.json` (exact content in spec Notes — copy verbatim)
2. In `espansr/__main__.py`:
   - Add `cmd_setup(args) -> int` function
   - Register `setup` subcommand in `main()`: `subparsers.add_parser("setup", help="Run post-install setup")`
   - Add `"setup": cmd_setup` to the handlers dict
3. `cmd_setup()` implementation (in order):
   a. `from espansr.core.config import get_config_dir, get_templates_dir`
   b. `config_dir = get_config_dir()` — creates dir if needed
   c. `templates_dir = get_templates_dir()` — creates dir if needed
   d. Locate bundled templates: `bundled_dir = Path(__file__).resolve().parent.parent / "templates"`. If `bundled_dir` is not a directory, print warning and continue (non-fatal).
   e. Copy loop: for each `.json` in bundled_dir, if not `(templates_dir / file.name).exists()`, copy with `shutil.copy2`. Count copies.
   f. Print: `"Templates: copied {n} bundled template(s) to {templates_dir}"` or `"Templates: {templates_dir} ({n} existing, no changes)"`
   g. `from espansr.integrations.espanso import get_espanso_config_dir, clean_stale_espanso_files, generate_launcher_file`
   h. `espanso_dir = get_espanso_config_dir()`
   i. If `espanso_dir`: call `clean_stale_espanso_files()`, call `generate_launcher_file()`, print `"Espanso config: {espanso_dir}"`, print `"Launcher: generated"`
   j. If not `espanso_dir`: print platform-specific guidance (use `get_platform()` to pick message — see spec Notes table), print `"Launcher: skipped (no Espanso config)"`
   k. Return 0
4. Create `tests/test_setup.py`:
   - Test that `cmd_setup` copies bundled template to empty tmp templates dir
   - Test that `cmd_setup` does NOT overwrite an existing file with the same name
   - Test that `cmd_setup` succeeds even when Espanso config is not found (mocked)
   - Test that `espansr list` returns at least one template after setup in a tmp environment
   - All tests must use `tmp_path` fixture, not real config dirs
   - Mock `get_config_dir`, `get_templates_dir` to point to tmp dirs
   - Mock `get_espanso_config_dir` to return `None`
5. Run: `pytest tests/test_setup.py && pytest`

### Task 3: Restructure install.sh to delegate to `espansr setup`

- **Files:** `install.sh`
- **Done when:** `install.sh` no longer contains any of these bash functions: `detect_espanso()`, `clean_stale_espanso_files()`, `generate_launcher()`, `setup_templates_dir()`; instead it calls `$VENV_CMD setup`; the only platform-branching that remains is `detect_platform()` (for apt-get) and the system-deps block; smoke test output is visible (not suppressed); all existing tests still pass
- **Criteria covered:** AC-6, AC-9
- **Status:** [ ] Not started

#### Implementation details

1. Delete these bash functions and their call sites:
   - `detect_espanso()` and `detect_espanso` call (approximately L116–L156)
   - `clean_stale_espanso_files()` and `clean_stale_espanso_files` call (approximately L159–L234)
   - `generate_launcher()` and `generate_launcher` call (approximately L237–L243)
   - `setup_templates_dir()` and `setup_templates_dir` call (approximately L246–L272)
2. After the `pip install` block and before `setup_shell_alias`, add:
   ```bash
   # ─── Post-install setup ────────────────────────────────────────────────────
   info "Running post-install setup…"
   "$VENV_CMD" setup && ok "Setup complete" || warn "Setup completed with warnings"
   ```
3. Update the smoke test section to show output instead of suppressing:
   - Change `"$VENV_CMD" list >/dev/null 2>&1` to `"$VENV_CMD" list`
   - Change `"$VENV_CMD" status >/dev/null 2>&1` to `"$VENV_CMD" status`
4. Verify `detect_platform()` still works (it only returns `"macos"`, `"wsl2"`, or `"linux"` — used only for `install_system_deps`). Do NOT delete this function.
5. Verify `setup_shell_alias()` still works. Do NOT delete this function.
6. Run: `bash -n install.sh` (syntax check) and `pytest` (ensure nothing broke)

### Task 4: Add platform-specific guidance to `espansr status`

- **Files:** `espansr/__main__.py`, `tests/test_setup.py` (or `tests/test_platform.py`)
- **Done when:** `espansr status` with no Espanso config dir prints a guidance message that includes the URL `https://espanso.org` and is different for WSL2 vs other platforms; tests verify the guidance message for each platform
- **Criteria covered:** AC-10
- **Status:** [ ] Not started

#### Implementation details

1. In `espansr/__main__.py` `cmd_status()`:
   - When `config_dir` is None, instead of `print("Espanso config: not found")`, import `get_platform` from `espansr.core.platform`
   - Build the message using the platform-specific guidance table from the spec Notes:
     - WSL2: `"Espanso config: not found — install Espanso on Windows (https://espanso.org), then run 'espanso start' from PowerShell"`
     - All others: `"Espanso config: not found — install Espanso (https://espanso.org), then run 'espanso start' to initialize"`
2. Add tests (in `tests/test_setup.py` or a new section of an existing test file):
   - Mock `get_espanso_config_dir` to return `None`
   - Mock `get_platform` to return `"wsl2"` — assert output contains "on Windows" and "PowerShell"
   - Mock `get_platform` to return `"linux"` — assert output contains "https://espanso.org" and does NOT contain "on Windows"
   - Mock `get_platform` to return `"macos"` — assert output contains "https://espanso.org"
3. Run: `pytest`

## Test Strategy

| Criterion | Tested by |
|-----------|-----------|
| AC-1 (PlatformConfig exists) | Task 1 — `test_platform.py` |
| AC-2 (config.py delegates) | Task 1 — grep verification + existing `test_espanso.py` and `test_path_consolidation.py` passing |
| AC-3 (espanso.py delegates) | Task 1 — grep verification + existing `test_path_consolidation.py` passing |
| AC-4 (single source) | Task 1 — grep verification |
| AC-5 (setup command) | Task 2 — `test_setup.py` |
| AC-6 (install.sh thin) | Task 3 — manual review + `bash -n` syntax check |
| AC-7 (bundled template) | Task 2 — `test_setup.py` verifies template passes `Template.from_dict()` |
| AC-8 (no-overwrite copy) | Task 2 — `test_setup.py` |
| AC-9 (list after install) | Task 2 — `test_setup.py` |
| AC-10 (status guidance) | Task 4 — `test_setup.py` |
| AC-11 (new platform = 1 file) | Task 1 — architectural; verified by AC-2 + AC-3 grep |
| AC-12 (all tests pass) | Every task — `pytest` at end |

## Session Log

<!-- Append after each session: date, completed, blockers -->

### 2026-02-28 — Task 1 complete
- Added `PlatformConfig` dataclass and `get_platform_config()` to `platform.py`
- Refactored `config.py` to delegate `get_config_dir()` to `get_platform_config()`
- Refactored `espanso.py` to delegate `_get_candidate_paths()` to `get_platform_config()`
- Removed `import platform` (stdlib) from `config.py` and `espanso.py`
- Kept `get_platform`/`is_windows` re-exports in `config.py` (consumed by existing tests)
- Updated WSL2 candidate path test mock targets in `test_path_consolidation.py`
- 11 new tests for `PlatformConfig`; 148 total tests pass; lint clean
- `grep -rn "import platform" espansr/` returns only `espansr/core/platform.py`
