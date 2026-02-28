# Roadmap — Espansr

## Backlog — v1.1+

> Each item has a spec in `/specs/`. See the Feature Lifecycle in `/AGENTS.md`.

### CLI Improvements

| # | Feature | Spec | Est. Sessions | Priority |
|---|---------|------|---------------|----------|
| 10 | `espansr doctor` diagnostic command | `/specs/cli-doctor.md` | 1 | High |
| 11 | CLI dry-run and verbose modes | `/specs/cli-dry-run-verbose.md` | 1–2 | Medium |
| 12 | Colored CLI output | `/specs/cli-colored-output.md` | 1 | Medium |
| 13 | Shell tab completion | `/specs/cli-tab-completion.md` | 1 | Low |

### Infrastructure

| # | Feature | Spec | Est. Sessions | Priority |
|---|---------|------|---------------|----------|
| 14 | Setup and platform resilience | `/specs/setup-platform-resilience.md` | 1–2 | High |

### GUI Improvements

| # | Feature | Spec | Est. Sessions | Priority |
|---|---------|------|---------------|----------|
| 15 | Status bar and sync feedback | `/specs/gui-status-bar-feedback.md` | 1–2 | High |
| 16 | Template preview pane | `/specs/gui-template-preview.md` | 1 | Medium |
| 17 | Dark/light mode with auto-detection | `/specs/gui-dark-mode.md` | 2 | Medium |
| 18 | Keyboard shortcuts | `/specs/gui-keyboard-shortcuts.md` | 1 | Low |

### Recommended implementation order

