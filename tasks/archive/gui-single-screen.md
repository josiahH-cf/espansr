# Tasks: GUI Overhaul — Single-Screen Layout with Inline Template Editor

**Spec:** `/specs/gui-single-screen.md`
**Branch:** `feat/3-gui-single-screen`

## Task 1 — Write failing tests

**File:** `tests/test_gui_single_screen.py`

- Test `TemplateEditorWidget` clears all fields when "New Template" is clicked
- Test selecting a template in the browser loads name, trigger, content into the editor
- Test Save button persists name/trigger/content to the template JSON on disk
- Test Delete button shows an inline confirmation widget (not `QMessageBox`)
- Test confirming delete removes the template from the list and disk
- Test cancelling delete leaves the template in the list
- Test toolbar contains a "Sync Now" button
- Test pressing Sync Now calls `sync_to_espanso()` (mocked)
- Test window geometry is restored from `UIConfig` on second launch
- Test `UIConfig.last_template` causes that template to be selected on launch

**Done when:** All tests exist and fail (TemplateEditorWidget does not exist yet).

## Task 2 — Create `template_editor.py` and simplify `template_browser.py`

**Files:** `espansr/ui/template_editor.py` (new), `espansr/ui/template_browser.py` (modify)

### template_editor.py

New `TemplateEditorWidget(QWidget)`:
- Name `QLineEdit`
- Trigger `QLineEdit` (placeholder `:mytrigger`)
- Content `QPlainTextEdit` (multiline, editable)
- "Save" `QPushButton` — calls `TemplateManager.save()`, emits `template_saved(Template)`
- "New Template" `QPushButton` — clears all fields, emits `new_template_requested()`
- `load_template(template)` — populates fields
- `clear()` — empties all fields
- `get_current_template()` — returns edited Template or None

### template_browser.py

- Remove: content preview pane, trigger display row
- Add: "Delete" `QPushButton` emitting `delete_requested(Template)`
- Keep: search bar, tree, refresh button, `template_selected` signal, `status_message` signal
- Add: `delete_requested = pyqtSignal(object)`

**Done when:** Task 1 tests for editor and delete signal pass.

## Task 3 — Rewrite `main_window.py`

**File:** `espansr/ui/main_window.py`

- Replace right splitter pane with `TemplateEditorWidget`
- Add `QToolBar` with: "Sync Now" button, auto-sync toggle `QCheckBox`, last-sync `QLabel`
- Wire signals: `browser.template_selected → editor.load_template`, `browser.delete_requested → _handle_delete`, `editor.template_saved → browser.refresh + save last_template`, `editor.new_template_requested → editor.clear`
- Inline delete confirm: `QFrame` inside browser area with Confirm/Undo buttons (no `QMessageBox`)
- Geometry persistence: save/restore `window_x`, `window_y`, `window_maximized`, `window_geometry`
- `last_template` restore: call `browser.select_template_by_name()` on startup if set
- Move auto-sync `QTimer` from `SyncPanelWidget` into `MainWindow`

**Done when:** Sync toolbar tests and geometry persistence tests pass.

## Task 4 — Remove stale files and update theme

**Files:** `espansr/ui/sync_panel.py` (delete), `espansr/ui/trigger_editor.py` (delete), `espansr/ui/theme.py` (modify)

- Delete `sync_panel.py` and `trigger_editor.py`
- Remove any remaining imports of `SyncPanelWidget` or `TriggerEditorDialog`
- Add theme styles for toolbar, editor panel, inline confirm widget
- Full test suite green

**Done when:** No dead imports remain, theme covers new widgets, all tests pass.

## Progress

| Task | Status |
|------|--------|
| 1    | Complete |
| 2    | Complete |
| 3    | Complete |
| 4    | Complete |
