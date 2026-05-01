# Workflow Playbook

This document defines how an agent executes feature work from spec to merged PR, and how routine stable-maintenance work is handled without unnecessary feature overhead.

## Global Rules

> These rules are **Recommend** tier (see `workflow/ORCHESTRATOR.md → Advisory Tiers`). Agents should follow them by default but may adapt when context justifies deviation.

- For feature work, work from a single feature ID at a time.
- For feature work, keep branch scope aligned to the spec's Affected Areas.
- For routine maintenance, keep branch scope aligned to the user request and the relevant canonical files.
- Recommended: Record non-obvious decisions in `/decisions/` before continuing.
- Move forward only when the current phase gate is satisfied (verify via PLAYBOOK gates below).
- Reference `.specify/constitution.md` for alignment on all design decisions.

## Stable Maintenance Contract

Routine maintenance is allowed when all of these are true:

- The request is limited to templates, prompts, documentation, or small workflow wording/corrections.
- No new user-facing application behavior, dependency, security boundary, or architecture decision is introduced.
- No active task claim or dirty worktree change would be overwritten.
- The relevant canonical instructions and touched files have been read first.

Routine maintenance flow:

1. Classify the request as routine maintenance, bugfix, feature work, or governance change.
2. Read `AGENTS.md`, `workflow/STATE.json`, and the relevant workflow/prompt/docs/template files.
3. Inspect git state and avoid unrelated changes.
4. Make the focused edit.
5. Run relevant checks from `workflow/COMMANDS.md` and any specific template/documentation validation that applies.
6. Summarize changed files and verification evidence.
7. If the user asked for completion and repository state allows it, commit, push, open a PR, and merge according to `workflow/CONCURRENCY.md → Automatic Git Workflow`.

Routine maintenance does not require new `/specs/` or `/tasks/` files. If the change grows beyond the routine scope, stop and route to the feature lifecycle, Bug Track, or governance protocol.

## Project-Level Phase Gates

| Phase | Required Input | Required Output | Gate to Advance |
| ----- | -------------- | --------------- | --------------- |
| Compass | Scaffold files placed | `.specify/constitution.md` populated | All relevant themes addressed (no `[PROJECT-SPECIFIC]` placeholders in covered sections); ambiguities documented |
| Define Features | Constitution | Feature specs with Compass mapping | At least one feature spec exists in `/specs/` with Compass capability mapping; every constitution capability has at least one feature mapping; no orphan features (every feature traces to a capability) |
| Scaffold Project | Feature specs | `workflow/COMMANDS.md` Code Conventions + Core Commands | Neither section contains `[PROJECT-SPECIFIC]` |
| Fine-tune Plan | Architecture plan | `/tasks/[feature-id]-[slug].md` files + ordered AC/task/model/branch mappings | Every active spec has a matching task file; all ACs mapped to tasks |
| Code | Fine-tuned specs + task files + pre-tests | Passing code on feature branch | All tasks marked Complete, tests pass |
| Test | Implementation | Verified ACs, bug log reviewed | No blocking bugs, all ACs pass in `/test post` mode; launch/smoke check passes or explicitly skipped (see phase-7-test.md); `scripts/workflow-lint.sh` run (advisory — non-blocking; uses Suggest tier). Then fork detection selects review path (see `workflow/ORCHESTRATOR.md → Fork Detection`). |
| Review Bot | Post-test pass | Merged PR, PR ready/manual step, or findings file | All rubric categories PASS, tests PASS, lint PASS → commit/push/PR and merge when safe; any FAIL → findings file written, route back to Code |
| Maintain | Shipped features or routine request | Maintenance mode active or focused routine update | Routine update verified, or maintenance level recorded in STATE.json and all items for selected level completed |
| Operationalize | Maintenance level selected + interview answers | `.github/maintenance-config.yml` + generated GitHub Actions workflows | Config file records all interview decisions; at least one workflow generated per enabled category; notification routing configured; all workflow YAML valid |

## Feature-Level Phase Contract

| Phase | Required Input | Required Output | Gate to Advance |
| ----- | -------------- | --------------- | --------------- |
| Scope | Issue or request | `/specs/[feature-id]-[slug].md` | 3–7 testable acceptance criteria with IDs |
| Plan | Spec | `/tasks/[feature-id]-[slug].md` | Every criterion mapped to one or more tasks |
| Test (`pre`) | Task file + spec | Failing tests committed | At least one failing test per criterion |
| Implement | Failing tests + task file | Passing code commits | Task statuses updated with evidence |
| Test (`post`) | Implemented feature + task file + spec | AC verification report + bug entries | All ACs verified or logged as bugs; launch/smoke check executed or explicitly skipped with reason |
| Bot Review | Post-test pass + spec + task file + diff | Rubric review report | All 6 rubric categories PASS, tests PASS, lint PASS, launch check PASS or SKIPPED |
| Conditional Merge (bot) | Bot review PASS | Committed, pushed, PR opened, merged when allowed | PR squash-merged and branch deleted when permissions/checks/rules allow; otherwise PR left ready with manual step reported |
| Review (manual) | Bot review FAIL or manual override | PASS/FAIL review report | All criteria have passing test evidence |
| PR | Review PASS (bot or manual) | Open PR with required checklist | CI and policy checks green; lint report reviewed (advisory) |
| Merge | Approved PR | Merged branch + cleanup | Bot conditional merge or human merge approval; post-merge test pass on base branch when practical (see `workflow/CONCURRENCY.md → Automatic Git Workflow → Merge on Completion`); feature branch and worktree cleaned up after safe merge |

## Routine Maintenance Definition of Done

A routine maintenance change is done when all are true:

- The diff is limited to the requested files and any directly related generated prompt/documentation counterpart.
- Relevant checks have passed or an explicit skip reason is recorded.
- No unrelated dirty worktree changes were included.
- The final summary states what changed, how it was verified, and whether commit/push/PR/merge was completed or why it safely stopped.

## Definition of Done

A feature is done only when all are true:

- Task file status counts show zero remaining tasks.
- Full test suite passes.
- Review report is PASS with criterion-level evidence.
- PR template is complete with verification and rollback.

## Context Discipline

- Start each phase in a fresh session when context quality drops.
- Prefer file artifacts over chat memory for continuity.
- If compacting repeatedly, split the feature and continue in a new branch.
- Persist orchestration state transitions in `/workflow/STATE.json` when using `/continue`.
