# Verification Guide

Use this checklist after installing from a fresh checkout or after changing setup/install behavior.

## 1. Install From The Repo Folder

```bash
# Linux / macOS / intentional WSL2 install
./install.sh
```

```powershell
# Windows PowerShell
.\install.ps1
```

Windows PowerShell and WSL are separate environments. On a Windows host, use
`.\install.ps1` unless you intentionally want a WSL-side `espansr` install.

The installer should create `.venv`, install the package in editable mode, run
`espansr setup`, seed bundled templates, record the install location for
`espansr refresh` and `espansr sync`, and smoke-test `espansr list` and
`espansr status`.

`install.ps1` also registers and starts the Espanso service when Espanso is
found, runs `espansr configure-remote-desktop --auto` (host mode with
`-RemoteDesktop`, workstation mode with `-LocalOnly`; see
[docs/CLI.md](CLI.md#espansr-configure-remote-desktop)), writes the
`%LOCALAPPDATA%\espansr\bin\espansr.cmd` launcher and appends that directory to
the Windows user PATH (removing any legacy venv `Scripts` entry), and starts
Espanso before running setup. It refuses `-RemoteDesktop` together with
`-LocalOnly`, and a failed setup stops the install instead of printing the
success banner. The remote-desktop step edits only one marked block in
Espanso's `config/default.yml` and keeps a one-time `default.yml.espansr-orig`
backup; `espansr configure-remote-desktop --revert` restores the file.

On Linux and macOS, `install.sh` does more than install `espansr`. Know its
side effects before running it:

- On Debian/Ubuntu it installs the Qt (xcb) runtime packages PyQt6 needs, plus
  `libfuse2` or `libfuse2t64` for the AppImage path, with `sudo apt-get`.
- When `espanso` is not on PATH it installs it: the upstream X11 `.deb` on
  apt distros (falling back to the X11 AppImage at `~/.local/bin/espanso`,
  wrapped in extract-and-run mode when FUSE is unavailable), or
  `brew tap espanso/espanso && brew install espanso` on macOS (Homebrew itself
  is never installed). After installing it, the script seeds
  `config/default.yml` with `show_icon: false` and `show_notifications: false`
  when that file does not exist, writes and enables a user systemd unit
  (`~/.config/systemd/user/espanso.service`, running `espanso daemon`) on
  Linux or runs `espanso service register` and `espanso service start` on
  macOS, and waits up to 15 seconds for the Espanso config directory.
- On WSL2 it never installs Espanso; use `espansr wsl-install-espanso`.
- It appends an `alias espansr=...` line to `~/.bashrc` or `~/.zshrc`. The
  PATH-visible shim at `~/.local/bin/espansr` comes from `espansr setup`.
- On a Linux Wayland session it detects Chrome, VS Code, Obsidian, and
  gnome-terminal and asks once (`[Y/n]`) whether to force them under XWayland
  so Espanso can capture keystrokes inside them. Saying yes writes user-owned
  `.desktop` overrides under `~/.local/share/applications/`, a
  `~/.local/bin/code` wrapper, and a systemd user drop-in for
  `gnome-terminal-server.service`. Every generated file carries the marker
  `espansr-xwayland-override`, and a revert script is installed at
  `~/.local/share/espansr/revert-xwayland-apps.sh` with a PATH-visible symlink
  `~/.local/bin/espansr-revert-xwayland-apps`. A non-interactive shell skips
  the prompt.

Opt-outs (each flag and its environment variable are equivalent):

| Flag | Environment variable | Effect |
|------|----------------------|--------|
| `--no-espanso` | `ESPANSR_NO_ESPANSO=1` | Skip the automatic Espanso runtime install |
| `--no-xwayland-apps` | `ESPANSR_XWAYLAND_APPS=no` | Skip the GNOME/Wayland app override prompt |
| `--yes-xwayland-apps` | `ESPANSR_XWAYLAND_APPS=yes` | Apply the overrides without prompting |
| (none) | `ESPANSR_XWAYLAND_APPS=auto` | Default: prompt in an interactive shell, skip otherwise |

Run `espansr-revert-xwayland-apps` at any time to remove the overrides, then
close and relaunch the affected apps.

## 2. Verify The CLI

```bash
espansr --version
espansr list
espansr validate
espansr status
espansr doctor
```

Expected:

- `--version` prints the installed version.
- `list` shows bundled starter templates with triggers.
- `validate` prints `All templates valid.` or specific template issues.
- `status` shows the detected Espanso config path and binary location; it exits 1 when no Espanso config directory is found, and a missing binary is only a warning.
- `doctor` prints `[ok]`, `[warn]`, or `[FAIL]` checks for Python, config, templates, Espanso, launcher files, the command shim, and validation.

`doctor` exits nonzero when Espanso or generated launcher files are missing.
That means espansr is installed, but Espanso-trigger expansion is not fully ready yet.

## 3. If Espanso Is Missing

Install and start Espanso from [espanso.org](https://espanso.org/), then run:

```bash
espansr setup
espansr doctor
```

On intentional WSL2 installs, Espanso normally runs on the Windows side. From WSL:

```bash
espansr wsl-install-espanso
espansr setup
espansr doctor
```

Run `setup` before `doctor`: `doctor` fails until `setup` has generated the
launcher files.

If the WSL launcher trigger ever stops opening the GUI, rerun `espansr setup` to regenerate the Windows-side launcher file before editing YAML manually.

## 4. Verify Publishing

```bash
espansr publish --dry-run
espansr publish
```

Expected: dry-run prints what would be written, and publish writes managed
Espanso output when Espanso config is detected. If Espanso is missing, publish
fails with a clear config-path error.

## 5. Verify The GUI

```bash
espansr gui
```

Expected: the window opens with template browsing, editing, previews, variables,
import, remote pull, and publishing available. Check that selecting a bundled
template populates the editor and that Publish reports a status message.

When Espanso is installed and running, also verify these triggers in any app
where Espanso expands text:

- `:aopen` opens the full espansr editor.
- `:coms` opens the commands popup and closes with `Esc`.
- `:sync` runs `espansr sync` (pull, commit and push local changes, reinstall)
  through the console entry point so its progress is visible.

## 6. Developer Checks

```bash
pytest
ruff check .
black --check .
```

Expected: all tests pass, with zero lint or format errors.