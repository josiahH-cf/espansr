# Codex Agent Instructions

Follow [../AGENTS.md](../AGENTS.md). This file only notes Codex-specific execution preferences.

## Execution

- Inspect the relevant files and git state before editing.
- Keep changes scoped to the user request.
- Preserve product behavior unless explicitly asked to change it.
- Do not touch templates, product docs, install scripts, WSL/PowerShell behavior, UI styles, packaging, or application code unless explicitly requested.

## Verification

Run the normal Python checks when relevant:

```bash
pytest
ruff check .
black --check .
```