1. `espansr doctor` (#10) — high value, low risk, composes existing code
2. Setup/platform resilience (#14) — infrastructure hardening before new features
3. GUI status bar & feedback (#15) — biggest UX gap in the GUI
4. CLI dry-run/verbose (#11) — safety net for power users
5. Colored CLI output (#12) — polish, benefits doctor/validate/status
6. Template preview (#16) — UX improvement
7. Dark/light mode (#17) — theme completion
8. Keyboard shortcuts (#18) — power user polish
9. Tab completion (#13) — nice-to-have

## Active

_No active work — ready for next feature._

**Next up:** GUI dark/light mode (#18) per recommended order

## Completed

### CLI Dry-Run and Verbose Modes
- `--dry-run` flag on `espansr sync` and `espansr setup`
- `--verbose` flag on `espansr setup` for per-file detail
- Flags combinable; zero side effects in dry-run mode
- `sync_to_espanso()` accepts `dry_run` parameter
- 8 tests in `tests/test_dry_run.py`
- **Spec:** `/specs/cli-dry-run-verbose.md` — **Tasks:** `/tasks/cli-dry-run-verbose.md`

### GUI Persistent Status Bar and Sync Feedback
- Permanent `QLabel` in status bar showing `Espanso: <path>` or `Espanso: not found`
- Status indicator refreshes on launch and after each sync
- Successful sync shows "Synced N template(s) to Espanso" with actual count
- Failed sync shows "Sync blocked: N error(s)" with reason
- `SyncResult` dataclass and `_last_sync_count` for richer feedback
- 12 tests in `tests/test_status_bar.py`
- **Spec:** `/specs/gui-status-bar-feedback.md` — **Tasks:** `/tasks/gui-status-bar-feedback.md`

### `espansr doctor` Diagnostic Command
- `cmd_doctor()` in `espansr/__main__.py` runs 7 sequential checks
- Checks: Python version, config dir, templates, Espanso config, Espanso binary, launcher, validation
- Status indicators: `[ok]`, `[warn]`, `[FAIL]`; exit 0 if no failures, 1 otherwise
- WSL2-aware: missing native Espanso binary is `[ok]` on WSL2
- Reuses existing functions — no duplicated logic
- 12 tests in `tests/test_doctor.py`
- **Spec:** `/specs/cli-doctor.md` — **Tasks:** `/tasks/cli-doctor.md`

### First Public Release (v1.0)
- README polished with CI badge, platform support matrix, and complete usage guide
- `CHANGELOG.md` created with entries for all shipped features
- Version bumped `0.1.0` → `1.0.0` in `pyproject.toml` and `espansr/__init__.py`
- `espansr --version` flag added
- 9 tests in `tests/test_release.py`
- **Spec:** `/specs/first-public-release.md` — **Tasks:** `/tasks/first-public-release.md`
- **Remaining human action:** Tag v1.0.0 release on GitHub

### Windows Installer
- `install.ps1` PowerShell script (5.1+ compatible) mirrors `install.sh` structure
- Python ≥3.11 check with download link on failure
- Venv creation, pip install, delegates to `espansr setup`
- Session PATH setup with instructions for permanent user-level PATH
- Smoke test with visible output, idempotent re-runs
- README updated with Windows install instructions
- **Spec:** `/specs/windows-installer.md` — **Tasks:** `/tasks/windows-installer.md`

### Lint Cleanup
- `ruff check .` and `black --check .` pass with zero warnings
- Code style is consistent across all 26 files
- Verified 2026-02-28

### CI Hardening
- Ruff lint step in `.github/workflows/ci.yml`
- Black format check in CI
- Python 3.11, 3.12, 3.13 test matrix
- All dependency versions pinned with upper bounds in `pyproject.toml`
- LICENSE file present in repo root

### Cross-Platform Installer Architecture
- `PlatformConfig` dataclass and `get_platform_config()` in `espansr/core/platform.py`
- `config.py` and `espanso.py` delegate all path logic to `PlatformConfig`
- `espansr setup` CLI command: copies bundled templates, detects Espanso, cleans stale files, generates launcher
- Bundled starter template `templates/espansr_help.json`
- `install.sh` restructured: ~145 lines of duplicated bash replaced by `$VENV_CMD setup`
- `espansr status` shows platform-specific guidance when Espanso is missing
- 10 tests in `tests/test_setup.py`, 11 new tests in `tests/test_platform.py`
- **Spec:** `/specs/install-first-run.md` — **Tasks:** `/tasks/install-first-run.md`

### Issue #7 — Template Import
- `import_template()` and `import_templates()` in `espansr/core/templates.py`
- Strips unrecognized top-level and variable fields to internal schema
- Name de-duplication with numeric suffix on collision
- Directory batch import with success/failure summary
- `espansr import <path>` CLI command
- GUI Import toolbar button with file dialog
- 15 tests in `tests/test_import.py`
- **Spec:** `/specs/template-import.md` — **Tasks:** `/tasks/template-import.md`

### Issue #6 — Espanso Config Validation
- `validate_template()` and `validate_all()` in `espansr/integrations/validate.py`
- Validation rules: empty trigger, short trigger, bad prefix, unmatched placeholders, unused variables, duplicate triggers
- Sync blocks on errors, proceeds with warnings
- `espansr validate` CLI command
- GUI surfaces validation messages in status bar
- 18 tests in `tests/test_validate.py`
- **Spec:** `/specs/espanso-config-validation.md` — **Tasks:** `/tasks/espanso-config-validation.md`

### Issue #5 — Espanso Launcher Trigger
- `generate_launcher_file()` writes `espansr-launcher.yml` with shell trigger
- WSL2-aware command construction (`wsl.exe -d DISTRO`)
- Configurable trigger keyword (`config.espanso.launcher_trigger`)
- `install.sh` generates launcher during install
- GUI first-run tip when launcher file is missing
- 10 tests in `tests/test_launcher.py`
- **Spec:** `/specs/espanso-launcher-trigger.md` — **Tasks:** `/tasks/espanso-launcher-trigger.md`

### Issue #4 — Inline Variable Editor
- `VariableEditorWidget` with add/edit/delete variable rows
- Name validation (alphanumeric + underscores, unique per template)
- Date-type format field, form-type multiline toggle
- Live YAML preview updates on every change
- 22 tests in `tests/test_variable_editor.py`
- **Spec:** `/specs/variable-editor.md` — **Tasks:** `/tasks/variable-editor.md`

### Issue #3 — GUI Single-Screen Layout
- Replaced two-panel layout with splitter (browser | editor)
- Toolbar with Sync Now, auto-sync toggle
- Inline template editor (name, trigger, content, save)
- Inline delete confirmation (no `QMessageBox`)
- Window geometry + last-template persistence
- 9 tests in `tests/test_gui_single_screen.py`, 8 tests in `tests/test_gui_editor.py`
- **Spec:** `/specs/gui-single-screen.md` — **Tasks:** `/tasks/gui-single-screen.md`

### Issue #2 — Espanso Path Consolidation
- `get_espanso_config_dir()` persists resolved path to config
- `clean_stale_espanso_files()` removes managed files from non-canonical dirs
- `install.sh` stale cleanup step
- 15 tests in `tests/test_path_consolidation.py`, additional in `tests/test_espanso.py`
- **Spec:** `/specs/espanso-path-consolidation.md` — **Tasks:** `/tasks/espanso-path-consolidation.md`

### Issue #1 — WSL/Platform Utility Module
- `espansr/core/platform.py`: `get_platform()`, `is_wsl2()`, `is_windows()`, `get_wsl_distro_name()`, `get_windows_username()`
- All callers refactored to import from `platform.py`
- 24 tests in `tests/test_platform.py`
- **Spec:** `/specs/wsl-platform-utility.md` — **Tasks:** `/tasks/wsl-platform-utility.md`

### v0.1.0 — Initial Standalone Build
- Template CRUD with JSON storage
- Espanso YAML generation
- CLI and GUI interfaces
- CI/CD with GitHub Actions (Python 3.11–3.12)
- Governance docs (AGENTS.md)

### Colored CLI Output
- `cli_color.py` utility with ok(), warn(), fail(), info() helpers
- Colors applied to doctor, status, validate, and setup output
- Auto-detects TTY and NO_COLOR env
- 7 tests in `tests/test_cli_color.py`
- **Spec:** `/specs/cli-colored-output.md` — **Tasks:** `/tasks/cli-colored-output.md`

### GUI Template Preview Pane
- `_output_preview` QPlainTextEdit below YAML preview in template editor
- Replaces `{{var}}` with defaults, labels (fallback), or formatted dates
- Live updates on content and variable changes
- 7 tests in `tests/test_gui_editor.py`
- **Spec:** `/specs/gui-template-preview.md` — **Tasks:** `/tasks/gui-template-preview.md`

### Setup and Platform Resilience
- Bundled template path fallback to importlib.resources
- `espansr setup --strict` returns 1 if Espanso not found
- Bundled templates validated during setup
- Platform config caching with @lru_cache
- 8 tests in `tests/test_setup_resilience.py`
- **Spec:** `/specs/setup-platform-resilience.md` — **Tasks:** `/tasks/setup-platform-resilience.md`

## Summary

| # | Feature | Spec | Status |
|---|---------|------|--------|
| 1 | WSL/Platform Utility | `/specs/wsl-platform-utility.md` | Complete |
| 2 | Espanso Path Consolidation | `/specs/espanso-path-consolidation.md` | Complete |
| 3 | GUI Single-Screen Layout | `/specs/gui-single-screen.md` | Complete |
| 4 | Inline Variable Editor | `/specs/variable-editor.md` | Complete |
| 5 | Espanso Launcher Trigger | `/specs/espanso-launcher-trigger.md` | Complete |
| 6 | Espanso Config Validation | `/specs/espanso-config-validation.md` | Complete |
| 7 | Template Import | `/specs/template-import.md` | Complete |
| 8 | Cross-Platform Installer | `/specs/install-first-run.md` | Complete |
| 9 | Windows Installer | `/specs/windows-installer.md` | Complete |
| 10 | First Public Release (v1.0) | `/specs/first-public-release.md` | Complete |
| 11 | `espansr doctor` | `/specs/cli-doctor.md` | Complete |
| 12 | CLI dry-run & verbose | `/specs/cli-dry-run-verbose.md` | Complete |
| 13 | Colored CLI output | `/specs/cli-colored-output.md` | Complete |
| 14 | Shell tab completion | `/specs/cli-tab-completion.md` | Not started |
| 15 | Setup/platform resilience | `/specs/setup-platform-resilience.md` | Complete |
| 16 | GUI status bar & feedback | `/specs/gui-status-bar-feedback.md` | Complete |
| 17 | GUI template preview | `/specs/gui-template-preview.md` | Complete |
| 18 | GUI dark/light mode | `/specs/gui-dark-mode.md` | Not started |
| 19 | GUI keyboard shortcuts | `/specs/gui-keyboard-shortcuts.md` | Not started |

**v1.0 total tests: 230 passing** (as of 2026-02-28)
