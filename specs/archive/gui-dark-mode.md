# Feature: GUI System Theme Detection (Dark/Light Mode)

**Status:** Complete

## Description

Detect the operating system's color scheme preference and apply the matching theme automatically. Currently the app defaults to dark theme with a stubbed-out light theme (`LIGHT_THEME` in `theme.py` contains only a background/text color and a `TODO` comment). This spec completes the light theme and adds automatic detection.

## Acceptance Criteria

- [x] `LIGHT_THEME` in `theme.py` is fully implemented with the same widget coverage as `DARK_THEME` (buttons, lists, scrollbars, status bar, toolbar, etc.)
- [x] On launch, the app detects the system color scheme via `QPalette` or `QStyleHints` and selects `"dark"` or `"light"` accordingly
- [x] If `config.ui.theme` is explicitly set to `"dark"` or `"light"`, the explicit setting overrides auto-detection
- [x] A new `config.ui.theme` value `"auto"` (the new default) means "follow the system"
- [x] The theme can be changed at runtime via a toolbar dropdown or menu item without restarting the app
- [x] All widget types render correctly in both themes (verified by visual inspection checklist)
- [x] Existing dark-theme tests pass; new tests verify light theme applies without error

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `espansr/ui/theme.py` — complete `LIGHT_THEME`, add `detect_system_theme()` |
| **Modify** | `espansr/ui/main_window.py` — add theme selector widget, call `detect_system_theme()` on init |
| **Modify** | `espansr/core/config.py` — change `UIConfig.theme` default from `"dark"` to `"auto"` |
| **Modify** | `tests/test_gui_single_screen.py` or new `tests/test_theme.py` — theme switching tests |

## Constraints

- No new dependencies — uses PyQt6's built-in `QStyleHints.colorScheme()` (Qt 6.5+) or `QPalette` luminance check
- Must degrade gracefully on Qt versions without `colorScheme()` — fall back to dark theme
- Light theme should use a professional, accessible color palette (WCAG AA contrast)

## Out of Scope

- Per-widget theme customization
- User-defined custom themes (only `dark`, `light`, `auto`)
- Real-time OS theme change detection while the app is running (only detected at launch or on manual switch)

## Dependencies

None.

## Notes

The current `LIGHT_THEME` stub:
```python
LIGHT_THEME = """
QMainWindow, QWidget {
    background-color: #ffffff;
    color: #1e1e1e;
}
/* TODO: Complete light theme */
"""
```

This needs ~200 lines of CSS to match `DARK_THEME`'s widget coverage. The VS Code "Light Modern" theme is a good reference for color values.

`QStyleHints.colorScheme()` returns `Qt.ColorScheme.Dark` or `Qt.ColorScheme.Light` on Qt 6.5+. For older Qt 6.x, check `QPalette.color(QPalette.ColorRole.Window).lightness() < 128`.

Recommended: 3 tasks (complete light theme → auto-detection → runtime switcher). 2 sessions.
