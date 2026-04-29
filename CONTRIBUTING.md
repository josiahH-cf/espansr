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

- Ensure acceptance criteria from the relevant spec are covered by tests for feature or bugfix work.
- For routine template, prompt, documentation, or small workflow maintenance, ensure the request scope and verification evidence are clear instead of creating unnecessary specs/tasks.
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
- For routine maintenance, reference the affected area or request instead.
- Do not include secrets or `.env` files.

## Routine Maintenance

Small stable-project changes can be handled without the full feature lifecycle: bundled template additions/edits/removals, prompt edits, docs updates, and small workflow corrections. Read `AGENTS.md` and the relevant workflow files first, make the focused change, run the relevant checks, and only push or merge when permissions and repository state make that safe.
