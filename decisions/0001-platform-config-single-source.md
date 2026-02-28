# Decision 0001: PlatformConfig as single source of truth for platform paths

**Date:** 2026-02-28
**Status:** Accepted
**Feature:** /specs/install-first-run.md

## Context

Platform-specific paths (espansr config dir, Espanso candidate dirs) were independently computed in three Python files (`platform.py`, `config.py`, `espanso.py`) and the bash installer. The path vocabulary also varied (`"Darwin"` vs `"macos"`). Any path change had to be replicated across all copies, creating a maintenance and correctness risk.

## Options

1. **PlatformConfig dataclass in `platform.py`** — One `@dataclass` per platform with all paths, consumed by `config.py` and `espanso.py` via `get_platform_config()`. Adding a new platform means editing one file.
2. **Config file or environment variables** — Store paths externally. More flexible but adds I/O, parsing, and a bootstrapping problem (need paths to find the config file).
3. **Keep per-module logic, add tests** — Leave duplication in place and rely on cross-module tests to catch drift. Lower effort but doesn't eliminate the root cause.

## Decision

Option 1. A `PlatformConfig` dataclass in `espansr/core/platform.py` defines `espansr_config_dir` and `espanso_candidate_dirs` for each platform. `config.py` and `espanso.py` delegate to `get_platform_config()` instead of computing paths themselves. The bash installer delegates post-install work to `espansr setup`, eliminating its own path duplication.

## Consequences

- Adding a new platform requires editing only `platform.py` (and optionally `install.sh` for system deps)
- `config.py` and `espanso.py` no longer import stdlib `platform`
- `install.sh` is ~145 lines shorter, with no Espanso detection, stale cleanup, launcher, or templates logic in bash
- The `espansr setup` command becomes the canonical post-install entry point for any installer (bash, PowerShell, or manual)
