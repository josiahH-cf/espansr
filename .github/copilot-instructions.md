# Copilot Instructions

Follow [../AGENTS.md](../AGENTS.md). If instructions conflict, `AGENTS.md` takes precedence.

## Scope

- Keep changes focused on the user request.
- Reflect every bundled prompt note across all of its discovery surfaces in the same change: the template JSON in `templates/`, the `:espansr` quick help (`templates/espansr_help.json`), and `docs/TEMPLATES.md`. Surfacing helpful notes everywhere is the whole project, not a special request.
- Do not touch install scripts, WSL/PowerShell behavior, UI styles, packaging, application behavior, or docs unrelated to the prompt-note set unless explicitly asked.
- Preserve existing CLI, GUI, publish/validate/sync, setup/doctor, `:aopen`, and `:coms` behavior.

## Checks

Use the normal project checks when relevant:

```bash
pytest
ruff check .
black --check .
```

Use normal task-by-task maintenance with clear scope and the standard Python checks.
