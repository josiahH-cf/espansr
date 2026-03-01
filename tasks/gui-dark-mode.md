# Tasks: gui-dark-mode

**Spec:** /specs/gui-dark-mode.md

## Status

- Total: 3
- Complete: 0
- Remaining: 3

## Task List

### Task 1: Complete light theme + detect_system_theme()

- **Files:** `espansr/ui/theme.py`, `tests/test_theme.py`
- **Done when:** `LIGHT_THEME` has full widget coverage matching `DARK_THEME`, `detect_system_theme()` returns `"dark"` or `"light"`, and `get_theme_stylesheet("auto", ...)` resolves to a concrete stylesheet
- **Criteria covered:** AC 1 (LIGHT_THEME fully implemented), AC 2 (system detection), AC 7 (tests)
- **Status:** [ ] Not started

### Task 2: Config default change + auto-theme wiring

- **Files:** `espansr/core/config.py`, `tests/test_theme.py`
- **Done when:** `UIConfig.theme` defaults to `"auto"`, explicit `"dark"` / `"light"` still work, existing test suite passes
- **Criteria covered:** AC 3 (explicit override), AC 4 (auto default)
- **Status:** [ ] Not started

### Task 3: Runtime theme switcher in toolbar

- **Files:** `espansr/ui/main_window.py`, `tests/test_theme.py`
- **Done when:** A `QComboBox` in the toolbar allows switching between Auto/Dark/Light at runtime; changing it re-applies the stylesheet and persists the choice
- **Criteria covered:** AC 5 (runtime switching), AC 6 (visual correctness)
- **Status:** [ ] Not started

## Test Strategy

| Acceptance Criterion | Test Location |
|---|---|
| AC 1 – LIGHT_THEME widget coverage | `test_theme.py::test_light_theme_widget_coverage` |
| AC 2 – System detection | `test_theme.py::test_detect_system_theme_*` |
| AC 3 – Explicit override | `test_theme.py::test_explicit_theme_override` |
| AC 4 – Auto default | `test_theme.py::test_auto_is_default` |
| AC 5 – Runtime switching | `test_theme.py::test_theme_combo_*` |
| AC 7 – Existing dark tests pass | Existing `test_gui_single_screen.py` |

## Session Log

