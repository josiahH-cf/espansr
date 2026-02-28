# Tasks: template-import

**Spec:** /specs/template-import.md

## Status

- Total: 4
- Complete: 4
- Remaining: 0

## Task List

### Task 1: Core import functions

- **Files:** `espansr/core/templates.py`, `tests/test_import.py`
- **Done when:** `import_template(path)` and `import_templates(dir)` load, normalize, de-duplicate, and save templates; all unit tests pass
- **Criteria covered:** 1 (strip fields), 2 (variable mapping), 3 (name collision), 4 (directory import), 7 (malformed JSON)
- **Status:** [x] Complete

### Task 2: CLI `import` subcommand

- **Files:** `espansr/__main__.py`, `tests/test_import.py`
- **Done when:** `espansr import <path>` imports a file or directory and prints a summary; CLI tests pass
- **Criteria covered:** 5 (CLI command)
- **Status:** [x] Complete

### Task 3: GUI Import button

- **Files:** `espansr/ui/main_window.py`, `tests/test_import.py`
- **Done when:** Toolbar shows an Import button that opens a file dialog, imports selected file(s), refreshes the template list, and shows a status message
- **Criteria covered:** 6 (GUI import)
- **Status:** [x] Complete

### Task 4: Update roadmap and docs

- **Files:** `tasks/roadmap-v1.0.md`
- **Done when:** Roadmap reflects completed Template Import feature with test count and pointers to spec/tasks
- **Status:** [x] Complete

## Test Strategy

| Criterion | Test(s) |
|-----------|---------|
| 1 — strip fields | `test_import_strips_unknown_fields` |
| 2 — variable mapping | `test_import_maps_variables`, `test_import_drops_unknown_variable_fields` |
| 3 — name collision | `test_import_renames_on_collision` |
| 4 — directory import | `test_import_directory_summary` |
| 5 — CLI command | `test_cli_import_file`, `test_cli_import_directory` |
| 6 — GUI button | `test_gui_import_button_exists`, `test_gui_import_triggers_dialog` |
| 7 — malformed JSON | `test_import_malformed_json_error` |

## Session Log

### 2026-02-28
- Completed all 4 tasks in a single session
- 15 tests written and passing
- Full suite: 141 tests pass, no regressions
