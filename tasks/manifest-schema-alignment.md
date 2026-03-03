# Tasks: Manifest Schema Alignment + Cross-Platform Path Resolution

**Spec:** `/specs/manifest-schema-alignment.md`
**Status:** In progress

## Task 1: Add `resolve_orchestratr_apps_dir()` to orchestratr.py

- Add `resolve_orchestratr_apps_dir()` function that returns the platform-appropriate `apps.d/` directory
- Linux: `~/.config/orchestratr/apps.d/`
- macOS: `~/Library/Application Support/orchestratr/apps.d/`
- WSL2: `/mnt/c/Users/<username>/AppData/Roaming/orchestratr/apps.d/`
- Returns `None` if orchestratr base dir doesn't exist (not installed)
- **Status:** Not started

## Task 2: Rewrite manifest generation (flat schema, new path, simplified commands)

- Change `generate_manifest()` signature to accept optional `apps_dir` (or resolve internally)
- Produce flat YAML: `name`, `chord`, `command`, `environment`, `description`, `ready_cmd`, `ready_timeout_ms`
- Remove nested `launch.command`, `hotkey.suggested_chord`, `version`
- Simplify `_build_launch_command()` and `_build_ready_command()` — always bare commands, no `wsl.exe` wrapping
- Add `environment` field: `"wsl"` on WSL2, `"native"` otherwise
- Update `manifest_needs_update()` to detect old nested format
- **Status:** Not started

## Task 3: Update `cmd_setup()` in `__main__.py`

- Use `resolve_orchestratr_apps_dir()` to determine manifest output path
- If `apps.d/` dir doesn't exist, print info message and skip (non-fatal)
- If written, print "Registered with orchestratr at <path>"
- Clean up old manifest at `~/.config/espansr/orchestratr.yml` if it exists
- Support `--dry-run` for the new path logic
- **Status:** Not started

## Task 4: Update all tests

- Update `TestManifestGeneration` for flat schema assertions
- Update `TestWsl2Manifest` — no more `wsl.exe` in commands, check `environment: wsl`
- Add tests for `resolve_orchestratr_apps_dir()` (all platforms)
- Add tests for old manifest cleanup
- Add tests for orchestratr-not-installed skip behavior
- Update `TestSetupIntegration` for new paths and messages
- **Status:** Not started
