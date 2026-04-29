# Boundaries & Bug Tracking

> Referenced from `AGENTS.md`. This is part of the canonical workflow — see `/governance/REGISTRY.md`.

## Boundaries

### Best Practices

- Read the spec before feature implementation; for routine maintenance, read the user request plus relevant canonical workflow/template/docs files
- Run tests before commit
- Include acceptance criteria evidence in feature PRs; include request/diff/check evidence in routine maintenance PRs
- Follow branch naming conventions
- Reference the constitution for alignment on design decisions

### Work Classification

Classify each request before editing:

| Class | Route | Examples |
|-------|-------|----------|
| Routine maintenance | Phase 8 stable maintenance path | Template add/edit/remove, prompt wording, docs updates, small workflow corrections |
| Feature work | Phases 2-7 | New app behavior, changed CLI/GUI behavior, new integrations |
| Bugfix | Bug Track | Reproducible defect, regression, failing behavior |
| Governance change | `governance/CHANGE_PROTOCOL.md` | Changes to authority, approval rules, security posture, or policy safeguards |

Routine maintenance can proceed end-to-end when requested, but only inside the requested scope and only after reading the relevant canonical files.

### Recommended Review Points

These are areas where extra awareness helps — not approval gates. All items below use the **Suggest** advisory tier (see `workflow/ROUTING.md → Advisory Tier Reference`):

- Adding new dependencies
- Modifying CI workflows
- Changing the constitution — consider using `/compass-edit` for traceability. Exception: Phase 2 Compass directly populates `.specify/constitution.md` during initial discovery.
- Modifying `AGENTS.md`
- Architectural decisions not covered by the spec

### Safe Automatic Completion

Agents may commit, push, open a PR, and merge routine maintenance only when all conditions hold:

- The user asked for the change or for end-to-end completion.
- The diff contains only current-task files and no unrelated dirty changes.
- Required local checks pass, or skipped checks are justified.
- Git credentials, remote permissions, branch state, and repository rules allow the step.
- No human approval gate, protected branch rule, security/privacy decision, or destructive action is involved.

If any condition is false, stop after the last safe step and report the remaining manual action.

### Avoid

- Committing secrets or `.env` files
- Modifying files outside the assigned scope
- Skipping tests
- Making decisions not traceable to a spec, constitution principle, bug entry, or routine maintenance request

## Bug Tracking

Use `/bug` (Claude) or `phase-7b-bug.prompt.md` (Copilot) from any phase:

```
Description: [what's wrong]
Location: [file:line or component]
Phase found: [which phase discovered this]
Severity: blocking | non-blocking
Expected: [what should happen]
Actual: [what does happen]
Fix-as-you-go: yes | no
```

- Small bugs (fix-as-you-go = yes): fix in place, log the fix
- Large bugs: add to backlog as a spec, assign model + branch when picked up
- Backlog review cycle: treat queued bugs as specs with full AC/branch/model assignment
