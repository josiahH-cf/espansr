# Feature: Manifest Schema Alignment + Cross-Platform Path Resolution

**Status:** Not started
**Project:** espansr

## Description

The existing orchestratr connector in `espansr/integrations/orchestratr.py` generates a manifest with a nested YAML schema (`launch.command`, `hotkey.suggested_chord`) that doesn't match orchestratr's flat `AppEntry` schema (`command`, `chord`). It also writes the manifest to espansr's own config directory (`~/.config/espansr/orchestratr.yml`), but orchestratr doesn't scan external directories — it reads from its own `apps.d/` drop-in directory. This spec fixes the schema to match, changes the output path to target orchestratr's `apps.d/`, and adds cross-platform path resolution so WSL2 apps can register with the Windows-side orchestratr daemon.

### Current State (Context for Implementation)

- **Connector module** (`espansr/integrations/orchestratr.py`): Fully implemented with `generate_manifest()`, `manifest_needs_update()`, `get_status_json()`, `_build_launch_command()`, `_build_ready_command()`. All functions work and are well-tested.
- **Manifest schema produced today**:
  ```yaml
  name: espansr
  description: Espanso template manager
  version: "1.x.x"
  launch:
    command: "espansr gui"          # ← NESTED under launch.*
  ready_cmd: "espansr status --json"
  ready_timeout_ms: 3000
  hotkey:
    suggested_chord: "e"            # ← NESTED under hotkey.*
  ```
- **What orchestratr actually expects** (flat `AppEntry` in `internal/registry/config.go`):
  ```yaml
  name: espansr
  chord: "e"                        # ← FLAT top-level
  command: "espansr gui"            # ← FLAT top-level
  environment: wsl                  # ← REQUIRED for routing
  description: "Espanso template manager"
  ready_cmd: "espansr status --json"
  ready_timeout_ms: 3000
  ```
- **Schema mismatches**:
  - `launch.command` → should be `command` (breaking: orchestratr ignores nested map)
  - `hotkey.suggested_chord` → should be `chord` (breaking: orchestratr ignores nested map)
  - `version` → not in orchestratr's schema (silently ignored, wasted)
  - `environment` → not emitted by espansr (orchestratr defaults to `native`, wrong for WSL2)
- **Output path**: Currently `~/.config/espansr/orchestratr.yml` (espansr's config dir). orchestratr will scan `~/.config/orchestratr/apps.d/` (its own drop-in directory, per `drop-in-app-discovery.md`).
- **WSL2 handling**: On WSL2, `_build_launch_command()` pre-wraps with `wsl.exe -d <distro> -- espansr gui`. Under the new architecture, commands should NOT be pre-wrapped — orchestratr handles environment routing based on the `environment` field.
- **CLI integration** (`espansr/__main__.py`): `espansr setup` calls `manifest_needs_update()` → `generate_manifest()`. `espansr status --json` calls `get_status_json()`. Both work correctly.
- **Tests** (`tests/test_orchestratr_connector.py`): 558 lines, 8 test classes, thorough coverage. All must be updated.

### Target Architecture

After this spec, the connector:
1. Writes a **flat** manifest matching orchestratr's `AppEntry` schema
2. Writes to **orchestratr's `apps.d/` directory** (not espansr's config dir)
3. On WSL2, resolves the **Windows-side** `apps.d/` path (`/mnt/c/Users/<user>/AppData/Roaming/orchestratr/apps.d/`)
4. Sets `environment: wsl` on WSL2, `environment: native` on Linux/macOS
5. Does **not** pre-wrap commands with `wsl.exe` — the `command` field is always the native command (`espansr gui`)

## Acceptance Criteria

