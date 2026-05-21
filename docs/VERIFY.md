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
`espansr setup`, seed bundled templates, and smoke-test `espansr list` and
`espansr status`.

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
- `status` shows the detected Espanso config path, or clear Espanso install/start guidance.
- `doctor` prints `[ok]`, `[warn]`, or `[FAIL]` checks for Python, config, templates, Espanso, launcher files, and validation.

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
espansr doctor
espansr setup
```

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

## 6. Developer Checks

```bash
pytest
ruff check .
black --check .
```

Expected: all tests pass, with zero lint or format errors.