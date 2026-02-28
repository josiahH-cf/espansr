# espansr

[![CI](https://github.com/josiahH-cf/espansr/actions/workflows/ci.yml/badge.svg)](https://github.com/josiahH-cf/espansr/actions/workflows/ci.yml)

A standalone GUI and CLI for managing [Espanso](https://espanso.org/) text expansion templates.

## Platform Support

| Platform | Install | CLI | GUI | Notes |
|----------|---------|-----|-----|-------|
| Linux | `install.sh` | Yes | Yes | Requires Python 3.11+ |
| macOS | `install.sh` | Yes | Yes | Requires Python 3.11+ |
| Windows | `install.ps1` | Yes | Yes | Requires Python 3.11+ in PATH |
| WSL2 | `install.sh` | Yes | Yes | Auto-detects Windows-side Espanso config |

## Features

- Browse and search your Espanso templates
- Edit trigger strings with live YAML preview
- Inline variable editor with date format and multiline support
- Import external template files or directories
- Validate templates for common Espanso issues
- Sync templates to Espanso with one click or CLI command
- Auto-sync on a configurable interval
- Launcher trigger to open espansr from Espanso itself
- WSL2 support: auto-detects Windows Espanso config path and restarts Espanso service after sync

## Install

### Linux / macOS / WSL2

```bash
./install.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Windows

Requires Python 3.11+ installed and in PATH ([download](https://www.python.org/downloads/)).

```powershell
.\install.ps1
```

Or manually (PowerShell or Command Prompt):

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -e .
.\.venv\Scripts\espansr setup
```

## Usage

### CLI

```bash
# Sync templates to Espanso
espansr sync

# Show Espanso status and config path
espansr status

# List templates with triggers
espansr list

# Run post-install setup (copies templates, detects Espanso)
espansr setup

# Validate templates for common issues
espansr validate

# Import a template file or directory
espansr import <path>

# Launch the GUI
espansr gui
```

### GUI

```bash
espansr gui
```

## Template Format

Templates are JSON files stored in `~/.config/espansr/templates/` (Linux/WSL2), `~/Library/Application Support/espansr/templates/` (macOS), or `%APPDATA%/espansr/templates/` (Windows).

A bundled starter template (`espansr_help.json`) is automatically copied on first install via `espansr setup`.

```json
{
  "name": "Greeting",
  "content": "Hello, {{name}}!",
  "trigger": ":greet",
  "variables": [
    {"name": "name", "label": "Name", "default": "World"}
  ]
}
```

The `trigger` field is the Espanso trigger string (e.g., `:greet`). Templates without a trigger are shown in the browser but excluded from Espanso sync.

## Schema

Templates use a standard JSON format with `name`, `content`, `trigger`, and `variables` fields. The `trigger` field is used for Espanso matching; other fields (`variables`, `refinements`) are preserved as-is.

## Development

```bash
pip install -e .[dev]

# Run tests
pytest

# Lint
ruff check .

# Format check
black --check .
```
