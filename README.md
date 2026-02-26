# automatr-espanso

A standalone GUI and CLI for managing [Espanso](https://espanso.org/) text expansion templates.

## Features

- Browse and search your Espanso templates
- Edit trigger strings with live YAML preview
- Sync templates to Espanso with one click or CLI command
- Auto-sync on a configurable interval
- WSL2 support: auto-detects Windows Espanso config path and restarts Espanso service after sync

## Install

```bash
./install.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### CLI

```bash
# Sync templates to Espanso
automatr-espanso sync

# Show Espanso status and config path
automatr-espanso status

# List templates with triggers
automatr-espanso list

# Launch the GUI
automatr-espanso gui
```

### GUI

```bash
automatr-espanso gui
```

## Template Format

Templates are JSON files stored in `~/.config/automatr-espanso/templates/` (Linux/WSL2) or `~/Library/Application Support/automatr-espanso/templates/` (macOS).

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
pytest
ruff check .
```
