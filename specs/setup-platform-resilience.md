# Feature: Setup and Platform Resilience

**Status:** Not started

## Description

Three infrastructure hardening improvements grouped together because they share the same code area (setup flow and platform module) and are each too small for a standalone spec.

**1. Bundled template path resilience.** `_get_bundled_dir()` uses `Path(__file__).parent.parent / "templates"` which only works for editable installs. Add a fallback using `importlib.resources` so non-editable installs (`pip install .`) can also locate bundled templates. Register `templates/` as package data in `pyproject.toml`.

**2. Setup exit code for missing Espanso.** `espansr setup` currently returns 0 even when Espanso is not found. It should return 0 (setup itself succeeded) but print a clear warning. No exit code change — but add a `--strict` flag that returns 1 if Espanso is not detected, for CI/scripting use.

**3. Validate bundled templates during setup.** After copying templates, run `validate_template()` on each copied template and report any issues. Catches malformed bundled content before the user discovers it via `espansr validate`.

**4. Platform config caching.** Add `@lru_cache` to `get_platform_config()` and `get_platform()` so repeated calls within a single process don't re-read `/proc/version` or call `cmd.exe` multiple times.

## Acceptance Criteria

- [ ] `_get_bundled_dir()` falls back to `importlib.resources` when the repo-level `templates/` dir does not exist
- [ ] `pyproject.toml` includes `templates/*.json` as package data
- [ ] `espansr setup --strict` returns 1 if Espanso config directory is not detected
- [ ] `espansr setup` (without `--strict`) still returns 0 when Espanso is missing
- [ ] After copying bundled templates, `cmd_setup` runs validation and prints any issues found
- [ ] `get_platform()` and `get_platform_config()` are cached with `@lru_cache` and return identical objects on repeat calls
- [ ] All existing tests pass without modification

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `espansr/__main__.py` — `_get_bundled_dir()` fallback, `cmd_setup` validation step, `--strict` flag |
| **Modify** | `espansr/core/platform.py` — add `@lru_cache` to `get_platform()` and `get_platform_config()` |
| **Modify** | `pyproject.toml` — package data for `templates/` |
| **Create** | `tests/test_setup_resilience.py` — tests for fallback, strict mode, validation step, caching |

## Constraints

- `importlib.resources` is stdlib (Python 3.9+) — no new dependency
- Caching must not break tests that mock platform detection — tests should call `get_platform.cache_clear()` in setup/teardown
- `--strict` is an additive flag, not a breaking change

## Out of Scope

- Changing the template storage format
- Migrating away from `shutil.copy2` for template copying
- Adding `--strict` to other commands

## Dependencies

None.

## Notes

`importlib.resources` API for Python 3.11+:
```python
from importlib.resources import files
bundled = files("espansr").parent / "templates"
```

For `@lru_cache` on `get_platform_config()`, note that the function currently returns a new `PlatformConfig` object each call. After caching, the same object is returned — callers should not mutate it. `PlatformConfig` should be made frozen (`@dataclass(frozen=True)`) or callers should be verified as read-only.

Recommended: 3 tasks (caching → bundled path fallback → strict + validation). 1–2 sessions.
