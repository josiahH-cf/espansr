# Roadmap — Espansr v1.0

## Backlog

> Each item below requires scoping (`/specs/`) before implementation begins.
> See the Feature Lifecycle in `/AGENTS.md`.

### CI Hardening
- Add ruff lint step to CI
- Pin dependency versions in pyproject.toml
- Add Python 3.13 to test matrix when available

### Lint Cleanup
- Run ruff check and fix all warnings
- Enforce consistent code style with black

### First Public Release (v1.0)
- README polish with screenshots and usage guide
- License file
- Tag v1.0.0 release on GitHub

## Active

_No active work — ready for next feature._

## Completed

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
| 1 | WSL/Platform Utility | `/specs/wsl-platform-utility.md` | `/tasks/wsl-platform-utility.md` | 24 | Complete |
| 2 | Espanso Path Consolidation | `/specs/espanso-path-consolidation.md` | `/tasks/espanso-path-consolidation.md` | 15+ | Complete |
| 3 | GUI Single-Screen Layout | `/specs/gui-single-screen.md` | `/tasks/gui-single-screen.md` | 17 | Complete |
| 4 | Inline Variable Editor | `/specs/variable-editor.md` | `/tasks/variable-editor.md` | 22 | Complete |
| 5 | Espanso Launcher Trigger | `/specs/espanso-launcher-trigger.md` | `/tasks/espanso-launcher-trigger.md` | 10 | Complete |
| 6 | Espanso Config Validation | `/specs/espanso-config-validation.md` | `/tasks/espanso-config-validation.md` | 18 | Complete |
| — | CI Hardening | _needs spec_ | — | — | Backlog |
| — | Lint Cleanup | _needs spec_ | — | — | Backlog |
| 7 | Template Import | `/specs/template-import.md` | `/tasks/template-import.md` | 15 | Complete |
| — | First Public Release | _needs spec_ | — | — | Backlog |

**Total tests: 126 passing** (as of 2026-02-28)
