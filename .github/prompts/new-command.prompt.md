---
agent: agent
description: 'Add a new espansr text expansion command — plan, create, validate, sync, commit, push'
---

# New Espansr Command

You are adding a new bundled text expansion template to espansr.

## Context

espansr templates are JSON files in `templates/` with this schema:

```json
{
  "name": "Human-Readable Name",
  "description": "Short description of what this command does.",
  "trigger": ":triggername",
  "content": "The full text that gets expanded when the trigger is typed."
}
```

Existing templates: list `templates/*.json` to see current commands and avoid trigger collisions.

## Process

Follow these steps in order. Do not skip the review step.

### Step 1 — Gather requirements

Ask what the command should do. Clarify:
- Trigger name (must start with `:`)
- What the expanded text should instruct or contain
- Whether it needs a secondary/removable section
- Whether it needs variables (most don't)

### Step 2 — Draft and review

Show the complete JSON file to the user before writing anything. Wait for explicit approval. Adjust if they request changes.

### Step 3 — Create the template file

Write the JSON file to `templates/<trigger_without_colon>.json`.
File naming: lowercase, underscores for spaces, no special characters.

### Step 4 — Import, validate, sync

Run these commands in sequence:

```
python -m espansr import templates/<filename>.json
python -m espansr validate
python -m espansr sync
```

If validate fails (duplicate trigger, missing trigger prefix), fix and re-run.
If import creates a duplicate (e.g., "Name (2)"), remove the old version from ~/.config/espansr/templates/ and re-import.

### Step 5 — Commit and push

```
git add templates/<filename>.json
git commit -m "feat: add :<trigger> bundled template

<one-line description of what the command does>"
git push
```

### Step 6 — Confirm

Show a summary table of the new trigger alongside all existing triggers.

## Rules

- Templates are static text unless the user explicitly requests variables.
- Do not hardcode paths, project names, or environment-specific details in content.
- Keep content clear, direct, and model-agnostic.
- Match the JSON formatting style of existing templates (2-space indent, ensure_ascii=False).
- One template per file. Filename matches the trigger name.
