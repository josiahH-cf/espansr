# Feature: Toggleable YAML Preview

**Status:** Complete

## Description

The YAML preview and output preview panels in the template editor add visual clutter for users who don't need them. Add a persistent toggle so users can show or hide these preview panes. The preference is saved to config and restored on next launch, keeping the editor focused on content by default.

## Acceptance Criteria

- [x] A toggle control (toolbar button or menu item) shows/hides the YAML preview and output preview panes
- [x] The toggle state persists across sessions via `config.ui.show_previews`
- [x] When hidden, the preview panes and their labels are fully removed from the layout (no empty space)
- [x] When shown, the previews restore to their previous behavior (live-updating on content/trigger/variable changes)
- [x] The default value for new installs is `false` (previews hidden) to keep the interface clean
- [x] Keyboard shortcut toggles the preview (e.g., Ctrl+P or Ctrl+Shift+P)
- [x] The toggle state is reflected in the toolbar tooltip or button label (e.g., "Show Previews" / "Hide Previews")

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `espansr/core/config.py` — add `show_previews: bool = False` to `UIConfig` |
| **Modify** | `espansr/ui/template_editor.py` — wrap YAML preview + output preview in a container widget; add `set_previews_visible(bool)` method |
| **Modify** | `espansr/ui/main_window.py` — add toolbar toggle button, wire to config persistence |
| **Create** | `tests/test_preview_toggle.py` — verify toggle behavior, persistence, and default state |

## Constraints

- Must not break existing tests that assert on YAML preview content (those tests should still work when previews are visible)
- The toggle must not affect the variable editor — only the YAML preview and output preview panes
- No new dependencies

## Out of Scope

- Separate toggles for YAML preview vs output preview (single toggle controls both)
- Resizable preview panes (existing `setMaximumHeight` behavior is sufficient)
- Preview-related keyboard shortcuts beyond the single toggle

## Dependencies

- None — builds on existing `UIConfig` pattern and template editor layout

## Notes

The existing `UIConfig` dataclass already has `theme`, `font_size`, `splitter_sizes`, and `last_template` fields. Adding `show_previews` follows the same pattern.

Implementation approach: wrap the four preview widgets (`preview_label`, `_yaml_preview`, `output_label`, `_output_preview`) in a `QWidget` container. The toggle simply calls `container.setVisible(bool)`. Signal connections remain wired regardless of visibility — previews update silently when hidden and show current state when made visible.
