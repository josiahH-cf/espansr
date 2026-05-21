# Contributing to espansr

Thanks for contributing to `espansr`.

## Prerequisites

- Python 3.11+
- Linux/macOS/WSL2/Windows development environment

## Setup

```bash
python -m pip install -e ".[dev]"
```

## Branch Naming

Use:

```text
agent/type-short-description
```

Where:

- `agent`: your identifier (`copilot`, `codex`, `claude`, username, etc.)
- `type`: `feat`, `bug`, `refactor`, `chore`, `docs`
- `short-description`: 2-4 word kebab-case summary

Examples:

- `copilot/bug-wsl-wrapper-checks`
- `josiah/docs-verify-guide`

## Development Commands

```bash
# tests
pytest

# lint
ruff check .

# format
black .
```

## Pull Requests

Before opening a PR:

- Ensure user-facing behavior changes are covered by tests.
- Ensure tests pass locally.
- Ensure lint/format checks are run.
- Keep changes in scope for the request.
- Avoid adding TODO/placeholder text.

Use `.github/pull_request_template.md` and include:

- What changed and why
- How to verify
- Rollback notes

## Commit Guidance

- Keep commits focused and atomic.
- Reference the affected area or request.
- Do not include secrets or `.env` files.

## Routine Maintenance

Small stable-project changes need clear scope, focused edits, and normal verification. Read `AGENTS.md`, inspect the relevant files, make the focused change, run the relevant checks, and only push or merge when permissions and repository state make that safe.
