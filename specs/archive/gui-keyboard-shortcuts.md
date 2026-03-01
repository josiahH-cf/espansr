# Feature: GUI Keyboard Shortcuts

**Status:** Complete

## Description

Add keyboard shortcuts for common actions in the GUI so power users can work without reaching for the mouse. Shortcuts are discoverable via tooltip text on toolbar buttons and (optionally) a menu bar.

## Acceptance Criteria

- [x] `Ctrl+S` triggers "Sync Now" (same as clicking the Sync button)
- [x] `Ctrl+N` creates a new template (clears the editor)
- [x] `Ctrl+I` opens the import file dialog
- [x] `Ctrl+F` focuses the template search/filter field in the browser (if one exists) or the template list
- [x] `Delete` or `Ctrl+D` deletes the currently selected template (with the existing inline confirmation)
- [x] All shortcuts work regardless of which widget has focus
- [x] Toolbar button tooltips show the shortcut (e.g., "Sync Now (Ctrl+S)")
- [x] Shortcuts do not conflict with standard Qt text editing shortcuts (Ctrl+C, Ctrl+V, Ctrl+Z, etc.)

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `espansr/ui/main_window.py` — register `QShortcut` instances, update tooltip text |
| **Modify** | `espansr/ui/template_browser.py` — expose `focus_search()` or `delete_selected()` methods if needed |
| **Create** | `tests/test_gui_shortcuts.py` — tests that simulate key presses and verify actions fire |

## Constraints

- No new dependencies — uses `QShortcut` from PyQt6
- Must not intercept text editing shortcuts when a `QLineEdit` or `QTextEdit` has focus
- macOS convention: use `Cmd` instead of `Ctrl` — `QKeySequence.StandardKey` handles this automatically where available

## Out of Scope

- Customizable/user-remappable shortcuts
- Menu bar with full Edit/File menus (could be added later but not required for shortcuts)
- Vim/Emacs key bindings

## Dependencies

None.

## Notes

`QShortcut` with `QKeySequence` is the standard PyQt6 approach:
```python
from PyQt6.QtGui import QKeySequence, QShortcut
shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
shortcut.activated.connect(self._do_sync)
```

For `Ctrl+S`, be aware this is commonly "Save" — in our context "Sync" is the closest equivalent. If the user is editing a template's fields, `Ctrl+S` should save the template first, then sync. Or we could use `Ctrl+S` for save and `Ctrl+Shift+S` for sync. This is a UX decision to finalize during implementation.

Recommended: 2 tasks (tests → implementation). Single session.