- [ ] Generated manifest uses flat YAML matching orchestratr's `AppEntry` schema: `name`, `chord`, `command`, `environment`, `description`, `ready_cmd`, `ready_timeout_ms` — no nested objects
- [ ] Manifest filename is `espansr.yml` in orchestratr's `apps.d/` directory
- [ ] On native Linux: manifest path is `~/.config/orchestratr/apps.d/espansr.yml`, `environment: native`
- [ ] On WSL2: manifest path is `/mnt/c/Users/<username>/AppData/Roaming/orchestratr/apps.d/espansr.yml`, `environment: wsl`
- [ ] On macOS: manifest path is `~/Library/Application Support/orchestratr/apps.d/espansr.yml`, `environment: native`
- [ ] `command` field is always the bare command (`espansr gui`) — never pre-wrapped with `wsl.exe`
- [ ] `ready_cmd` field is always the bare command (`espansr status --json`) — never pre-wrapped
- [ ] `espansr setup` prints confirmation: "Registered with orchestratr at <path>"
- [ ] If orchestratr's `apps.d/` directory does not exist (orchestratr not installed), `espansr setup` prints a non-fatal info message ("orchestratr not found — skipping app registration") and continues
- [ ] `manifest_needs_update()` detects schema changes from the old nested format and triggers regeneration
- [ ] `espansr setup --dry-run` shows what would be written and where, without writing
- [ ] All existing tests updated to match new schema and paths; no test regressions

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `espansr/integrations/orchestratr.py` — rewrite `generate_manifest()` for flat schema and new paths, add `resolve_orchestratr_apps_dir()`, simplify `_build_launch_command()` / `_build_ready_command()` (remove `wsl.exe` wrapping), update `manifest_needs_update()` |
| **Modify** | `espansr/__main__.py` — update `cmd_setup()` to use new path, improve user feedback messages |
| **Modify** | `tests/test_orchestratr_connector.py` — update all assertions for flat schema, new paths, cross-platform logic |

## Constraints

- No new dependencies — YAML generation uses PyYAML (already a dependency)
- Must not break `espansr status --json` (output format unchanged)
- Must not break `espansr setup` for non-connector functionality (template copying, Espanso detection, launcher trigger)
- On WSL2, the Windows username is resolved from `$USER` mapped through `/mnt/c/Users/` or from `cmd.exe /c echo %USERNAME%` — handle cases where the Windows and WSL usernames differ
- If the `apps.d/` parent directory (`~/.config/orchestratr/`) doesn't exist, that means orchestratr isn't installed — do not create it (only orchestratr should create its own config directory)
- Backward compatibility: if an old-format manifest exists at `~/.config/espansr/orchestratr.yml`, `espansr setup` should clean it up (delete) after writing the new one

## Out of Scope

- Changes to `get_status_json()` output format (it's already correct and stable)
- GUI integration for connector status (follow-up feature)
- Modifying orchestratr code (handled by orchestratr's own specs)

## Dependencies

- **orchestratr `drop-in-app-discovery.md`** — defines the `apps.d/` directory structure and manifest schema that this spec targets. Can be developed in parallel since the schema is agreed upon, but orchestratr must implement `apps.d/` scanning for the manifests to actually be discovered.

## Notes

### Cross-platform path resolution

```python
def resolve_orchestratr_apps_dir() -> Optional[Path]:
    """Resolve the orchestratr apps.d/ directory for the current platform.
    
    Returns None if orchestratr is not installed (directory doesn't exist).
    """
    platform = detect_platform()  # "linux", "macos", "wsl2", "windows"
    
    if platform == "wsl2":
        # orchestratr runs on Windows — target Windows-side path
        win_user = _resolve_windows_username()
        base = Path(f"/mnt/c/Users/{win_user}/AppData/Roaming/orchestratr")
    elif platform == "windows":
        base = Path(os.environ.get("APPDATA", "")) / "orchestratr"
    elif platform == "macos":
        base = Path.home() / "Library" / "Application Support" / "orchestratr"
    else:  # linux
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "orchestratr"
    
    apps_dir = base / "apps.d"
    if not base.exists():
        return None  # orchestratr not installed
    return apps_dir
```

### Windows username resolution from WSL2

```python
def _resolve_windows_username() -> str:
    """Get the Windows username from inside WSL2."""
    # Method 1: Parse /mnt/c/Users/ for existing user directories
    # Method 2: Run cmd.exe /c "echo %USERNAME%" 
    # Method 3: Check WSLENV or other environment variables
    # Prefer method 2 as most reliable
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo", "%USERNAME%"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Fallback: scan /mnt/c/Users/ for non-system directories
        ...
```

### New manifest format

```yaml
# orchestratr app manifest — written by espansr setup
name: espansr
chord: "e"
command: "espansr gui"
environment: native  # or "wsl" on WSL2
description: "Espanso template manager"
ready_cmd: "espansr status --json"
ready_timeout_ms: 3000
```

### Old manifest cleanup

During `espansr setup`, after writing the new manifest:
```python
old_path = config_dir / "orchestratr.yml"  # old location in espansr's config dir
if old_path.exists():
    old_path.unlink()
    print(f"  Cleaned up old manifest at {old_path}")
```
