# Codex Agent Instructions

Follow [../AGENTS.md](../AGENTS.md). This file only notes Codex-specific execution preferences.

## Execution

- Inspect the relevant files and git state before editing.
- Keep changes scoped to the user request.
- Preserve product behavior unless explicitly asked to change it.
- Adding or revising bundled prompt notes is the default work: add the template JSON in `templates/`, register it in `espansr/core/discovery.py`, and run `python scripts/sync_discovery.py`.
- Do not touch install scripts, WSL/PowerShell behavior, UI styles, packaging, application code, or docs unrelated to the prompt-note set unless explicitly requested.

## Verification

Run the normal Python checks when relevant:

```bash
pytest
ruff check .
black --check .
```
