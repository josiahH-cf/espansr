# Claude Code — Session Rules

## Session Bootstrap

At the start of every session, before any work:
1. Read `AGENTS.md` — project routing and phase navigation
2. Read `workflow/STATE.json` — current project state (including `advisoryProfile` for guidance tone and `forkActivationLevel` for fork sensitivity)
3. Read `.specify/constitution.md` — project identity (if it exists)
4. Read the active task file (if `currentTaskFile` is set in state)
5. For `/continue` sessions, read `workflow/archive/ORCHESTRATOR.md` as the historical loop contract reference

This ensures context is grounded in reality, not memory from previous sessions.
Advisory guidance adapts to `advisoryProfile`; the detailed historical model is in `workflow/archive/ORCHESTRATOR.md`.

Strictly follow the rules in ./AGENTS.md for all project conventions, routing, commands, and boundaries.

Canonical workflow policy lives in `AGENTS.md`, active `/workflow/*.md` files, and `/governance/*.md`.
This file is an adapter for Claude-specific session mechanics and command references.

## Context Discipline

- Start every task in a fresh session
- Compact at 60 percent context usage — do not wait until 95 percent
- If you compact more than twice, stop — the task is too large
- Include only files the current task touches via @ references
- Never carry planning context into implementation — write to a file, clear, restart

## Planning

- Begin complex work in Plan Mode
- Write plans to `/specs/` or `/tasks/` — never keep plans only in chat

## Testing

- Follow `AGENTS.md` and `workflow/COMMANDS.md` for routine maintenance checks. Archived phase-gate references live under `workflow/archive/`.
- Use a subagent for test verification when the test suite is large

## Implementation

- One task per session
- Orient first: read the task file, relevant source files, and test file before writing
- Follow existing patterns — read before writing
- When uncertain, write the decision to `/decisions/` before proceeding

## Scope Discipline

- Do not generate entire modules in a single pass
- Do not refactor code outside the current task scope

## Development Principles

Use these baseline principles for context discipline, commit habits, worktree usage, and session hygiene:

- Start every feature in a fresh session; compact at 60% context
- Never keep plans only in chat — write to `/specs/` or `/tasks/`
- Write failing tests before implementation (use `/test` pre-impl mode)
- Run `/test` again post-implementation to verify all ACs pass

## Escalation

- Use `workflow/archive/FAILURE_ROUTING.md` for historical retry, model-switch, and escalation paths
- If policy docs conflict, follow precedence in `AGENTS.md`

## Claude-Specific Commands

Commands are organized by workflow phase. Run `/continue` to auto-advance through phases.

### Setup (Phase 1)

- `/initialization` — Phase 1: detect fresh vs existing vs scaffolded repo, place or merge scaffold assets, then route to Compass or `/update-workflow`
- `/update-workflow` — Update scaffold to latest version from local source or upstream (can be invoked at any time)

### Interview & Planning (Phases 2–5)

- `/compass` — Phase 2: Dynamic discovery interview to establish project identity → outputs `.specify/constitution.md`
- `/compass-edit` — Edit mode for the constitution (approval-gated)
- `/define-features` — Phase 3: Translate constitution into feature specs
- `/scaffold` — Phase 4: Reason about architecture, produce plan (no code)
- `/fine-tune` — Phase 5: Create ordered specs with model assignments and branches

### Build & Test (Phases 6–7)

- `/implement` — Phase 6: TDD implementation from spec
- `/build-session` — Phase 6 session mode: sustained multi-feature implementation session
- `/test` — Phase 7: Run tests against acceptance criteria, log bugs
- `/review-bot` — Phase 7a: Automated full-rubric review + auto-merge (default merge path)
- `/bug` — Bug Track: Log a bug from any phase (lightweight, non-interrupting)
- `/bugfix` — Structured bug fix: reproduce → diagnose → fix → verify → PR

### Maintain & Continue (Phases 8–9+)

- `/maintain` — Phase 8: Documentation, compliance, standards enforcement
- `/operationalize` — Phase 9: Interview-driven automation config (schedules, notifications, release publishing)
- `/continue` — Orchestrator: reads project state, determines phase, auto-advances, keeps building

### Review & Ship

- `/review-session` — Review completed feature branch, create PR, ship
- `/cross-review` — Independent cross-agent review (optional)

## Precedence

If any instruction in this file conflicts with AGENTS.md, AGENTS.md takes precedence.

## Personal Overrides

- Use `/CLAUDE.local.md` (project root, gitignored) for personal behavioral preferences
- Use `.claude/settings.local.json` (inside `.claude/`, gitignored) for permission-mode overrides
- Do not put project rules in either local file
