# espansr

[![CI](https://github.com/josiahH-cf/espansr/actions/workflows/ci.yml/badge.svg)](https://github.com/josiahH-cf/espansr/actions/workflows/ci.yml)

`espansr` is a local-first GUI and CLI manager for [Espanso](https://espanso.org/) text expansion templates. It stores editable templates as JSON, validates them, and publishes managed Espanso YAML output.

The project is installed from this repository. A PyPI or pipx install path is not documented here because the repository currently provides script-based source installs.

## Quick Start

```bash
git clone https://github.com/josiahH-cf/espansr.git
cd espansr
```

Install with the script for the environment where you want to run `espansr`:

```bash
# Linux / macOS / intentional WSL-side install
./install.sh

# Windows host install from PowerShell
.\install.ps1
```

Windows PowerShell and WSL are separate environments. If your machine is a Windows host, use `.\install.ps1` unless you intentionally want a WSL-side `espansr` install that manages Windows-side Espanso config files.

First use:

```bash
espansr doctor
espansr gui
espansr publish
```

After setup, type `:aopen` anywhere Espanso expands text to open the editor, or type `:coms` to open the command popup.

## What espansr Manages

`espansr` manages:

- Live template JSON files in your platform-specific `espansr` config directory.
- Bundled starter templates copied from this repository on setup.
- Managed Espanso files named `espansr.yml`, `espansr-launcher.yml`, and `espansr-commands.yml`.
- Optional Git-backed template sync through `espansr remote`, `pull`, and `push`.

`espansr` does not replace Espanso, manage arbitrary Espanso YAML, or delete unmanaged Espanso files.

## Template Lifecycle

Create or edit templates with `espansr gui`, or import JSON with:

```bash
espansr import file.json
```

Validate templates before publishing:

```bash
espansr validate
```

Publish local templates to Espanso:

```bash
espansr publish
espansr publish --dry-run
```

Sync template JSON across machines with an existing Git remote:

```bash
espansr remote set git@github.com:USER/REPO.git
espansr pull
espansr push
```

Inspect or apply bundled starter updates:

```bash
espansr starters
espansr starters --apply
```

Retire a template and refresh managed Espanso output:

```bash
espansr retire :trigger
espansr retire template_file.json --dry-run
```

## Common Commands

```bash
espansr gui              # open the visual editor
espansr publish          # write managed Espanso YAML
espansr pull             # pull remote templates, then publish locally
espansr push             # push local JSON templates to the remote
espansr starters         # inspect bundled starter drift
espansr retire TARGET    # back up, delete, and publish after retirement
espansr list             # list templates with triggers
espansr status           # show Espanso connection details
espansr validate         # check template issues
espansr doctor           # run setup diagnostics
```

See [docs/CLI.md](docs/CLI.md) for all commands and flags.

## Platform Support

| Platform | Install | CLI | GUI | Notes |
|----------|---------|-----|-----|-------|
| Linux | `./install.sh` | yes | yes | Python 3.11+ |
| macOS | `./install.sh` | yes | yes | Python 3.11+ |
| Windows | `.\install.ps1` | yes | yes | Preferred for Windows hosts |
| WSL2 | `./install.sh` | yes | yes | Separate WSL install; uses Windows-side Espanso |

If a WSL install cannot find Espanso, install and start Espanso on Windows first or run:

```bash
espansr wsl-install-espanso
```

## GUI Notes

The GUI includes template browsing, editing, variable editing, previews, import, remote pull, and publishing. `Ctrl+S` publishes, `Ctrl+N` creates a new template, `Ctrl+I` imports, `Ctrl+F` searches, and `Delete` starts the delete-with-undo flow.

Deleting a template from the GUI backs it up locally, removes the JSON file after the undo window, and publishes the remaining templates so managed Espanso output no longer contains the retired trigger.

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/CLI.md](docs/CLI.md) | Command reference |
| [docs/TEMPLATES.md](docs/TEMPLATES.md) | Template schema and lifecycle details |
| [docs/VERIFY.md](docs/VERIFY.md) | Post-install and release verification checklist |
| [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) | Contributor setup and checks |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |

## Template Example

```json
{
  "name": "Greeting",
  "content": "Hello, {{name}}! Thanks for reaching out.",
  "trigger": ":greet",
  "variables": [
    { "name": "name", "label": "Name", "default": "there" }
  ]
}
```

Typing `:greet` expands through Espanso after `espansr publish`.

## Development

Contributor setup, tests, linting, and formatting are documented in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

## License

[MIT](LICENSE)
