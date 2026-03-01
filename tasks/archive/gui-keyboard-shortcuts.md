# Tasks: GUI Keyboard Shortcuts

**Spec:** /specs/gui-keyboard-shortcuts.md

## Status

- Total: 3
- Complete: 3
- Remaining: 0

## Task List

### Task 1: Write failing tests

- **Files:** `tests/test_gui_shortcuts.py` (create)
- **Done when:** `pytest tests/test_gui_shortcuts.py` runs and all tests fail with `AttributeError` or assertion errors (not import errors)
- **Criteria covered:** All 8 acceptance criteria have at least one test
- **Status:** [x] Complete

Tests to write:
- `test_ctrl_s_triggers_sync` — simulate `Ctrl+S`, verify `_do_sync` fires
- `test_ctrl_n_clears_editor` — simulate `Ctrl+N`, verify editor cleared
- `test_ctrl_i_opens_import_dialog` — simulate `Ctrl+I`, verify import triggered
- `test_ctrl_f_focuses_search` — simulate `Ctrl+F`, verify `TemplateBrowserWidget.focus_search()` activates search field
- `test_delete_triggers_delete` — simulate `Delete`, verify `TemplateBrowserWidget.start_delete()` fires
- `test_ctrl_d_triggers_delete` — simulate `Ctrl+D`, same
- `test_sync_tooltip_includes_shortcut` — assert sync button tooltip contains `Ctrl+S`
- `test_import_tooltip_includes_shortcut` — assert import button tooltip contains `Ctrl+I`

### Task 2: Expose public methods on TemplateBrowserWidget

- **Files:** `espansr/ui/template_browser.py`
- **Done when:** `focus_search()` and `start_delete()` are public methods; Task 1 tests that exercise these no longer fail on `AttributeError`
- **Criteria covered:** Ctrl+F (focus search), Delete/Ctrl+D (delete selected)
- **Status:** [x] Complete

Changes:
- Add `focus_search(self) -> None` — sets focus to the filter `QLineEdit` and selects all text
- Rename `_start_delete` → `start_delete` (make public); update all internal callers

### Task 3: Register shortcuts and update tooltips in MainWindow

- **Files:** `espansr/ui/main_window.py`
- **Done when:** All Task 1 tests pass; `ruff check .` and `black --check .` pass; full test suite green
- **Criteria covered:** All 8 acceptance criteria
- **Status:** [x] Complete

Changes:
- Import `QShortcut`, `QKeySequence` from `PyQt6.QtGui`
- In `_setup_ui`, after toolbar buttons are created, register:
  - `QShortcut(QKeySequence.StandardKey.Save, self)` → `self._do_sync`
  - `QShortcut(QKeySequence("Ctrl+N"), self)` → `self._editor.clear`
  - `QShortcut(QKeySequence("Ctrl+I"), self)` → `self._do_import`
  - `QShortcut(QKeySequence("Ctrl+F"), self)` → `self._browser.focus_search`
  - `QShortcut(QKeySequence("Delete"), self)` → `self._browser.start_delete`
  - `QShortcut(QKeySequence("Ctrl+D"), self)` → `self._browser.start_delete`
- Update `_sync_btn` tooltip: `"Sync templates to Espanso (Ctrl+S)"`
- Update `_import_btn` tooltip: `"Import template(s) from a JSON file (Ctrl+I)"`

## Test Strategy

| Criterion | Task | Test |
|-----------|------|------|
| Ctrl+S triggers sync | 3 | `test_ctrl_s_triggers_sync` |
| Ctrl+N clears editor | 3 | `test_ctrl_n_clears_editor` |
| Ctrl+I opens import | 3 | `test_ctrl_i_opens_import_dialog` |
| Ctrl+F focuses search | 2, 3 | `test_ctrl_f_focuses_search` |
| Delete triggers delete | 2, 3 | `test_delete_triggers_delete` |
| Ctrl+D triggers delete | 2, 3 | `test_ctrl_d_triggers_delete` |
| Tooltips show shortcut | 3 | `test_sync_tooltip_includes_shortcut`, `test_import_tooltip_includes_shortcut` |

## Session Log

- **2026-03-01:** All 3 tasks complete. 8 tests passing, 290 total. Lint clean.
