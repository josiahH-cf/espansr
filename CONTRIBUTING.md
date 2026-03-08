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

# workflow lint (advisory)
scripts/workflow-lint.sh
```

## Pull Requests

Before opening a PR:

- Ensure acceptance criteria from the relevant spec are covered by tests.
- Ensure tests pass locally.
- Ensure lint/format checks are run.
- Keep changes in scope for the feature/task.
- Avoid adding TODO/placeholder text.

Use `.github/pull_request_template.md` and include:

- What changed and why
- How to verify
- Rollback notes

## Commit Guidance

- Keep commits focused and atomic.
- Reference the related spec/task file when relevant.
- Do not include secrets or `.env` files.
