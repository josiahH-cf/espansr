# Tasks: Setup and Platform Resilience

**Spec:** /specs/setup-platform-resilience.md

## Status

- Total: 3
- Complete: 3
- Remaining: 0

## Task List

### Task 1: Platform config caching

- **Files:** `espansr/core/platform.py`, `tests/test_setup_resilience.py`
- **Done when:** `get_platform()` and `get_platform_config()` are decorated with `@lru_cache`, `PlatformConfig` is frozen, and repeated calls return the same object.
- **Status:** [x] Complete

### Task 2: Bundled template path fallback

- **Files:** `espansr/__main__.py`, `pyproject.toml`, `tests/test_setup_resilience.py`
- **Done when:** `_get_bundled_dir()` falls back to `importlib.resources` when the repo-level `templates/` dir does not exist, and `pyproject.toml` includes `templates/*.json` as package data.
- **Criteria covered:** `_get_bundled_dir()` falls back to `importlib.resources`; `pyproject.toml` includes `templates/*.json` as package data.
- **Status:** [x] Complete

### Task 3: Setup strict mode and validation step

- **Files:** `espansr/__main__.py`, `tests/test_setup_resilience.py`
- **Done when:** `espansr setup --strict` returns 1 if Espanso config is not detected; `espansr setup` (without `--strict`) still returns 0; `cmd_setup` runs `validate_template()` on copied templates and prints issues.
- **Criteria covered:** `--strict` flag behavior; post-copy validation step; existing tests unmodified.
- **Status:** [x] Complete

## Test Strategy

| Criterion | Task | Test |
|-----------|------|------|
| `lru_cache` on `get_platform()` + `get_platform_config()` | 1 | `test_get_platform_cached`, `test_get_platform_config_cached` |
| `PlatformConfig` is frozen | 1 | `test_platform_config_frozen` |
| `_get_bundled_dir()` importlib fallback | 2 | `test_bundled_dir_fallback_importlib` |
| `pyproject.toml` package data | 2 | `test_bundled_dir_package_data` (manual verify) |
| `--strict` returns 1 when no Espanso | 3 | `test_setup_strict_returns_1_without_espanso` |
| `--strict` returns 0 when Espanso found | 3 | `test_setup_strict_returns_0_with_espanso` |
| Non-strict returns 0 when no Espanso | 3 | Already covered by `test_setup.py` |
| Post-copy validation runs | 3 | `test_setup_validates_copied_templates` |
| Validation issues printed | 3 | `test_setup_prints_validation_warnings` |

## Session Log

