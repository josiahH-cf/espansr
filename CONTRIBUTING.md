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

Use short descriptive branches, as `AGENTS.md` describes:

```text
agent/type-short-description
user/type-short-description
```

Where:

- `agent/` is for changes made by an AI agent and `user/` for changes made by a person
- `type`: `feat`, `bug`, `refactor`, `chore`, `docs`
- `short-description`: 2-4 word kebab-case summary

Examples:

- `agent/feat-adversary-review-note`
- `user/docs-verify-guide`

## Bundled Prompt Notes

Adding or renaming a bundled prompt note is routine work, not a special request:

- Add the template JSON in `templates/`.
- Register it once in `espansr/core/discovery.py`.
- Run `python scripts/sync_discovery.py` to regenerate the `:espansr` quick help and the
  `docs/TEMPLATES.md` note list. `tests/test_discovery_sync.py` fails when they drift.

## Development Commands

```bash
# tests
pytest

# lint
ruff check .

# format
black .

# discovery surfaces
python scripts/sync_discovery.py --check
```

## Pull Requests

Before opening a PR:

- Ensure user-facing behavior changes are covered by tests.
- Ensure tests pass locally.
- Ensure lint/format checks are run.
- Keep changes in scope for the request.
- Avoid adding TODO/placeholder text.
- Add an entry under `## [Unreleased]` in `CHANGELOG.md` for any user-visible change,
  including new or revised bundled notes.

In the PR description include:

- What changed and why
- How to verify
- Rollback notes

## Commit Guidance

- Keep commits focused and atomic.
- Reference the affected area or request.
- Do not include secrets or `.env` files.

## Routine Maintenance

Small stable-project changes need clear scope, focused edits, and normal verification. Read `AGENTS.md`, inspect the relevant files, make the focused change, run the relevant checks, and only push or merge when permissions and repository state make that safe.
