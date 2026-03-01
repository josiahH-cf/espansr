# Feature: First Public Release (v1.0)

**Status:** Complete

## Description

Prepare the project for its first public release. This includes polishing the README with a CI badge, platform support matrix, and complete usage guide; creating a CHANGELOG documenting all features shipped since v0.1.0; bumping the version from `0.1.0` to `1.0.0` in all locations; and adding `--version` CLI support so users can verify their installed version.

## Acceptance Criteria

- [x] `pyproject.toml` `version` field is `"1.0.0"`
- [x] `espansr/__init__.py` `__version__` is `"1.0.0"`
- [x] `espansr --version` prints "espansr 1.0.0" and exits 0
- [x] `CHANGELOG.md` exists with entries for all completed features (issues 1–9)
- [x] `README.md` contains a CI badge linking to the GitHub Actions workflow
- [x] `README.md` contains a platform support matrix (Linux, macOS, Windows, WSL2)
- [x] `README.md` Development section includes lint, format, and type-check commands

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `pyproject.toml` — version bump |
| **Modify** | `espansr/__init__.py` — version bump |
| **Modify** | `espansr/__main__.py` — add `--version` flag |
| **Create** | `CHANGELOG.md` |
| **Modify** | `README.md` — badge, platform matrix, usage polish |

## Constraints

- No behavior changes to existing commands
- No new dependencies
- All existing tests must continue to pass

## Out of Scope

- Git tag creation (human action)
- GitHub Release creation (human action)
- PyPI publishing (not a project goal per AGENTS.md)
- Screenshots (requires display; human can add later)

## Dependencies

All features 1–9 must be complete (they are).

## Notes

The `__version__` in `espansr/__init__.py` is the single source for the version string. The CLI `--version` flag reads from there. `pyproject.toml` must be kept in sync manually.
