# Feature: `espansr doctor` Diagnostic Command

**Status:** Complete

## Description

Add a single `espansr doctor` CLI command that composes existing health checks into one consolidated diagnostic report. Modelled after `brew doctor` and `flutter doctor`, it gives users a single command to verify their installation is healthy without running `status`, `validate`, and `list` separately.

The command runs checks in sequence, printing a pass/warn/fail line for each. It exits 0 if all checks pass, 1 if any fail.

## Acceptance Criteria

- [x] `espansr doctor` prints a check for each: Python version, espansr config dir, templates found, Espanso config detected, Espanso binary found, launcher file present, template validation (0 errors)
- [x] Each line is prefixed with a status indicator: `[ok]`, `[warn]`, or `[FAIL]`
- [x] Exit code is 0 when all checks are `ok` or `warn`, 1 when any check is `FAIL`
- [x] `espansr doctor` reuses existing functions (`get_config_dir`, `get_espanso_config_dir`, `validate_all`, etc.) — no duplicated logic
- [x] The command is registered in the argparse subparsers and documented in `--help`

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `espansr/__main__.py` — add `cmd_doctor`, register subparser |
| **Create** | `tests/test_doctor.py` — tests for each check scenario |

## Constraints

- No new dependencies — uses only stdlib and existing espansr modules
- Must run without Espanso installed (degrades gracefully to `[warn]` / `[FAIL]`)
- Must complete in < 5 seconds on any platform

## Out of Scope

- Colored output (tracked in `/specs/cli-colored-output.md`)
- Auto-fix of detected issues
- Network checks

## Dependencies

None — composes existing functions.

## Notes

Existing functions to reuse:
- `get_config_dir()` from `espansr.core.config`
- `get_templates_dir()` from `espansr.core.config`
- `get_espanso_config_dir()` from `espansr.integrations.espanso`
- `get_match_dir()` from `espansr.integrations.espanso`
- `validate_all()` from `espansr.integrations.validate`
- `shutil.which("espanso")` for binary detection
- `get_platform()` from `espansr.core.platform`

Recommended implementation order within this spec: ~2 tasks (tests, then implementation). Single session.
