# Verification Guide

Use this checklist after installing from a fresh checkout or after changing setup/install behavior.

CI runs the full suite on native Linux, macOS, and Windows. On Linux/Python
3.12, macOS, and Windows it also runs `scripts/verify_install.py`: a fresh
install into a path with spaces, actual Git pull/push with local edits, repeat
installation, starter upgrades, preserved custom templates and preferences,
exact prompt copying through Qt, and maximization, reopening, and pane resizing
of both windows on Qt's offscreen platform. It also retains custom clipboard
timing in host mode through Git sync/reinstall and in workstation mode through
another refresh. The canary uses a temporary home and a
local Git remote, cleans them up, and restores the Windows runner's user PATH.
It skips Espanso runtime installation and desktop typing; those require a real
desktop, permissions, and the checks below. Clipboard and window checks use Qt
offscreen, so they are not evidence of a real desktop.

### What CI checks on each system

A change has these results only once its own CI run passes; until then they
are what CI will check, not evidence.

| Environment | Checked by CI | Needs a real machine |
|-------------|--------------|----------------------|
| Windows 11 (x64) | Full suite, installer canary (`install.ps1 -LocalOnly`), Espanso 2.3.0 to 2.4.1 upgrade | Typing triggers, window focus, WMI restart of a live Espanso, RDP/RustDesk sessions, PowerShell 7 |
| macOS (Apple Silicon) | Full suite, installer canary, Homebrew route | Accessibility and Input Monitoring permissions, launchd service, Terminal automation for `:sync`, Intel Macs |
| Linux (Ubuntu, X11 libraries) | Full suite on 3.11-3.13, installer canary, X11 `.deb` upgrade | X11 or Wayland desktop typing, the Wayland `.deb` and AppImage routes, non-apt distributions |
| WSL2 | Path and launcher logic through mocks, and the Windows profile lookup against stand-in `cmd.exe` and `wslpath` scripts on the Linux and macOS jobs (not WSL) | Everything that crosses to Windows: the real `cmd.exe` and `wslpath`, Espanso detection, restart, `wsl.exe` triggers |

Teammates on a different system should run the checks in sections 1-5 on it;
a passing CI run does not cover the right-hand column.

A separate `scripts/verify_espanso_runtime.py` canary installs the real official
2.3.0 runtime and runs the real upgrade route on Windows and Linux. On macOS it
runs the Homebrew route. It verifies the installed version, preserves existing
clipboard configuration through upgrade and a repeated install pass, enables
statistics without changing those settings, and checks counter availability
using the real version probe. It restores the runner's original default config.
It runs only on
disposable CI runners, without starting services or typing into desktop apps.

Installers target Espanso **2.4.1+**. Missing runtimes are installed; older
standard installations are upgraded; supported versions skip network downloads.
Windows uses the official per-user installer, Linux preserves an installed
X11/Wayland Debian package or the managed AppImage, and macOS uses Homebrew.
Windows/Linux downloads are pinned to 2.4.1 and SHA-256 verified before stopping
an existing runtime. The configuration and prompt store remain outside the
runtime's installation folder. Custom/system installs, unavailable package
managers, unsupported architectures and failed upgrades get guidance without
blocking espansr. On macOS, Accessibility/Input Monitoring permissions may
still need to be granted through the OS; an installer cannot grant them.

Use Windows `-NoEspanso`, POSIX `--no-espanso`, or `ESPANSR_NO_ESPANSO=1` to skip
runtime installation/upgrade. Existing Espanso can still be used. WSL's explicit
`espansr wsl-install-espanso` command shares the Windows runtime helper.

### Local expansion counts

On Espanso 2.4+, setup enables `stats.enabled` in `config/default.yml`, preserving
other settings, comments and a one-time original backup. Expand a prompt using
its actual trigger, then inspect its small `Runs` label in `:coms` details or
the `:aopen` editor. While a window is open, counts refresh every ten seconds.
Copy trigger, Copy prompt and scratchpad actions never increment the count.
Older or undetectable runtimes show unavailable; a failed read does not prevent
copying or publishing. Publishing reads usage before it finishes: while another
espansr process holds the usage lock, or when the lock cannot be taken at all,
it waits up to five seconds first, and the window does not respond meanwhile.
Existing expansions before native tracking was enabled cannot be recovered.

