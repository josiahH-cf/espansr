# Concurrency Safety

Rules and strategies for running multiple agents on the same codebase simultaneously.

## Core Rule

> If two agents need to modify the same file, the split is wrong.

Redesign the task decomposition until each agent has exclusive file ownership.

## Worktree Isolation

Every agent gets an isolated worktree via `scripts/setup-worktree.sh <agent> <type> <description>`.

- Directory: `.trees/<agent>-<type>-<description>/`
- Branch: `<agent>/<type>-<description>`
- Agent identifier: any label (e.g., `claude`, `copilot`, `codex`, `agent-1`, a user name)
- Max parallel agents: 3 (configurable in this file)
- Inventory: `scripts/setup-worktree.sh --list`
- Cleanup: `scripts/setup-worktree.sh --cleanup`
- Conflict check: `scripts/clash-check.sh`

## Task Decomposition Strategies

### Strategy 1: Vertical Slice (Preferred)

Each agent builds an entire feature slice (route → controller → validation → tests).
- ✅ No file overlap
- ✅ Each agent is self-contained
- ❌ Requires careful interface design up front

### Strategy 2: Interface Contract

Define API contracts and data types FIRST, then agents code against agreed interfaces independently.
- ✅ Enables true parallel work
- ✅ Single source of truth (types/schemas)
- ❌ Requires freeze on interfaces early

### Strategy 3: Dependency-Graph

Group files by import relationships; assign each group to one agent.
- ✅ Respects natural code boundaries
- ❌ Complex for highly interconnected codebases

### Strategy 4: Advisory Strength-Based Routing

Consult the advisory routing hints in `workflow/ROUTING.md` when deciding which agent to assign to a task. Any agent can perform any task, but model strengths may inform the choice:
- Claude tends to excel at complex reasoning, refactoring, bug diagnosis
- Copilot tends to excel at UI work, documentation, boilerplate
- Codex tends to excel at batch operations, migrations, CI/CD

These are suggestions, not constraints.

## Drift Detection

**Agentic drift**: gradual, invisible divergence when parallel agents encode different assumptions in code that merges cleanly but contains contradictory logic.

### Prevention
- Short integration cycles: merge every few hours, not days
- Pre-write conflict check: `scripts/clash-check.sh` before starting work
- Interface contracts: define types/schemas before implementation
- Vertical slices: minimize shared file surface area

### Detection
- Post-merge, run full test suite (catches behavioral conflicts)
- Review merged code for contradictory patterns
- Track which agents modified which files across branches (check `activeClaims` in STATE.json)

## Safety Limits

| Limit | Value | Rationale |
|-------|-------|-----------|
| Max parallel agents | 3 | Integration tax is nonlinear |
| Max worktree age | 24h | Stale worktrees drift |
| Conflict check frequency | Before each commit | Catches overlaps early |
| Integration cycle | Every 4-8 hours | Prevents drift accumulation |

## Runtime Isolation

Worktrees share the host machine. Prevent resource conflicts:

- **Ports**: Allocate unique dev server port per worktree (e.g., base_port + worktree_index)
- **Databases**: Use separate database files per worktree (e.g., `.trees/<name>/dev.db`)
- **Docker**: Use unique container names per worktree
- **Temp files**: Use worktree-specific temp directories

## Automatic Git Workflow

Automatic git completion is conditional. Agents may commit, push, open PRs, and merge only when the user asked for completion and the repository state makes the step safe.

### Branching

- Feature work uses the branch naming rules in `workflow/ROUTING.md`.
- Routine maintenance may use `agent/docs-short-description`, `agent/chore-short-description`, or `agent/feat-short-description` for bundled template additions.
- Direct commits to `main` are only appropriate when the maintainer explicitly requested that mode and branch protections/repository policy allow it.

### Commit Cadence

- Commit only files that belong to the current task/request.
- Do not include unrelated dirty worktree changes.
- Use a conventional, scoped message where practical, for example `docs: clarify maintenance workflow`, `chore: update prompt wording`, or `feat: add :trigger bundled template`.
- If a spec/task exists, reference it. If this is routine maintenance, reference the user request or affected area instead.

### Push, PR, and Merge

Proceed in this order when safe:

1. Push the current branch.
2. Open a PR using `.github/PULL_REQUEST_TEMPLATE.md`.
3. Wait for required local/remote checks when they are available.
4. Merge only if repository permissions and review/branch-protection rules allow it.
5. Delete the branch only after merge succeeds and no local work would be lost.

Stop and report the remaining manual step if credentials are unavailable, the remote rejects the push, CI cannot be
observed, required human review exists, branch protection blocks merge, or unrelated changes are present.

### Merge on Completion

After a merge, update local base branch state and run the relevant verification command from `workflow/COMMANDS.md`
when practical. If post-merge verification cannot run locally, record the reason and rely on remote CI only when its
status is visible.
