# Build, Test & Lint Commands

> Referenced from `AGENTS.md`. This is part of the canonical workflow — see `/governance/REGISTRY.md`.

These values are set with initial values during Phase 1 (initialization) and finalized during Phase 4 (Scaffold Project) based on architecture reasoning.

## Core Commands

| Command | Value |
|---------|-------|
| Install | `python -m pip install -e ".[dev]"` |
| Build | `python -m pip install build && python -m build` |
| Test (all) | `pytest` |
| Test (single) | `pytest tests/<file>.py::test_<name>` |
| Lint | `ruff check .` |
| Format | `black .` |
| Type-check | `not applicable` |
| Lint (workflow) | `scripts/workflow-lint.sh` |
| Review Bot | `/review-bot` (Claude) or `phase-7a-review-bot.prompt.md` (Copilot) |

## Project Snapshot

- Name: `espansr`
- Description: Espanso text expansion template manager with GUI + CLI sync and validation tools.
- Primary language/framework: Python 3.11+, PyQt6, pytest, ruff, black.

## Code Conventions

- Functions and variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Files and directories: `snake_case` for Python modules; lowercase directories for project areas.

## Architecture Map

- `espansr/`: application package (CLI entrypoint, core services, integrations, and GUI modules).
- `espansr/core/`: shared platform/config/template/completion primitives used by CLI and GUI.
- `espansr/integrations/`: Espanso, orchestratr, and validation integration boundaries.
- `espansr/ui/`: desktop UI windows/widgets and interaction flow.
- `tests/`: pytest suite for CLI, integrations, platform behavior, and GUI interactions.
- `templates/`: bundled starter templates packaged for setup/bootstrap.
- `docs/`: user and developer documentation (CLI, development, templates, verification).
- `workflow/`: control-plane lifecycle, routing, and execution contracts.
- `governance/`: policy-change and registry guardrails.
- `specs/`, `tasks/`, `decisions/`: planning, execution, and architecture decision artifacts.
- `.github/`: prompts, agents, CI/workflow automation, and issue/PR templates.
- `.claude/` and `.codex/`: agent-specific command/config overlays.
- `scripts/`: workflow and policy utility scripts.
- `meta-prompts/`: source-of-truth prompt templates used to generate installed prompts.