The local `usage.json` beside `config.json` contains a schema version, native
database checkpoint, trigger ownership, and command records with lifetime
counts and trigger aliases. It contains no prompt bodies and is outside the
template Git repository. Stable capability IDs (or the existing filename
fallback) keep totals through trigger renames. Reusing a tracked trigger for
another command assigns only later records to that command. History before
the first espansr checkpoint can only be attributed by its native trigger name.
Native statistics clear/prune retains totals already checkpointed by espansr;
unread records removed from the native database cannot be recovered. Nothing
in espansr clears or prunes native statistics.

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
The default `--auto` path leaves existing managed clipboard settings unchanged
(only untouched settings an earlier release wrote are brought up to date, once);
only explicit host/workstation selection resets their defaults. **Remote paste**
in either desktop window makes that selection and persists locally. Check actual
copy/paste in both directions in an active RustDesk session as well; CI's
clipboard checks cannot exercise a connection between your workstations.
Explicit trigger, prompt, and packet copies retry a busy Windows clipboard for
up to three seconds on the Qt event loop; the newest copy cancels any pending
older request. Successful copying preserves the complete text, including Unicode
and trailing whitespace. A persistent lock displays a retry hint.
When Espanso is installed but a Windows restart fails, publishing/setup now
returns failure even though the match files were written. Do not treat the
installer's package step as proof that the running worker reloaded. For an
IPC `Access is denied` error, close the existing Espanso instance and relaunch
it in the same Windows account/session as the app, then retry the installer.

On Linux and macOS, `install.sh` does more than install `espansr`. Know its
side effects before running it:

- On Debian/Ubuntu it installs the Qt (xcb) runtime packages PyQt6 needs, plus
  `libfuse2` or `libfuse2t64` for the AppImage path, with `sudo apt-get`.
- When `espanso` is not on PATH it installs it: the upstream X11 `.deb` on
  apt distros (falling back to the X11 AppImage at `~/.local/bin/espanso`,
  wrapped in extract-and-run mode when FUSE is unavailable), or
  `brew install espanso` on macOS (Homebrew itself
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

### Clipboard after an expansion

Run this on each machine, including one you reach over RDP or RustDesk. Copy a
unique sentinel line, such as `sentinel-4271`, as the text to get back.

1. `espansr doctor` prints `Clipboard restore saved in default.yml: ...`, names
   the mode, and lists what it cannot observe. It reads the saved settings
   only; the steps below confirm what the running Espanso does. On Windows it
   also prints `Espanso process: running independently`, a separate check. A
   `[warn]` line means the saved setting leaves the prompt on the clipboard;
   run the command it prints. A configuration command that could not restart
   Espanso says so: restart Espanso before testing, since espansr cannot
   confirm it uses the saved settings.
2. Copy the sentinel, then type a short trigger into a plain text field and a
   long one such as `:one-shot` into another. Each field holds the exact,
   complete prompt, never the sentinel and never a cut-off prompt. Wait three
   seconds and paste: you get the sentinel.
3. Expand twice within two seconds, wait three seconds, and paste: you still
   get the sentinel.
4. Copy something new within two seconds after an expansion, wait three
   seconds, and paste. If the sentinel comes back instead of your newer copy,
   Espanso's restore ran after your copy: wait for the restore before copying,
   or shorten it with `--restore-delay`.
5. Inside the remote session, repeat steps 2 to 4. If a field ever receives the
   sentinel instead of the prompt, raise the delay with
   `espansr configure-remote-desktop --auto --restore-delay 3000` and repeat.
   With RustDesk clipboard sharing on, also copy on each side and paste on the
   other, in both directions.
6. Copy an image instead and repeat step 2: the image is replaced, because
   Espanso restores text only.
7. The `:coms` Copy prompt and Copy trigger buttons replace the clipboard on
   purpose; they are copies, not expansions, so nothing is restored after them.

### Local-only prompts

Create a prompt in the editor, check **Local only**, and save. `espansr list`
shows `(local only)`, the trigger expands, and `:coms` shows the Local only
note. With a template remote, `espansr push` leaves the prompt out of the
remote and `espansr pull` leaves it unchanged. Delete the last line of a
local-only file and run `espansr push`: it refuses, names the file, and sends
nothing; restore the line and it pushes the rest. A local-only template placed
in the install checkout makes `espansr sync` warn `Not committed: ... Move it
to` your template store, and `espansr sync` neither commits nor pushes it
(other Git tools in that checkout still can).

## 6. Developer Checks

```bash
pytest
ruff check .
black --check .
```

Expected: all tests pass, with zero lint or format errors.
