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
pytest tests/test_espanso.py::test_sync_creates_yaml
```

## Linting & Formatting

```bash
# Lint
ruff check .

# Format check
black --check .

# Auto-format
black .
```

## Project Structure

```
espansr/              Main Python package
├── __main__.py       CLI entrypoint and command dispatcher
├── core/
│   ├── config.py     EspansoConfig dataclass, config I/O
│   ├── platform.py   PlatformConfig — single source of truth for paths
│   ├── templates.py  TemplateManager, template CRUD
│   ├── cli_color.py  Colored CLI output helpers
│   └── completions.py Shell tab completion generator
├── integrations/
│   ├── espanso.py    Espanso YAML sync, launcher generation
│   ├── orchestratr.py Orchestratr manifest and status
│   └── validate.py   Template validation rules
└── ui/
    ├── main_window.py    Main GUI window and layout
    ├── template_browser.py Template list widget
    ├── template_editor.py  Editor with YAML/output preview
    ├── variable_editor.py  Inline variable editing
    └── theme.py            Dark/light mode detection
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

The CI pipeline (GitHub Actions) runs on every push and PR:

- **Ruff** lint check
- **Black** format check
- **pytest** across Python 3.11, 3.12, 3.13
