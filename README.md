# espansr

[![CI](https://github.com/josiahH-cf/espansr/actions/workflows/ci.yml/badge.svg)](https://github.com/josiahH-cf/espansr/actions/workflows/ci.yml)

`espansr` is a local-first GUI and CLI manager for [Espanso](https://espanso.org/) text expansion templates. It stores editable templates as JSON, validates them, and publishes the Espanso YAML files it manages.

This project installs from this repository with the OS-specific scripts below. A PyPI or pipx install path is not documented because this repository currently provides script-based source installs.

## Before You Install

You need:

- Python 3.11 or newer.
- Git, so you can get this repository.
- Espanso installed and started if you want text expansion triggers to work immediately.

`espansr` can install without Espanso, but triggers such as `:aopen`, `:coms`, `:sync`, and bundled template triggers only expand after Espanso is installed, started, and detected.

Windows PowerShell and WSL are separate environments. On a Windows host, use the Windows PowerShell installer unless you intentionally want a WSL-side `espansr` install.

## Get The Repo

```bash
git clone https://github.com/josiahH-cf/espansr.git
cd espansr
```

## Install

Run one command from the repository folder.

| Your environment | Command |
|------------------|---------|
| Windows PowerShell | `.\install.ps1` |
| Linux | `./install.sh` |
| macOS | `./install.sh` |
| Intentional WSL2 install | `./install.sh` |

Use PowerShell for the Windows command, not Command Prompt. If PowerShell blocks local scripts, run this in the same terminal first:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
```

The installer creates a local `.venv`, installs `espansr` in editable mode, runs `espansr setup`, copies bundled starter templates, validates them, records the install location for `espansr refresh` and `espansr sync`, and smoke-tests the CLI. When Espanso is already available, setup also generates the managed Espanso files for `:aopen`, `:coms`, `:sync`, and template expansion, and it creates a PATH-visible `espansr` command shim so the command works in non-interactive shells. On Windows that shim is an `espansr.cmd` launcher in `%LOCALAPPDATA%\espansr\bin`, which the installer appends to your user PATH; the virtual environment's `Scripts` folder is not added to PATH (a legacy entry from an older install is removed), so `python` and `pip` in new shells keep resolving to your own Python.

On Windows, the installer also looks for Espanso, registers and starts its service when it is available (before running setup, so the first publish succeeds), and runs `espansr configure-remote-desktop --auto` to tune Espanso for the machine's role (`-RemoteDesktop` and `-LocalOnly` force host or workstation mode; see [What It Manages](#what-it-manages) for the settings it writes). On Linux and macOS, `install.sh` installs Espanso when it is missing (`.deb` or AppImage on Linux, Homebrew on macOS), starts it, seeds its default config, and on GNOME/Wayland offers to run Chrome, VS Code, Obsidian, and gnome-terminal under XWayland so triggers fire inside them; pass `--no-espanso` or `--no-xwayland-apps` to opt out, and see [docs/VERIFY.md](docs/VERIFY.md) for every side effect and the revert command. On WSL2, Espanso must run on the Windows side (`espansr wsl-install-espanso`).

## Fresh Reinstall Reset

Only use this when you intentionally want to remove the local espansr install and local espansr data before reinstalling. It does not uninstall Espanso itself.

From Windows PowerShell in the repository folder. For the cleanest reset, use a terminal that is not currently running the `.venv` virtual environment.

```powershell
# Optional: restore Espanso's own config first (removes the espansr-managed block).
espansr configure-remote-desktop --revert
$launcherDir = Join-Path -Path $env:LOCALAPPDATA -ChildPath "espansr\bin"
Remove-Item -Recurse -Force .\.venv -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:APPDATA\espansr" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\espansr" -ErrorAction SilentlyContinue
Remove-Item -Force "$env:APPDATA\espanso\match\espansr.yml" -ErrorAction SilentlyContinue
Remove-Item -Force "$env:APPDATA\espanso\match\espansr-launcher.yml" -ErrorAction SilentlyContinue
Remove-Item -Force "$env:APPDATA\espanso\match\espansr-commands.yml" -ErrorAction SilentlyContinue
Remove-Item -Force "$env:APPDATA\espanso\match\espansr-sync.yml" -ErrorAction SilentlyContinue
$env:PATH = (($env:PATH -split ";") | Where-Object { $_ -and ($_ -ine $launcherDir) }) -join ";"
$userPath = (Get-Item HKCU:\Environment).GetValue("Path", "", "DoNotExpandEnvironmentNames")
if ($userPath) {
	$pathEntries = $userPath -split ";" | Where-Object { $_ -and ($_ -ine $launcherDir) }
	Set-ItemProperty -Path HKCU:\Environment -Name Path -Value ($pathEntries -join ";") -Type ExpandString
}
```

## First Use

```bash
espansr doctor
espansr gui
```

After Espanso is installed and running, type `:aopen` anywhere Espanso expands text to open the editor. Type `:coms` to open the command popup — it lists every trigger with previews, and you can also describe the job you need ("challenge finished research") or pick what you have and what you want to produce to surface the right prompt without remembering its trigger. See [docs/PROCESS.md](docs/PROCESS.md). Type `:sync` to update this machine: it runs `espansr sync`, which pulls the repository, commits and pushes your local changes, and reruns the installer; `espansr sync --no-push` pulls and reinstalls without committing or pushing. On Windows the `:sync` window stays open after the run so you can read the result.

Use `espansr publish` after template changes if you want to refresh Espanso output from the CLI. The GUI also publishes from the toolbar and saves edited templates into the same local template store.

To reinstall `espansr` in place after pulling updates or if an install looks broken, run `espansr refresh`. It reruns the correct OS installer (`install.ps1` on Windows, `install.sh` on Linux/macOS/WSL2), prints `ok` with a short desktop notification when it finishes, and opens the install folder if the reinstall fails.

## Verify From Windows PowerShell

```powershell
espansr --version
espansr list
espansr status
espansr doctor
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m black --check .
```

## If Espanso Is Missing

If the installer or `espansr doctor` cannot find Espanso, `espansr` is still installed, but text expansion triggers will not be active yet.

Install and start Espanso from [espanso.org](https://espanso.org/), then run:

```bash
espansr setup
espansr doctor
```

For an intentional WSL2 install, install/start Windows-side Espanso from WSL with:

```bash
espansr wsl-install-espanso
espansr setup
espansr doctor
```

Run `setup` before `doctor`: `doctor` fails until `setup` has generated the launcher files.

If you meant to install on the Windows host instead, open Windows PowerShell in this repository and run `.\install.ps1`.

## What It Manages

`espansr` manages:

- Live template JSON files in your platform-specific `espansr` config directory.
- Bundled starter templates copied from this repository on setup.
- Managed Espanso files named `espansr.yml`, `espansr-launcher.yml`, `espansr-commands.yml`, and `espansr-sync.yml`.
- One espansr-managed block in Espanso's `config/default.yml`, written by `espansr configure-remote-desktop` (the Windows installer runs it) and removable with `--revert`; the first edit keeps a backup as `default.yml.espansr-orig`. Host mode sets `win32_exclude_orphan_events: false`, `backend: Clipboard`, `preserve_clipboard: false`, `show_icon: false`, `show_notifications: false`, `key_delay: 30`, and `backspace_delay: 30`; workstation mode sets `win32_exclude_orphan_events: false`, `preserve_clipboard: true`, and `restore_clipboard_delay: 1500`. Everything outside the block is left byte for byte as you wrote it.
- Optional Git-backed template sync through `espansr remote`, `pull`, and `push`.
- Optional workflow manifests describing how bundled prompts relate (`espansr workflows`), user-saved handoff packets in the config directory (`espansr packet`), and structural output-contract checks (`espansr check-output`).

It does not replace Espanso, manage Espanso YAML beyond that block and its own match files, or delete unmanaged Espanso files. The process layer is optional: every trigger works directly, no workflow tracks a current step, and nothing runs automatically.

## More Help

| Document | Purpose |
|----------|---------|
| [docs/CLI.md](docs/CLI.md) | Commands, flags, GUI launch notes, and WSL helper details |
| [docs/TEMPLATES.md](docs/TEMPLATES.md) | Template schema, starter templates, publish behavior, and lifecycle details |
| [docs/PROCESS.md](docs/PROCESS.md) | Capability graph, workflow manifests, handoff packets, and output contracts |
| [docs/VERIFY.md](docs/VERIFY.md) | Practical post-install verification checklist |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Contributor setup, tests, linting, and formatting |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |

License: [MIT](LICENSE)

## Cursor Or VS Code Install Prompt

```text
You are helping me install espansr from Cursor or VS Code with an open folder. Assume I want the full install unless I explicitly say otherwise.

Goal: get or use the espansr repository, run the correct OS-specific installer, verify the install, and leave espansr usable.

First identify the operating system, shell, and current open folder path. Confirm whether the open folder is already the espansr repository by checking for README.md, pyproject.toml, install.sh, install.ps1, and the espansr/ package directory.

If the current folder is the espansr repository, use it. If it is an empty or general projects folder, clone https://github.com/josiahH-cf/espansr.git there and enter the repo. If the folder is not suitable and the right location is unclear, ask one minimal follow-up question for the desired parent folder.

Choose the installer from the actual OS and shell:
- Windows host in PowerShell: run .\install.ps1 from the repo folder. If local scripts are blocked, first run Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned in that terminal.
- Linux: run ./install.sh from the repo folder.
- macOS: run ./install.sh from the repo folder.
- WSL2: explain that Windows PowerShell and WSL are separate. Use ./install.sh only if I intentionally want a WSL-side espansr install; otherwise switch to Windows PowerShell and run .\install.ps1.

Run the installer to completion. Do not invent a PyPI, pipx, Homebrew, apt, winget, or package-manager install path for espansr.

After install, run espansr --version, espansr list, espansr status, and espansr doctor. If Espanso is missing, explain that espansr is installed but triggers will not expand until Espanso is installed and started. For WSL2, prefer espansr wsl-install-espanso for Windows-side Espanso setup; otherwise point me to https://espanso.org/ and rerun espansr setup and espansr doctor after Espanso starts.

Ask only the minimum follow-up questions needed for OS, shell, folder location, or permission prompts. Never ask me to choose among install methods unless the Windows-vs-WSL location is genuinely ambiguous.
```
