# Feature: GUI Persistent Status Bar and Sync Feedback

**Status:** Complete

## Description

Two related GUI improvements that make the application's state visible at all times:

**1. Persistent Espanso status indicator.** The status bar currently shows transient messages (sync result, tips) that disappear after a timeout. Add a permanent left-side indicator showing whether Espanso is detected (`Espanso: connected` / `Espanso: not found`). This updates on launch and after each sync.

**2. Sync result toast notification.** After clicking "Sync Now", display a richer feedback message: "Synced N templates to Espanso" on success, or the specific error/warning. The current implementation shows "Sync successful" which doesn't tell the user *what* was synced.

## Acceptance Criteria

- [x] The status bar has a permanent widget on the left showing `Espanso: <path>` or `Espanso: not found`
- [x] The permanent widget updates after `espansr setup` is detected or after a manual sync
- [x] After a successful sync, the status bar shows "Synced N template(s) to Espanso" with the actual count
- [x] After a failed sync, the status bar shows the reason (e.g., "Sync blocked: 2 validation errors")
- [x] Transient messages (sync result, import result) still disappear after their timeout; the permanent indicator remains visible
- [x] Status bar indicator is testable via `pytest-qt` (widget text can be asserted)

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `espansr/ui/main_window.py` — add permanent status widget, update sync feedback messages |
| **Modify** | `espansr/integrations/espanso.py` — `sync_to_espanso()` should return a count or result object (not just bool) |
| **Modify** | `tests/test_gui_single_screen.py` — add tests for status bar state |

## Constraints

- No new dependencies
- The permanent indicator must not interfere with transient `showMessage()` calls — use `QLabel` added to `QStatusBar` as a permanent widget, which coexists with `showMessage()`
- Status bar must be readable in both dark and light themes

## Out of Scope

- Real-time Espanso process monitoring (checking if `espanso` daemon is running)
- Notification popups outside the main window (system tray, OS notifications)

## Dependencies

None.

## Notes

`QStatusBar` supports permanent widgets via `addPermanentWidget(QLabel)`. Transient messages (`showMessage`) overlay the permanent widgets temporarily, then the permanent widgets reappear.

Current `sync_to_espanso()` returns `bool`. Changing it to return a dataclass (`SyncResult(success: bool, count: int, errors: list)`) gives both the CLI and GUI richer information. This is a mild API change — the CLI handler in `cmd_sync` would need a 1-line update.

Recommended: 3 tasks (SyncResult refactor → permanent status widget → sync feedback). 1–2 sessions.
