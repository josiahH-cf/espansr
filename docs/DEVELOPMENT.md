# Development Guide

## Setup

```bash
git clone https://github.com/josiahH-cf/espansr.git
cd espansr
pip install -e .[dev]
```

This installs espansr in editable mode along with dev dependencies (pytest, pytest-qt, ruff, black).

## Running Tests

```bash
# Run the full test suite
pytest

# Run a single test file
pytest tests/test_espanso.py

# Run a single test
pytest tests/test_espanso.py::test_sync_produces_valid_yaml_v2_match_file
```

GUI tests run against Qt's offscreen platform by default (set in
`tests/conftest.py`, matching CI), so `pytest` never pops real windows or
steals focus locally. To deliberately watch the widgets render on a real
display, override the platform for one run:

```bash
QT_QPA_PLATFORM=windows pytest tests/test_commands_popup.py   # Windows
QT_QPA_PLATFORM=xcb pytest tests/test_commands_popup.py       # Linux/X11
```

## Linting & Formatting

```bash
# Lint
ruff check .

# Format check
black --check .

# Auto-format
black .

# Discovery surfaces (the :espansr quick help and the docs note list)
python scripts/sync_discovery.py --check
```

## Project Structure

```
espansr/                    Main Python package
├── __main__.py             CLI entry point and command dispatcher
├── core/
│   ├── atomic.py           Crash-safe file replacement helpers
│   ├── capabilities.py     Capability identity and artifact-type helpers
│   ├── cli_color.py        ANSI color helpers for CLI output
│   ├── command_catalog.py  Shared trigger catalog for the commands popup
│   ├── completions.py      Shell completion script generators
│   ├── config.py           Configuration management
│   ├── discovery.py        Single source for the :espansr quick help and docs note list
│   ├── install_meta.py     Install metadata recording (used by refresh and sync)
│   ├── output_contract.py  Structural output contracts for model-generated responses
│   ├── packets.py          Handoff packets: explicit, user-controlled context transport
│   ├── platform.py         Platform detection, per-platform paths, command shim
│   ├── recommend.py        Deterministic, local capability recommendations
│   ├── remote.py           Git-backed remote template sync
│   ├── templates.py        Template management, version history, bundled reconciliation
│   └── workflows.py        Workflow manifests: the home for process topology
├── integrations/
│   ├── espanso.py          Espanso YAML output, generated triggers, remote-desktop config
│   ├── orchestratr.py      orchestratr manifest and status
│   └── validate.py         Espanso config validation rules
└── ui/
    ├── commands_popup.py   Lightweight commands popup launched by :coms
    ├── main_window.py      Main GUI window and layout
    ├── packet_dialog.py    Handoff-packet dialog: preview, explicit save, reopen
    ├── template_browser.py Template browser widget
    ├── template_editor.py  Inline template editor with YAML/output preview
    ├── theme.py            PyQt6 theme configuration (dark/light)
    ├── variable_editor.py  Inline variable editor widget
    └── workflow_diagram.py Workflow diagrams for :coms and the editor window
scripts/
└── sync_discovery.py       Regenerate the :espansr quick help and docs note list
templates/                  Bundled starter templates (prompt notes)
└── _meta/workflows/        Bundled workflow manifests
tests/                      pytest suite; conftest.py defaults Qt to offscreen
```

## Conventions

- Python `snake_case` for functions and variables, `PascalCase` for classes
- Line length: 100 characters (configured in `pyproject.toml`)
- Every public function has a docstring
- No dead code — remove unused imports, variables, and functions
- Explicit error handling over silent failures

## Testing Conventions

- Tests live in `/tests/` using `test_*.py` naming
- Write tests before implementation (TDD)
- Each acceptance criterion gets at least one test
- For UI tests, use `pytest-qt` with deterministic widget-level assertions
- Tests must be deterministic — no flaky tests

## CI Pipeline

The CI pipeline (GitHub Actions) runs on pushes to `main` and on pull requests
targeting `main`:

- **Ruff** lint check
- **Black** format check
- **pytest** across Python 3.11, 3.12, 3.13
