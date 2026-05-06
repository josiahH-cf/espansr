# Canonical Policy Registry

This registry names the active policy and workflow files for the current
repository. Archived lifecycle material remains available for historical
reference, but routine stable maintenance should not require reading archived
workflow files unless the active request specifically concerns those files.

## Active Canonical Files

| File | Authority | Owner |
|---|---|---|
| `/AGENTS.md` | Entrypoint, project overview, phase routing, and stable maintenance path | Human maintainer |
| `/workflow/STATE.json` | Machine-readable orchestration state for `/continue` | Orchestrator agent |
| `/workflow/COMMANDS.md` | Build/test/lint commands, code conventions, and project map | Human maintainer |
| `/workflow/ROUTING.md` | Advisory routing hints, branch naming, and active concurrency summary | Human maintainer |
| `/governance/CHANGE_PROTOCOL.md` | Policy mutation rules | Human maintainer |
| `/governance/POLICY_TESTS.md` | Policy validation expectations | Human maintainer |
| `/.specify/constitution.md` | Project identity and scope | Human maintainer |
| `/.github/REVIEW_RUBRIC.md` | Review scoring rubric | Human maintainer |
| `/.github/PULL_REQUEST_TEMPLATE.md` | PR template | Human maintainer |

## Archived References

The following archived files are historical or deep-reference material, not
active routine-maintenance prerequisites:

- `/workflow/archive/LIFECYCLE.md`
- `/workflow/archive/PLAYBOOK.md`
- `/workflow/archive/FILE_CONTRACTS.md`
- `/workflow/archive/BOUNDARIES.md`
- `/workflow/archive/FAILURE_ROUTING.md`
- `/workflow/archive/LINT_CONTRACT.md`
- `/workflow/archive/LINT_REPORT.md`
- `/workflow/archive/CONCURRENCY.md`
- `/workflow/archive/ORCHESTRATOR.md`
- `/meta-prompts/archive/`
- `/specs/archive/`
- `/tasks/archive/`

If an adapter, prompt, or task still needs one of these references, it should
link to the archived path explicitly.

## Adapter Files

- `/CLAUDE.md` — Claude adapter; imports `AGENTS.md`
- `/.github/copilot-instructions.md` — Copilot adapter; imports `AGENTS.md`
- `/.codex/config.toml` — Codex configuration
- `/.codex/AGENTS.md` — Codex adapter
- `/.aiignore` — Files excluded from AI agent context

Adapters may add tool-specific mechanics but must not redefine canonical
workflow policy.

## Scripts

- `/scripts/setup-worktree.sh` — Worktree creation, inventory, and cleanup
- `/scripts/clash-check.sh` — Pre-write conflict detection between worktrees
- `/scripts/policy-check.sh` — Policy validation script
- `/scripts/workflow-lint.sh` — Non-destructive workflow artifact linting

## Agent Definition Files

- `/.github/agents/implementer.agent.md` — Implementation specialist
- `/.github/agents/reviewer.agent.md` — Review specialist
- `/.github/agents/planner.agent.md` — Planning specialist

## Issue Templates

- `/.github/ISSUE_TEMPLATE/feature.yml` — Feature request issue template
- `/.github/ISSUE_TEMPLATE/bug.yml` — Bug report issue template
- `/.github/ISSUE_TEMPLATE/agent-task.yml` — Agent task issue template
- `/.github/ISSUE_TEMPLATE/feature.md` — Feature request markdown fallback
- `/.github/ISSUE_TEMPLATE/bug.md` — Bug report markdown fallback

## CI/CD Files

- `/.github/workflows/ci.yml` — Python test/lint/format CI
- `/.github/workflows/copilot-setup-steps.yml` — Environment setup for Copilot Coding Agent
- `/.github/workflows/copilot-agent.yml` — Issue-to-PR automation via Copilot assignment
- `/.github/workflows/claude-review.yml` — Mention-triggered PR review
- `/.github/workflows/autofix.yml` — CI-failure auto-fix loop
- `/.github/workflows/agentic-triage.yml` — Scheduled issue triage
