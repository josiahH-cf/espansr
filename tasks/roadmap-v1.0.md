# Roadmap — Espansr v1.0

## Backlog

> Each item below requires scoping (`/specs/`) before implementation begins.
> See the Feature Lifecycle in `/AGENTS.md`.

_Backlog empty — all planned features complete._

## Active

_No active work._

## Completed

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

## Summary

| # | Feature | Spec | Tasks | Tests | Status |
|---|---------|------|-------|-------|--------|
| 1 | WSL/Platform Utility | `/specs/wsl-platform-utility.md` | `/tasks/wsl-platform-utility.md` | 33 | Complete |
| 2 | Espanso Path Consolidation | `/specs/espanso-path-consolidation.md` | `/tasks/espanso-path-consolidation.md` | 15+ | Complete |
| 3 | GUI Single-Screen Layout | `/specs/gui-single-screen.md` | `/tasks/gui-single-screen.md` | 17 | Complete |
| 4 | Inline Variable Editor | `/specs/variable-editor.md` | `/tasks/variable-editor.md` | 22 | Complete |
| 5 | Espanso Launcher Trigger | `/specs/espanso-launcher-trigger.md` | `/tasks/espanso-launcher-trigger.md` | 10 | Complete |
| 6 | Espanso Config Validation | `/specs/espanso-config-validation.md` | `/tasks/espanso-config-validation.md` | 18 | Complete |
| 7 | Template Import | `/specs/template-import.md` | `/tasks/template-import.md` | 15 | Complete |
| 8 | Cross-Platform Installer | `/specs/install-first-run.md` | `/tasks/install-first-run.md` | 21 | Complete |
| — | CI Hardening | — | — | — | Complete |
| — | Lint Cleanup | — | — | — | Complete |
| 9 | Windows Installer | `/specs/windows-installer.md` | `/tasks/windows-installer.md` | — | Complete |
| 10 | First Public Release | `/specs/first-public-release.md` | `/tasks/first-public-release.md` | 9 | Complete |
| — | **Human action** | Tag v1.0.0 on GitHub | — | — | Pending |

**Total tests: 167 passing** (as of 2026-02-28)
