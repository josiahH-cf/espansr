# Project

- Project name: automatr-espanso
- Description: A standalone Espanso text expansion template manager with CLI and GUI. No LLM dependency.
- Primary language/framework: Python with PyQt6

# Build

- Install: `./install.sh` (recommended) or `pip install -e .` / `pip install -e .[dev]` for development
- Build: `not applicable` (setuptools package, no separate build step required for local development)
- Test (all): `pytest`
- Test (single): `pytest path/to/test_file.py::test_name`
- Lint: `ruff check .`
- Format: `black .`
- Type-check: `not applicable`

# Architecture

- `automatr_espanso/`: Main Python package and app entrypoint.
- `automatr_espanso/core/`: Core configuration and template handling.
- `automatr_espanso/integrations/`: Espanso sync integration.
- `automatr_espanso/ui/`: PyQt6 user interface screens.
- `templates/`: Bundled Espanso-specific template JSON files (starts empty; add static snippets here).
- `tests/`: Test suite.

# Conventions

- Functions and variables: standard Python `snake_case` (classes use `PascalCase`)
- Files and directories: standard Python module naming with lowercase and `snake_case` where needed
- Prefer explicit error handling over silent failures
- No dead code — remove unused imports, variables, and functions
- Every public function has a doc comment
- No hardcoded secrets, URLs, or environment-specific values

# Core Code Lineage

`config.py` and `templates.py` are adapted copies of the same files from `automatr-prompt`.
They will diverge over time — this is intentional. Do not attempt to re-merge or share them.
Key differences from automatr-prompt:
- `EspansoConfig` replaces `LLMConfig`
- Config dir is `automatr-espanso` (not `automatr`)
- `TemplateManager` has `iter_with_triggers()` method

# Testing

- Write tests before implementation
- Place tests under `/tests/` using `test_*.py` naming
- For UI behavior, use `pytest-qt` and prefer deterministic widget-level tests over timing-dependent flows
- Each acceptance criterion requires at least one test
- Do not modify existing tests to accommodate new code — fix the implementation
- Run the full test suite before committing
- Tests must be deterministic — no flaky tests in the main suite

# Dependencies

- PyYAML: required for Espanso YAML file generation
- PyQt6: required for GUI
- No `requests` dependency
- No llama.cpp dependency
- No dependency on `automatr-prompt` at runtime

# Commits

- One logical change per commit
- Present-tense imperative subject line, under 72 characters
- Reference the spec or task file in the commit body when applicable

# Security

- No secrets in code or instruction files
- Use environment variables for all credentials
- Sanitize all external input
- Log security-relevant events
