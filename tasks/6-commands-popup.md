# Tasks: 6-commands-popup

**Feature ID:** 6-commands-popup
**Spec:** /specs/6-commands-popup.md

## Status

- Total: 5
- Complete: 5
- Remaining: 0
- Blocked: 0

## Pre-Implementation Tests

| AC | Test File | Status |
|----|-----------|--------|
| AC-1 | tests/test_launcher.py::test_generate_commands_popup_creates_valid_yaml | [x] Written |
| AC-1 | tests/test_setup.py::test_setup_generates_commands_popup_when_espanso_found | [x] Written |
| AC-2 | tests/test_commands_popup.py::test_build_command_catalog_includes_template_and_system_triggers | [x] Written |
| AC-3 | tests/test_commands_popup.py::test_commands_popup_dialog_renders_entries | [x] Written |
| AC-4 | tests/test_commands_popup.py::test_commands_popup_dialog_closes_on_escape | [x] Written |
| AC-5 | tests/test_doctor.py::test_doctor_reports_commands_popup_file_missing | [x] Written |
| AC-5 | tests/test_path_consolidation.py::test_clean_stale_deletes_commands_popup_file_from_noncanonical | [x] Written |

## Task List

### T-1: Create shared command catalog

- **Files:** `espansr/core/command_catalog.py`
- **Test File:** `tests/test_commands_popup.py`
- **Done when:** A normalized catalog exists for template and system triggers with stable sorting and preview text.
- **Criteria covered:** AC-2, AC-3
- **Branch:** `copilot/feat-command-catalog`
- **Status:** [x] Complete

### T-2: Add popup-only UI

- **Files:** `espansr/ui/commands_popup.py`
- **Test File:** `tests/test_commands_popup.py`
- **Done when:** The popup renders standardized rows, scrolls, and closes on `Esc`.
- **Criteria covered:** AC-3, AC-4
- **Branch:** `copilot/feat-commands-popup-ui`
- **Status:** [x] Complete

### T-3: Wire CLI popup launch path

- **Files:** `espansr/__main__.py`
- **Test File:** `tests/test_commands_popup.py`
- **Done when:** `espansr gui --view commands` launches the popup path without launching the full editor.
- **Criteria covered:** AC-1, AC-4
- **Branch:** `copilot/feat-commands-popup-cli`
- **Status:** [x] Complete

### T-4: Generate and manage `:coms` trigger file

- **Files:** `espansr/integrations/espanso.py`, `espansr/__main__.py`
- **Test File:** `tests/test_launcher.py`, `tests/test_setup.py`, `tests/test_doctor.py`, `tests/test_path_consolidation.py`
- **Done when:** `espansr-commands.yml` is generated, checked by doctor, and cleaned up as an espansr-managed file.
- **Criteria covered:** AC-1, AC-5
- **Branch:** `copilot/feat-commands-popup-trigger`
- **Status:** [x] Complete

### T-5: Update docs and changelog

- **Files:** `docs/CLI.md`, `docs/TEMPLATES.md`, `docs/VERIFY.md`, `CHANGELOG.md`
- **Test File:** N/A
- **Done when:** User docs explain `:coms`, popup scope, and verification steps.
- **Criteria covered:** AC-1 through AC-5
- **Branch:** `copilot/docs-commands-popup`
- **Status:** [x] Complete

## Routing Plan

| Task | Suggested Model | Rationale | Reviewer | Parallel? | Context Needs |
|------|-----------------|-----------|----------|-----------|---------------|
| T-1 | Copilot | Small core abstraction from existing template metadata | Claude | Yes (with T-2) | Small |
| T-2 | Copilot | UI work fits existing PyQt patterns | Claude | Yes (with T-1) | Medium |
| T-3 | Copilot | Localized CLI/parser edit | Claude | No — depends on T-2 | Small |
| T-4 | Copilot | Reuses existing launcher generation patterns | Claude | No — depends on T-3 | Medium |
| T-5 | Copilot | Documentation pass after behavior is locked | Claude | Yes (after T-4) | Small |

## Test Strategy

- AC-1: `tests/test_launcher.py::test_generate_commands_popup_creates_valid_yaml`, `tests/test_setup.py::test_setup_generates_commands_popup_when_espanso_found`
- AC-2: `tests/test_commands_popup.py::test_build_command_catalog_includes_template_and_system_triggers`
- AC-3: `tests/test_commands_popup.py::test_commands_popup_dialog_renders_entries`
- AC-4: `tests/test_commands_popup.py::test_commands_popup_dialog_closes_on_escape`
- AC-5: `tests/test_doctor.py::test_doctor_reports_commands_popup_file_missing`, `tests/test_path_consolidation.py::test_clean_stale_deletes_commands_popup_file_from_noncanonical`

## Evidence Log

- 2026-04-14 T-1 through T-5 — commands run: `pytest tests/test_commands_popup.py tests/test_launcher.py tests/test_setup.py tests/test_doctor.py tests/test_path_consolidation.py tests/test_dry_run.py tests/test_setup_resilience.py -q`, result: pass, notes: 89 passed in focused verification
- 2026-04-14 T-1 through T-5 — commands run: `pytest -q`, result: partial, notes: 396 passed / 6 failed in unrelated baseline Windows tests (`test_get_config_dir_triggers_migration`, three `test_release` README encoding failures, two `test_remote_remove_*` permission failures)
- 2026-04-14 T-1 through T-5 — commands run: `python -m ruff check .`, `python -m black --check .`, result: not run, notes: `ruff` and `black` are not installed in the current virtual environment

## Session Log

| Date | Last Completed | Next Action | Blockers | State Link |
|------|---------------|-------------|----------|------------|
| 2026-04-14 | T-1 through T-5 complete | Review / ship | Full-suite baseline failures outside feature scope; ruff/black missing from current venv | [workflow/STATE.json](../workflow/STATE.json) |
