# Claude Code — Session Rules

Follow [AGENTS.md](AGENTS.md) for the repository rules. This file only adds Claude-specific session hygiene.

## Session Discipline

- Read `AGENTS.md` before editing.
- Inspect the relevant files and current git state before changing anything.
- Keep work scoped to the user request.
- Reflect every bundled prompt note everywhere it is discovered. Add the template JSON in `templates/`, register it in `espansr/core/discovery.py`, and run `python scripts/sync_discovery.py` to regenerate the `:espansr` quick help and `docs/TEMPLATES.md` from that single source. `tests/test_discovery_sync.py` enforces it. Surfacing helpful notes everywhere is the project's purpose.
- Do not touch install scripts, WSL/PowerShell behavior, UI styles, packaging, product code, or docs unrelated to the prompt-note set unless explicitly asked.
- Preserve existing behavior and tests.

## Verification

Use the normal Python project checks when relevant:

```bash
pytest
ruff check .
black --check .
```

Use normal task-by-task maintenance; no separate project-state machine or automated review path is required.

## Local Overrides

- Use `/CLAUDE.local.md` for personal behavior preferences.
- Use `.claude/settings.local.json` for local Claude settings.
- Do not put project policy in local override files.
