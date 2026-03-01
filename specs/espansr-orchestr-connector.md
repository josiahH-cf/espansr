# Feature: espansr ↔ orchestr Connector

**Status:** Not started  
**Project:** espansr (this repo)

## Description

espansr needs to be discoverable, launchable, and optionally queryable by orchestr. This spec defines the espansr-side changes required for integration: an app manifest that orchestr's registry reads, a launch protocol that handles both CLI and GUI modes, and an optional health endpoint that lets orchestr track espansr's status. The goal is zero-config for basic launch and minimal config for deeper integration.

## Acceptance Criteria

- [ ] espansr ships an `orchestr.yml` app manifest in its config directory that orchestr can discover
- [ ] `espansr gui` is launchable by orchestr and reports its PID correctly
- [ ] `espansr status --json` outputs machine-readable status (template count, last sync, config path) for orchestr health checks
- [ ] When launched by orchestr, espansr GUI responds to "bring to front" signals (X11 `_NET_ACTIVE_WINDOW`, macOS `NSApplication.activate`, Windows `SetForegroundWindow`) — existing window manager behavior, no custom IPC
- [ ] orchestr manifest includes a `ready_cmd` that orchestr can poll to confirm espansr is responsive
- [ ] If orchestr is not installed, espansr behavior is unchanged — connector is passive
- [ ] `espansr setup` regenerates the orchestr manifest if it's missing or outdated

## Affected Areas

| Area | Files |
|------|-------|
| **Create** | `espansr/integrations/orchestr.py` — manifest generation and status helpers |
| **Modify** | `espansr/__main__.py` — add `--json` flag to `status` subcommand |
| **Modify** | `espansr/core/config.py` — add orchestr manifest path to `EspansoConfig` |
| **Modify** | `espansr/__main__.py` (`cmd_setup`) — call manifest generation |
| **Create** | `tests/test_orchestr_connector.py` — tests for manifest generation, JSON status output |

## Constraints

- No new dependencies — YAML generation already uses PyYAML
- Manifest format must match orchestr's app registry schema (defined in `orchestr/03-app-registry.md`)
- `--json` output must be stable (machine-readable contract) — use a versioned schema
- espansr must not import or depend on orchestr code — integration is via files and CLI

## Out of Scope

- orchestr daemon code (lives in orchestr repo)
- HTTP API client in espansr (orchestr calls espansr, not the other way)
- GUI changes to display orchestr connection status (follow-up feature)

## Dependencies

- `orchestr/03-app-registry.md` — defines the manifest schema espansr must produce
- `orchestr/04-http-api.md` — defines `/apps/{name}/ready` endpoint that calls espansr's `ready_cmd`

## Notes

### App manifest format

Generated at `~/.config/espansr/orchestr.yml` (or platform-equivalent via `PlatformConfig`):

```yaml
# orchestr app manifest for espansr
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

### Launch lifecycle from orchestr's perspective

1. User presses `Ctrl+Space → e`
2. orchestr checks if espansr is already running (PID file or process list)
3. If running → bring espansr window to front (OS-native WM request)
4. If not running → execute `espansr gui`, poll `ready_cmd` until success or timeout
5. If `ready_cmd` times out → orchestr notifies user "espansr failed to start"

### Manifest regeneration

`espansr setup` should:
1. Check if `orchestr.yml` exists in config dir
2. If missing or if version has changed → regenerate from current espansr metadata
3. Print: `✓ orchestr manifest written to ~/.config/espansr/orchestr.yml`

This is idempotent and safe — the manifest is a declarative file, not a running connection.

### WSL2 considerations

When espansr runs inside WSL2 and orchestr runs on Windows:
- orchestr's registry entry for espansr uses: `wsl.exe -d Ubuntu -- espansr gui`
- The manifest generation should detect WSL2 and emit the appropriate cross-env launch command
- `ready_cmd` becomes: `wsl.exe -d Ubuntu -- espansr status --json`
- Window management ("bring to front") for WSLg windows works through the standard X11/Wayland path since WSLg renders windows on the Windows desktop
