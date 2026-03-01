# Tasks: toggleable-yaml-preview

**Spec:** /specs/toggleable-yaml-preview.md

## Status

- Total: 4
- Complete: 4
- Remaining: 0

## Task List

### Task 1: Add `show_previews` to UIConfig

- **Files:** `espansr/core/config.py`
- **Done when:** `UIConfig` has `show_previews: bool = False` and round-trips through `Config.from_dict`/`to_dict`
- **Criteria covered:** Toggle state persists via `config.ui.show_previews`; default is `false`
- **Status:** [x] Complete

### Task 2: Wrap preview widgets in a togglable container

- **Files:** `espansr/ui/template_editor.py`
- **Done when:** YAML preview + output preview are inside a `QWidget` container; `set_previews_visible(bool)` shows/hides it; signal connections stay wired regardless of visibility
- **Criteria covered:** Toggle shows/hides previews; hidden means no empty space; shown restores live-updating
- **Status:** [x] Complete

### Task 3: Wire toolbar toggle and keyboard shortcut in MainWindow

- **Files:** `espansr/ui/main_window.py`
- **Done when:** Toolbar button toggles preview visibility, tooltip reflects state, Ctrl+Shift+P shortcut toggles, state persists to config on change and on close
- **Criteria covered:** Toggle control in toolbar; keyboard shortcut; tooltip/label reflects state; persistence across sessions
- **Status:** [x] Complete

### Task 4: Tests for toggle behavior, persistence, and defaults

- **Files:** `tests/test_preview_toggle.py`
- **Done when:** All acceptance criteria have at least one test; existing YAML preview tests still pass
- **Criteria covered:** All
- **Status:** [x] Complete

## Test Strategy

| Criterion | Test |
|-----------|------|
| Toggle shows/hides previews | `test_toggle_hides_and_shows_previews` |
| State persists via config | `test_toggle_persists_to_config` |
| Hidden = no empty space | `test_hidden_previews_not_visible` |
| Shown = live-updating | `test_previews_update_when_visible` |
| Default is false | `test_default_show_previews_false` |
| Keyboard shortcut | `test_shortcut_toggles_preview` |
| Tooltip reflects state | `test_toggle_button_tooltip_reflects_state` |

## Session Log

<!-- Append after each session: date, completed, blockers -->
