---
agent: agent
description: 'Ongoing maintenance — documentation, compliance, and standards enforcement'
---
<!-- role: derived | canonical-source: meta-prompts/phase-8-maintain.md -->
<!-- generated-from-metaprompt -->

[AGENTS.md](../../AGENTS.md)
[workflow/PLAYBOOK.md](../../workflow/PLAYBOOK.md)
[workflow/FILE_CONTRACTS.md](../../workflow/FILE_CONTRACTS.md)

# Phase 8 — Maintain

**Objective:** Maintain project health through focused routine updates, documentation, compliance, and standards enforcement. Maintenance is an **ongoing mode**, not a terminal "done" state.

**Trigger:** Feature shipped (post-Phase 7), periodic maintenance trigger, or a concrete stable-maintenance request from the maintainer.

**Entry commands:**
- Claude: `/maintain`
- Copilot: `phase-8-maintain.prompt.md`

---

## Maintenance Level Selection

On entry, select a maintenance level and record it in `/workflow/STATE.json` (`maintenanceLevel` field). The level determines scope for this maintenance pass.

| Level | Scope | When to Use |
|-------|-------|-------------|
| **Light** | Docs + lint + stale TODO sweep | Low-touch periodic check-in |
| **Standard** | Light + compliance check + dependency audit + bug log review | Default recommended level |
| **Deep** | Standard + security audit + architecture review + performance regression check | Pre-release, scheduled audit, or after major changes |

If no level is specified, default to **Standard**.

## Request Classification

Before editing, classify the request:

| Class | Route |
|-------|-------|
| Routine maintenance | Handle directly in Phase 8 |
| Bugfix | Route through `/bug` or `/bugfix` |
| Feature work | Route through `/define-features` / `/implement` lifecycle |
| Governance change | Route through `governance/CHANGE_PROTOCOL.md` |

Routine maintenance includes bundled template additions/edits/removals, prompt edits, documentation updates, and small workflow wording corrections. These do not require new specs or task files when they do not change application behavior, security posture, architecture, or governance safeguards.

## What Happens

### Routine Stable-Maintenance Request

When the user asks for a focused template, prompt, documentation, or small workflow correction:

1. Read `AGENTS.md`, `workflow/STATE.json`, and the relevant canonical workflow/prompt/docs/template files.
2. Inspect git state and avoid unrelated changes.
3. Make only the focused edit requested.
4. Update direct counterparts when needed for consistency, such as `meta-prompts/` plus `.github/prompts/` copies.
5. Run relevant checks from `workflow/COMMANDS.md`; for template changes, also validate/import/sync as applicable.
6. Summarize the diff and verification evidence.
7. If the user requested completion and permissions/repository state allow it, commit, push, open a PR, and merge according to `workflow/CONCURRENCY.md → Automatic Git Workflow`.

Stop before git completion if unrelated dirty files are present, checks fail, credentials are unavailable, CI or branch protection cannot be satisfied, or human approval is required.

### Initial Setup (first run after shipping)
1. Select maintenance level (prompt if not provided)
2. Generate README from constitution + feature specs
3. Generate CONTRIBUTING from AGENTS.md conventions
4. Produce release notes from implemented features
5. Run security baseline check

### Ongoing (periodic)
Execute items based on selected level:

**Light:**
1. Documentation drift — README/CONTRIBUTING vs current state
2. Auto-corrections — lint, format, stale TODOs

**Standard** (includes Light):
3. Compliance check — all specs have tests, all tests pass
4. Dependency audit — outdated or vulnerable
5. Bug log review — stale entries flagged or closed

**Deep** (includes Standard):
6. Security audit — vulnerability scan + policy review
7. Architecture review — drift from constitution principles
8. Performance regression check

## Feature Re-entry

Maintenance mode does not block new feature work. A project in maintenance can start new `/compass-edit` → `/define-features` → `/implement` cycles at any time. Feature-level phases run within ongoing maintenance — the project does not need to "exit" maintenance first. After the feature ships, return to the current maintenance level.

## Gate

- For routine maintenance: request classified, relevant context read, focused diff verified, no unrelated changes included
- For periodic maintenance: maintenance level selected and recorded in `STATE.json`
- README exists and reflects current project state
- CONTRIBUTING exists with branch naming, commit format, PR requirements
- All items for the selected level completed
- No stale compliance issues (Standard and Deep)
- Security baseline checked (Deep)

## Output

- Focused routine update with verification evidence, when applicable
- Updated documentation
- Compliance report (scope depends on level)
- Bug log entries for any findings
- `STATE.json` remains or is updated to `projectPhase: "8-maintain"`; `maintenanceLevel` set for periodic passes

## Rules

- Do not change application logic — maintenance only
- Commit maintenance changes separately from feature work
- Do not create specs/tasks for routine maintenance unless the change becomes feature work
- Commit/push/PR/merge only when requested and safe under repository state and permissions
- Maintenance is ongoing — never set project status to a terminal "completed" state

## See Also

- Bug tracking parallel workflow: `AGENTS.md → Bug Track`
