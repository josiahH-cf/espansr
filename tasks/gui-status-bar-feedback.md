# Tasks: GUI Persistent Status Bar and Sync Feedback

**Spec:** /specs/gui-status-bar-feedback.md

## Status

- Total: 3
- Complete: 3
- Remaining: 0

## Task List

### Task 1: Refactor `sync_to_espanso()` to return `SyncResult`

- **Files:** `espansr/integrations/espanso.py`, `espansr/__main__.py`, `tests/test_gui_single_screen.py`
- **Done when:** `sync_to_espanso()` returns a `SyncResult(success: bool, count: int, errors: list[str])` dataclass; CLI `cmd_sync` still works correctly; existing GUI `_do_sync` still calls `sync_to_espanso()` and handles the new return type; all existing tests pass without modification.
- **Criteria covered:** Prerequisite for richer sync feedback in GUI.
- **Status:** [x] Complete

#### Implementation details

1. Add `SyncResult` dataclass to `espansr/integrations/espanso.py`:
   ```python
   @dataclass
   class SyncResult:
       success: bool
       count: int
       errors: list[str]
   ```
2. Change `sync_to_espanso()` to return `SyncResult` instead of `bool`.
   - Success: `SyncResult(success=True, count=len(matches), errors=[])`
   - No match dir: `SyncResult(success=False, count=0, errors=["Could not find Espanso config directory"])`
   - Validation errors: `SyncResult(success=False, count=0, errors=[...error messages...])`
   - Write error: `SyncResult(success=False, count=0, errors=[str(e)])`
3. Update `cmd_sync()` in `__main__.py` to use `result.success` instead of bare `bool`.
4. Update `_do_sync()` in `main_window.py` to use `result.success` and `result.count`.
5. Fix any test mocks that assert `sync_to_espanso` returns `bool` — they should now return a `SyncResult`.

### Task 2: Add permanent Espanso status indicator to status bar

- **Files:** `espansr/ui/main_window.py`, `tests/test_gui_single_screen.py`
- **Done when:** Status bar has a permanent `QLabel` on the left showing `Espanso: <path>` or `Espanso: not found`; the label updates on launch; the label is accessible for test assertions; all existing tests pass.
- **Criteria covered:** Permanent status widget; testable via pytest-qt.
- **Status:** [x] Complete

#### Implementation details

1. In `_setup_ui()`, after creating the status bar, add a `QLabel` as a permanent widget:
   ```python
   from PyQt6.QtWidgets import QLabel
   self._espanso_status = QLabel()
   self.statusBar().addPermanentWidget(self._espanso_status)
   ```
2. Add `_update_espanso_status()` method that reads `get_espanso_config_dir()` and sets the label text.
3. Call `_update_espanso_status()` at the end of `__init__`.
4. Add test: `test_espanso_status_label_shows_path` — mock `get_espanso_config_dir` to return a path, assert label text contains the path.
5. Add test: `test_espanso_status_label_shows_not_found` — mock `get_espanso_config_dir` to return None, assert label text contains "not found".

### Task 3: Show sync count in status bar feedback

- **Files:** `espansr/ui/main_window.py`, `tests/test_gui_single_screen.py`
- **Done when:** After a successful sync, status bar shows "Synced N template(s) to Espanso"; after a failed sync with validation errors, status bar shows "Sync blocked: N validation error(s)"; permanent Espanso indicator updates after sync; all tests pass.
- **Criteria covered:** Sync result toast with count; status bar updates after sync; failed sync shows reason.
- **Status:** [x] Complete

#### Implementation details

1. In `_do_sync()`, use `_last_sync_count` for the success message:
   - Success: `f"Synced {result.count} template(s) to Espanso"`
   - Blocked by errors: `f"Sync blocked: {len(errors)} validation error(s)"`
2. Call `_update_espanso_status()` after sync completes (in case Espanso path changed).
3. Add test: `test_sync_success_shows_count` — mock `sync_to_espanso` to return `SyncResult(success=True, count=3, errors=[])`, assert status bar contains "Synced 3".
4. Add test: `test_sync_blocked_shows_error_count` — mock `validate_all` to return errors, assert status bar contains "blocked".
5. Update existing `test_sync_success_shows_status_message` if the message text changed (it checks for "successful" — now will be "Synced").

## Test Strategy

| Criterion | Task | Test |
|-----------|------|------|
| SyncResult return type | 1 | Existing sync tests adapted to new return type |
| Permanent status widget exists | 2 | `test_espanso_status_label_shows_path` |
| Widget shows path or not found | 2 | `test_espanso_status_label_shows_not_found` |
| Sync count in message | 3 | `test_sync_success_shows_count` |
| Blocked sync shows reason | 3 | `test_sync_blocked_shows_error_count` |
| Status updates after sync | 3 | `test_espanso_status_updates_after_sync` |
| Transient messages coexist | 2 | Existing tests — transient messages still work |

## Session Log

