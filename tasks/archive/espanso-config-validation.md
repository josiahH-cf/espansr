# Tasks: Validate Espanso Config Before Sync and Surface Errors in UI

**Spec:** `/specs/espanso-config-validation.md`
**Branch:** `feat/espanso-config-validation`

## Task 1 — Write failing tests for validation module

**File:** `tests/test_validate.py`

- Test `validate_template()` returns empty list for valid template
- Test error on empty trigger string
- Test warning on trigger not starting with `:` or `/`
- Test error on trigger shorter than 2 characters
- Test warning for `{{var}}` placeholder in content with no matching variable
- Test warning for variable defined but never referenced in content
- Test `validate_all()` detects duplicate triggers across templates
- Test `validate_all()` returns errors and warnings from multiple templates
- Test `ValidationWarning` has severity, message, and template_name fields
- Test `sync_to_espanso()` blocks on validation errors (mocked)
- Test `sync_to_espanso()` proceeds with warnings only (mocked)
- Test CLI `validate` command returns 0 on clean, 1 on errors

**Done when:** All tests exist and fail (validate module doesn't exist yet).

## Task 2 — Create `validate.py` and make unit tests pass

**File:** `espansr/integrations/validate.py`

- `ValidationWarning` dataclass: `severity` ("error"/"warning"), `message`, `template_name`
- `validate_template(template) -> list[ValidationWarning]` — single-template checks
- `validate_all() -> list[ValidationWarning]` — all templates + cross-template checks
- Rules: empty trigger, short trigger, bad prefix, unmatched placeholders, unused variables, duplicate triggers

**Done when:** All `test_validate.py` unit tests pass.

## Task 3 — Wire validation into sync, CLI, and UI

**Files:** `espansr/integrations/espanso.py`, `espansr/__main__.py`, `espansr/ui/main_window.py`

- `sync_to_espanso()`: call `validate_all()`, block on errors, print warnings
- `__main__.py`: add `cmd_validate()` and `validate` subcommand
- `main_window.py`: show validation messages in status bar after sync
- All tests pass

**Done when:** Integration tests pass, full test suite green.

## Progress

| Task | Status |
|------|--------|
| 1    | Complete |
| 2    | Complete |
| 3    | Complete |
