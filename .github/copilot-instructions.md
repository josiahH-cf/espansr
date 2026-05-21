# Copilot Instructions

Follow [../AGENTS.md](../AGENTS.md). If instructions conflict, `AGENTS.md` takes precedence.

## Scope

- Keep changes focused on the user request.
- Do not touch `templates/`, product docs, install scripts, WSL/PowerShell behavior, UI styles, packaging, or application behavior unless explicitly asked.
- Preserve existing CLI, GUI, publish/validate/sync, setup/doctor, `:aopen`, and `:coms` behavior.

## Checks

Use the normal project checks when relevant:

```bash
pytest
ruff check .
black --check .
```

Use normal task-by-task maintenance with clear scope and the standard Python checks.
