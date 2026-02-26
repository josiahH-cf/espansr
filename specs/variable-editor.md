# Spec: Add Inline Variable Editor to Template Editor Panel

**Issue:** #4  
**Status:** Draft

## Description

Add a "Variables" section to the template editor panel (from Issue #3). Users can add, edit, and remove template variables through an inline UI — no JSON hand-editing required. Each variable has a name, type (form/date), and default value. Changes update the live YAML preview and are persisted when the template is saved.

## Acceptance Criteria

- [ ] A "Variables" section appears below the content editor with an "Add Variable" button; clicking it adds an inline row with name, type dropdown (form/date), and default value fields
- [ ] Each variable row has edit (inline) and delete controls; deleting a variable removes it from the list immediately
- [ ] Variable names are validated: non-empty, alphanumeric plus underscores only, unique within the template; invalid names show an inline error message
- [ ] A live YAML preview panel shows the Espanso match entry (trigger + content + vars) and updates on every change to trigger, content, or variables
- [ ] Date-type variables show a format parameter field (e.g., `%Y-%m-%d`); form-type variables show a multiline toggle
- [ ] Saving the template persists all variable data (name, label, default, type, multiline, params) to the template JSON file
- [ ] Loading a template with existing variables populates the variable rows correctly

## Affected Areas

| Area | Files |
|------|-------|
| **Create** | `automatr_espanso/ui/variable_editor.py` — new widget for variable list + add/edit/delete |
| **Modify** | `automatr_espanso/ui/template_editor.py` — integrate variable editor + YAML preview |
| **Modify** | `automatr_espanso/ui/theme.py` — styles for variable rows, type dropdown |
| **Create** | `tests/test_variable_editor.py` — widget-level tests for variable CRUD and validation |

## Constraints

- Must integrate cleanly into the editor panel layout from Issue #3
- Reuse `_build_espanso_var_entry()` and `_convert_to_espanso_placeholders()` from `espanso.py` for YAML preview generation
- Variable data model is the existing `Variable` dataclass — no schema changes
- `Variable.label` auto-generates from `name` if empty (existing behavior); UI should show the auto-generated label as a placeholder

## Out of Scope

- New variable types beyond form and date
- Variable reordering (drag-and-drop)
- Variable grouping or sections
- Content-aware variable detection (auto-detecting `{{placeholders}}` in content)

## Dependencies

- Issue #3 (GUI overhaul) — provides the editor panel layout this feature extends

## Notes

- The `Variable` dataclass (at `templates.py` L18) has fields: `name`, `label`, `default`, `multiline`, `type` ("form"/"date"), `params`
- The existing `trigger_editor.py` has YAML preview logic at lines 95–115 — this code moves to the new inline editor
- `_build_espanso_var_entry()` in `espanso.py` L35 handles form→layout and date→params conversion
- The variable list can be a `QVBoxLayout` of row widgets — keep it lightweight
