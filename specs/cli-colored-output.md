# Feature: Colored CLI Output

**Status:** Not started

## Description

Add ANSI color support to CLI commands so status indicators, errors, and warnings are visually distinct. Uses only stdlib (no `colorama` or `rich`) — raw ANSI escape codes with automatic detection of terminal capabilities.

Colors are applied to `doctor`, `status`, `setup`, `validate`, and `sync` output. If stdout is not a TTY (piped or redirected), colors are suppressed automatically.

## Acceptance Criteria

- [ ] A `cli_color.py` utility module provides `ok()`, `warn()`, `fail()`, and `info()` helpers that wrap text in ANSI codes
- [ ] Colors are suppressed when stdout is not a TTY (`sys.stdout.isatty()` is False)
- [ ] Colors are suppressed when `NO_COLOR` environment variable is set (per https://no-color.org/)
- [ ] `espansr doctor` output uses green for `[ok]`, yellow for `[warn]`, red for `[FAIL]`
- [ ] `espansr validate` uses red for errors and yellow for warnings
- [ ] `espansr status` uses green for found paths and yellow/red for missing
- [ ] Existing test assertions still pass (tests typically capture output without a TTY, so colors are auto-suppressed)

## Affected Areas

| Area | Files |
|------|-------|
| **Create** | `espansr/core/cli_color.py` — color utility module |
| **Modify** | `espansr/__main__.py` — use color helpers in `cmd_doctor`, `cmd_status`, `cmd_validate`, `cmd_setup` |
| **Create** | `tests/test_cli_color.py` — unit tests for color helpers and suppression |

## Constraints

- No new dependencies — stdlib only (ANSI escape codes)
- Must respect `NO_COLOR` env var
- Must auto-detect TTY — no `--color` flag needed (but `--no-color` could be added as a stretch goal)
- On Windows (native, not WSL2), ANSI support depends on Windows Terminal or `cmd.exe` with VT processing enabled; degrade gracefully

## Out of Scope

- GUI color changes (GUI has its own theme system)
- Styling of `espansr list` output (table formatting is a separate concern)
- `--color=always` / `--color=never` flags (stretch goal, not required)

## Dependencies

- Spec: `/specs/cli-doctor.md` — `doctor` command must exist before coloring it. However, the color module itself can be built first and applied to `validate`/`status`/`setup` immediately.

## Notes

Standard ANSI codes:
- Green: `\033[32m` / Reset: `\033[0m`
- Yellow: `\033[33m`
- Red: `\033[31m`
- Bold: `\033[1m`

The utility module pattern (`ok("text")` returns `"\033[32m[ok]\033[0m text"` or `"[ok] text"` depending on context) keeps the callers clean.

Recommended: 2 tasks (color module + tests, then apply to CLI commands). Single session.
