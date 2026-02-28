# Spec: Validate Espanso Config Before Sync and Surface Errors in UI

**Issue:** #6  
**Status:** Complete

## Description

Add a validation layer that checks templates for Espanso-incompatible patterns before syncing. Validation runs automatically before each sync and is available as a standalone function. Warnings and errors are surfaced in the GUI status bar and returned from the CLI. This catches common mistakes (empty triggers, duplicate triggers, missing variable references, invalid trigger format) before they silently produce broken Espanso config files.

## Acceptance Criteria

- [x] A `validate_template(template) -> list[ValidationWarning]` function checks a single template and returns a list of warnings/errors, each with a severity ("error" or "warning"), a message, and the template name
- [x] Validation detects: empty trigger string, trigger not starting with `:` or `/` (Espanso convention), trigger shorter than 2 characters, duplicate triggers across templates, content referencing `{{var}}` placeholders that have no matching variable defined, and variables defined but never referenced in content
- [x] A `validate_all() -> list[ValidationWarning]` function validates all triggered templates and additionally checks for cross-template issues (duplicate triggers)
- [x] `sync_to_espanso()` calls `validate_all()` before writing; errors prevent the sync and are printed to stdout; warnings are printed but do not block sync
- [x] The GUI "Sync Now" action displays validation errors/warnings in the status bar; errors show as persistent messages until the user acknowledges them
- [x] A new `espansr validate` CLI command runs `validate_all()` and prints results; exits 0 if no errors, 1 if errors found

## Affected Areas

| Area | Files |
|------|-------|
| **Create** | `espansr/integrations/validate.py` — validation logic |
| **Modify** | `espansr/integrations/espanso.py` — call validation before sync |
| **Modify** | `espansr/ui/main_window.py` — display validation results in status bar |
| **Modify** | `espansr/__main__.py` — add `validate` CLI command |
| **Create** | `tests/test_validate.py` — unit tests for all validation rules |

## Constraints

- Validation must not modify any templates or files — read-only analysis
- Validation must complete in under 100ms for 100 templates (no I/O beyond template loading)
- Validation runs synchronously — no async/threading needed at this scale
- Error severity blocks sync; warning severity does not
- Trigger format rules follow Espanso v2 conventions: starts with `:` (keyword triggers) or `/` (regex triggers)

## Out of Scope

- Full Espanso schema validation (verifying every YAML field against Espanso's internal schema)
- Auto-fixing detected issues
- Real-time validation as the user types in the editor (can be added later)
- Validating YAML syntax of already-synced files on disk
- Custom user-defined validation rules

## Dependencies

- None — uses existing `TemplateManager` and `Template`/`Variable` dataclasses

## Notes

- Espanso v2 trigger conventions: keyword triggers start with `:` (e.g., `:sig`), regex triggers start with `/` — most users use keyword triggers
- The `Template` dataclass has `trigger`, `content`, and `variables` fields needed for validation
- `iter_with_triggers()` already filters to templates with non-empty triggers — but validation should also warn about templates with content but no trigger (potential oversight)
- The `_convert_to_espanso_placeholders()` function transforms `{{var}}` to `{{var.value}}` for form types — validation should check the pre-conversion content
- `ValidationWarning` should be a simple dataclass: `severity`, `message`, `template_name`
