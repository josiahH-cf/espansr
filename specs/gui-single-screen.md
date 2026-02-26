# Spec: GUI Overhaul — Single-Screen Layout with Inline Template Editor

**Issue:** #3  
**Status:** Draft

## Description

Replace the current two-panel layout (template browser + sync/status panel) and the modal trigger editor dialog with a single-screen layout. The left panel is a template list with search, create, and delete. The right panel is an inline editor with trigger input, content editor, and save button. Sync moves to the toolbar. The activity log and dedicated sync panel are removed.

## Acceptance Criteria

- [ ] The right panel displays an inline editor with: template name field, trigger input, and editable content area (`QPlainTextEdit`) — no modal dialogs are used for editing
- [ ] A "New Template" button clears the editor to empty fields; saving creates a new template JSON on disk
- [ ] A "Delete" button removes the selected template from disk and the list, with an inline undo/confirmation widget (not a `QMessageBox` dialog)
- [ ] A "Sync Now" button in the toolbar calls `sync_to_espanso()` and shows the result in the status bar; auto-sync toggle is accessible from the toolbar area
- [ ] Selecting a template in the left-panel list loads its name, trigger, and content into the right-panel editor
- [ ] Saving a template (via Save button) persists name, trigger, and content to the template JSON file and refreshes the template list
- [ ] Window geometry (position, size, maximized state) and last-selected template are persisted to `UIConfig` and restored on next launch

## Affected Areas

| Area | Files |
|------|-------|
| **Rewrite** | `automatr_espanso/ui/main_window.py` — new layout with toolbar, splitter, status bar |
| **Rewrite** | `automatr_espanso/ui/template_browser.py` — simplified list (remove preview pane, add New/Delete buttons) |
| **Remove** | `automatr_espanso/ui/sync_panel.py` — functionality moves to toolbar + status bar |
| **Remove** | `automatr_espanso/ui/trigger_editor.py` — trigger editing is inline |
| **Create** | `automatr_espanso/ui/template_editor.py` — new right-panel editor widget |
| **Modify** | `automatr_espanso/ui/theme.py` — styles for new toolbar, editor widgets |
| **Modify** | `automatr_espanso/core/config.py` — wire up unused `UIConfig` fields (geometry, last_template) |

## Constraints

- Must preserve the existing dark theme aesthetic from `theme.py`
- Template list search/filter behavior must be preserved (name, trigger, description)
- Must not break `sync_to_espanso()` or any core/integration logic — UI-only change
- The `QPlainTextEdit` for content must support multiline text with reasonable performance for templates up to ~10KB
- `pytest-qt` tests must be deterministic and not rely on timers or sleeps

## Out of Scope

- Variable editing UI (that's Issue #4 — a separate "Variables" section added to this editor)
- YAML live preview (moved to Issue #4 where it makes sense alongside variable editing)
- Light theme completion (`theme.py` TODO)
- Template versioning UI
- Template folder management UI

## Dependencies

- Issue #1 (shared platform module) — used by Espanso status display in status bar

## Notes

- `UIConfig` already defines `window_x`, `window_y`, `window_maximized`, `window_geometry`, `last_template`, `expanded_folders` — these are currently unused and should be wired up
- The sync panel's `QTimer`-based auto-sync should move to `MainWindow` or a small background helper
- The activity log is dropped in this redesign (low usage, clutters screen)
- Layout target: left panel ~300px, right panel fills remaining space
- The "Edit Trigger…" button and `TriggerEditorDialog` are eliminated — the trigger `QLineEdit` lives in the editor panel permanently
