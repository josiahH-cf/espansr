# Copilot Instructions

> **Routing & conventions:** Follow the rules in ../AGENTS.md. If any instruction below conflicts with AGENTS.md, AGENTS.md takes precedence.

## Project Standards

- Read `/AGENTS.md` before starting any task
- Follow `/workflow/PLAYBOOK.md` for phase gates and `/workflow/FILE_CONTRACTS.md` for artifact requirements
- Follow `/workflow/FAILURE_ROUTING.md` when blocked
- Classify each request first: routine maintenance, feature work, bugfix, or governance change

## Completions

Follow naming conventions and patterns from `workflow/COMMANDS.md` Code Conventions section.

## Code Review

- Flag functions over 50 lines
- Flag nesting deeper than 3 levels
- Flag missing error handling on I/O operations
- Flag tests that assert only the happy path
- Flag hardcoded values that should be configuration
- For feature work, verify every acceptance criterion from the linked spec has a test
- For feature work, verify task file criteria mappings (`AC-*`) align with tests and PR evidence
- For routine maintenance, verify the diff matches the request and relevant checks were run or explicitly skipped

## PR Descriptions

- State what changed, why, and how to verify
- Link the Feature ID plus matching spec/task files when they exist
- For routine maintenance without a spec/task, identify the request type and affected files instead
- List files changed, grouped by concern

## Coding Agent

- Read the linked spec before starting feature work; for routine maintenance, read the relevant canonical workflow/template/docs files
- Do not modify files outside the scope described in the issue
- Treat `/AGENTS.md` and `/workflow/*.md` as canonical; do not redefine policy in ad hoc notes

## Session Bootstrap

At the start of every session:
1. Read `AGENTS.md` for project conventions and phase navigation
2. Read `workflow/STATE.json` for current project state
3. If a task is active, read the task file from `/tasks/`
4. If no task is active and the request is routine, use the Phase 8 stable maintenance path

See `workflow/ORCHESTRATOR.md` for the full loop contract.

## Key References

- Agent routing and branch naming: `workflow/ROUTING.md`
- Build/test/lint commands: `workflow/COMMANDS.md`
- Behavioral boundaries: `workflow/BOUNDARIES.md`
- Concurrency safety: `workflow/CONCURRENCY.md`
- Orchestrator loop: `workflow/ORCHESTRATOR.md`
