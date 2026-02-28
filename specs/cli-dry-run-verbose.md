# Feature: CLI Dry-Run and Verbose Modes

**Status:** Not started

## Description

Add `--dry-run` and `--verbose` flags to `espansr sync` and `espansr setup` so users can preview what would happen without making changes, and get detailed output when debugging issues.

`--dry-run` shows what files would be written, copied, or deleted — then exits without acting. `--verbose` increases output detail (e.g., why a template was skipped during setup, which files were synced).

## Acceptance Criteria

- [ ] `espansr sync --dry-run` lists which YAML files would be written or deleted, then exits 0 without writing anything
- [ ] `espansr setup --dry-run` lists which templates would be copied, which Espanso dir would be detected, whether launcher would be generated — without acting
- [ ] `espansr setup --verbose` prints one line per template explaining whether it was copied or skipped (and why: "already exists" vs "identical content")
- [ ] `--dry-run` and `--verbose` can be combined
- [ ] Both flags are registered in argparse help text

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `espansr/__main__.py` — add flags to `sync` and `setup` subparsers, pass to handlers |
| **Modify** | `espansr/integrations/espanso.py` — `sync_to_espanso()` accepts `dry_run` parameter |
| **Create** | `tests/test_dry_run.py` — tests for dry-run and verbose behavior |

## Constraints

- `--dry-run` must guarantee zero side effects (no file writes, no config changes)
- No new dependencies
- Existing tests must not break (default behavior unchanged when flags are absent)

## Out of Scope

- Dry-run for `espansr import` (could be added later)
- Colored output (tracked separately)
- `clean_stale_espanso_files` dry-run (small enough to add here if < 300 line diff, otherwise defer)

## Dependencies

None.

## Notes

Current `sync_to_espanso()` signature returns `bool`. The `dry_run` parameter should cause it to print the plan and return `True` without writing. The `--verbose` flag on setup maps to printing per-file decisions in `cmd_setup`.

Recommended: 3 tasks (tests → sync dry-run → setup dry-run/verbose). Can be done in 1–2 sessions.
