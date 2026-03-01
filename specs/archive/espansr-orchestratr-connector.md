# Feature: espansr ↔ orchestratr Connector

**Status:** Complete  
**Project:** espansr (this repo)

## Description

espansr needs to be discoverable, launchable, and optionally queryable by orchestratr. This spec defines the espansr-side changes required for integration: an app manifest that orchestratr's registry reads, a launch protocol that handles both CLI and GUI modes, and an optional health endpoint that lets orchestratr track espansr's status. The goal is zero-config for basic launch and minimal config for deeper integration.

## Acceptance Criteria

- [x] espansr ships an `orchestratr.yml` app manifest in its config directory that orchestratr can discover
- [x] `espansr gui` is launchable by orchestratr and reports its PID correctly
- [x] `espansr status --json` outputs machine-readable status (template count, last sync, config path) for orchestratr health checks
- [x] When launched by orchestratr, espansr GUI responds to "bring to front" signals (X11 `_NET_ACTIVE_WINDOW`, macOS `NSApplication.activate`, Windows `SetForegroundWindow`) — existing window manager behavior, no custom IPC
- [x] orchestratr manifest includes a `ready_cmd` that orchestratr can poll to confirm espansr is responsive
- [x] If orchestratr is not installed, espansr behavior is unchanged — connector is passive
- [x] `espansr setup` regenerates the orchestratr manifest if it's missing or outdated

## Affected Areas

| Area | Files |
|------|-------|
| **Create** | `espansr/integrations/orchestratr.py` — manifest generation and status helpers |
| **Modify** | `espansr/__main__.py` — add `--json` flag to `status` subcommand |
| **Modify** | `espansr/core/config.py` — add orchestratr manifest path to `EspansoConfig` |
| **Modify** | `espansr/__main__.py` (`cmd_setup`) — call manifest generation |
| **Create** | `tests/test_orchestratr_connector.py` — tests for manifest generation, JSON status output |

## Constraints

- No new dependencies — YAML generation already uses PyYAML
- Manifest format must match orchestratr's app registry schema (defined in `orchestratr/03-app-registry.md`)
- `--json` output must be stable (machine-readable contract) — use a versioned schema
- espansr must not import or depend on orchestratr code — integration is via files and CLI

## Out of Scope

- orchestratr daemon code (lives in orchestratr repo)
- HTTP API client in espansr (orchestratr calls espansr, not the other way)
- GUI changes to display orchestratr connection status (follow-up feature)

## Dependencies

- `orchestratr/03-app-registry.md` — defines the manifest schema espansr must produce
- `orchestratr/04-http-api.md` — defines `/apps/{name}/ready` endpoint that calls espansr's `ready_cmd`

## Notes

### App manifest format

Generated at `~/.config/espansr/orchestratr.yml` (or platform-equivalent via `PlatformConfig`):

```yaml
# orchestratr app manifest for espansr
name: espansr
description: "Espanso template manager"
version: "1.1.0"  # from espansr.__version__

launch:
  command: "espansr gui"
  # On Windows, full path may be needed:
  # command: "C:\\Users\\...\\espansr.exe gui"
  
ready_cmd: "espansr status --json"
ready_timeout_ms: 3000

hotkey:
  suggested_chord: "e"  # Ctrl+Space → e to launch espansr
```

### `espansr status --json` output

```json
{
  "version": "1.1.0",
  "status": "ok",
  "config_dir": "/home/user/.config/espansr",
  "espanso_synced": true,
  "template_count": 5,
  "last_sync": "2025-01-15T10:30:00Z"
}
```

When espansr has issues:
```json
{
  "version": "1.1.0",
  "status": "degraded",
  "config_dir": "/home/user/.config/espansr",
  "espanso_synced": false,
  "template_count": 0,
  "errors": ["No templates found", "Espanso not detected"]
}
```

### Launch lifecycle from orchestratr's perspective

1. User presses `Ctrl+Space → e`
2. orchestratr checks if espansr is already running (PID file or process list)
3. If running → bring espansr window to front (OS-native WM request)
4. If not running → execute `espansr gui`, poll `ready_cmd` until success or timeout
5. If `ready_cmd` times out → orchestratr notifies user "espansr failed to start"

### Manifest regeneration

`espansr setup` should:
1. Check if `orchestratr.yml` exists in config dir
2. If missing or if version has changed → regenerate from current espansr metadata
3. Print: `✓ orchestratr manifest written to ~/.config/espansr/orchestratr.yml`

This is idempotent and safe — the manifest is a declarative file, not a running connection.

### WSL2 considerations

When espansr runs inside WSL2 and orchestratr runs on Windows:
- orchestratr's registry entry for espansr uses: `wsl.exe -d Ubuntu -- espansr gui`
- The manifest generation should detect WSL2 and emit the appropriate cross-env launch command
- `ready_cmd` becomes: `wsl.exe -d Ubuntu -- espansr status --json`
- Window management ("bring to front") for WSLg windows works through the standard X11/Wayland path since WSLg renders windows on the Windows desktop
