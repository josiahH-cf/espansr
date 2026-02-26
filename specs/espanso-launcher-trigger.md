# Spec: Ship Espanso Launcher Trigger for Hotkey-Style GUI Launch

**Issue:** #5  
**Status:** Draft

## Description

Auto-generate a separate `automatr-launcher.yml` in the Espanso match directory containing a shell trigger (default: `:aopen`) that launches the Automatr GUI. The file is created during installation and on first app run. On WSL2, the command invokes the Linux-side binary via `wsl.exe`. The trigger keyword is configurable. First-run detection shows setup instructions in the GUI.

## Acceptance Criteria

- [ ] A `automatr-launcher.yml` file is written to the Espanso `match/` directory with a single shell trigger that launches `automatr-espanso gui`; the file is separate from `automatr-espanso.yml`
- [ ] The trigger keyword defaults to `:aopen` and is configurable via `config.espanso.launcher_trigger`; changing the config regenerates the file
- [ ] On WSL2, the shell command uses `wsl.exe -d $WSL_DISTRO_NAME -- <path-to-binary> gui` to correctly invoke the Linux binary from Windows-side Espanso
- [ ] On native Linux/macOS, the shell command invokes the `automatr-espanso gui` binary directly
- [ ] `install.sh` generates the launcher file during installation if an Espanso config directory is found
- [ ] On first run (launcher file does not exist), the GUI displays a non-blocking info message explaining the trigger keyword and how to customize it
- [ ] The launcher file is included in stale cleanup (Issue #2) — old copies in non-canonical paths are removed

## Affected Areas

| Area | Files |
|------|-------|
| **Modify** | `automatr_espanso/integrations/espanso.py` — add `generate_launcher_file()`, update stale cleanup list |
| **Modify** | `automatr_espanso/core/config.py` — add `launcher_trigger` field to `EspansoConfig` |
| **Modify** | `automatr_espanso/ui/main_window.py` — first-run detection + info message |
| **Modify** | `install.sh` — call launcher generation during install |
| **Create** | `tests/test_launcher.py` — tests for launcher YAML generation and WSL2 command construction |

## Constraints

- The launcher file must not be overwritten by `sync_to_espanso()` — it lives in a separate file
- WSL2 distro name: prefer `$WSL_DISTRO_NAME` env var; fall back to parsing `wsl.exe -l -q` output
- The GUI launch command should use a detached/background process so Espanso doesn't block waiting for the window to close
- First-run message must be non-blocking (status bar message or dismissable banner, not a dialog)

## Out of Scope

- Global keyboard shortcut registration (we use Espanso's own trigger mechanism instead)
- Windows .lnk shortcut creation
- System tray / persistent background daemon
- Custom hotkey chord (Ctrl+O) — Espanso text triggers are the mechanism

## Dependencies

- Issue #2 (path consolidation) — needs correct canonical path resolution and stale cleanup
- Issue #1 (shared platform module) — for `is_wsl2()` and WSL distro detection

## Notes

- Espanso v2 shell trigger format:
  ```yaml
  matches:
    - trigger: ":aopen"
      replace: "{{output}}"
      vars:
        - name: output
          type: shell
          params:
            cmd: "wsl.exe -d Ubuntu -- /home/user/automatr-espanso/.venv/bin/automatr-espanso gui &"
  ```
- The `&` at the end of the shell command is important — without it, Espanso blocks until the GUI closes
- `$WSL_DISTRO_NAME` is set automatically in WSL2 sessions; it contains the distro name (e.g., "Ubuntu")
- The binary path should be resolved at generation time using `shutil.which("automatr-espanso")` or the known venv path
- `EspansoConfig` needs a new field: `launcher_trigger: str = ":aopen"`
