# Feature: GUI Template Preview Pane

**Status:** Not started

## Description

Add a read-only preview pane to the template editor that shows the fully expanded output of the current template with example variable values filled in. This makes it concrete what the user's trigger will produce before syncing to Espanso.

When a template is selected or edited, the preview updates live — showing the content with `{{name}}` replaced by the variable's default value (or the variable label if no default is set).

## Acceptance Criteria

- [ ] The editor panel includes a "Preview" section below the YAML preview
- [ ] The preview shows the template content with all `{{var}}` placeholders replaced by their default values
- [ ] Variables with no default value use their label as the preview value (e.g., `{{name}}` → `Name`)
- [ ] The preview updates live as the user edits content or variables
- [ ] The preview is read-only (not editable by the user)
- [ ] Templates with no variables show the content as-is in the preview
- [ ] The preview is visually distinct from the editable content field (styled as read-only)

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `espansr/ui/template_editor.py` — add preview `QPlainTextEdit`, `_update_preview()` method |
| **Modify** | `tests/test_gui_editor.py` — tests for preview content |

## Constraints

- No new dependencies
- Preview must not slow down typing (debounce if needed, but likely unnecessary for simple string replacement)
- Must work with date-type variables — show `{{date}}` as a placeholder like `2026-02-28` (current date) rather than substituting the format string

## Out of Scope

- Rendering HTML or rich text in the preview
- Simulating Espanso form UI (just show the substituted plain text)
- Preview of the YAML output (already exists — this is the *user-facing* expanded content)

## Dependencies

None.

## Notes

The preview is a simple `str.replace()` loop over the variable list. For date-type variables, use `datetime.now().strftime(format)` with the configured format string (or `%Y-%m-%d` as default).

The YAML preview already exists and serves a different purpose (showing what Espanso will receive). The template preview shows what the *end user* will see when the trigger fires.

Layout consideration: the editor panel is already vertically packed (name, trigger, content, variables, YAML preview, save button). Adding another text area could feel crowded. Consider making the preview collapsible or using a tab between "YAML Preview" and "Output Preview".

Recommended: 2 tasks (tests → implementation). Single session.
