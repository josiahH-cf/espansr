# Project

- Project name: Automatr Espanso
- Description: A standalone Espanso text expansion template manager with CLI and GUI.
- Primary language/framework: Python with PyQt6
- Scope: Espanso config management, template-to-trigger sync, YAML generation
- Non-goals: cloud APIs, multi-tenant, mobile/web, PyPI publishing

# Build

- Install: `./install.sh` (recommended) or `pip install -e .` / `pip install -e .[dev]` for development
- Build: `not applicable` (setuptools package, no separate build step required for local development)
- Test (all): `pytest`
- Test (single): `pytest path/to/test_file.py::test_name`
- Lint: `ruff check .`
- Format: `black .`
- Type-check: `not applicable`

# Architecture

- `automatr_espanso/`: Main Python package and app entrypoint.
- `automatr_espanso/core/`: Core configuration and template handling.
- `automatr_espanso/integrations/`: Espanso sync integration.
- `automatr_espanso/ui/`: PyQt6 user interface screens.
- `templates/`: Bundled Espanso-specific template JSON files (starts empty; add static snippets here).
- `tests/`: Test suite.

# Feature Lifecycle

1. **Ideate** — Human files a GitHub issue or describes the feature
2. **Scope** — Agent explores the codebase and writes `/specs/[feature-name].md` using the template
3. **Plan** — Agent decomposes the spec into `/tasks/[feature-name].md` (2–5 tasks)
4. **Test** — Agent writes failing tests for each acceptance criterion
5. **Implement** — Agent makes tests pass, one task per session
6. **Review** — A different agent or human reviews the PR

GitHub Issues are the human intake mechanism. Agents read issues but do not create, edit, or close them.
All agent-driven planning happens in local files (`/specs/`, `/tasks/`, `/decisions/`).

# Conventions

- Functions and variables: standard Python `snake_case` (classes use `PascalCase`)
- Files and directories: standard Python module naming with lowercase and `snake_case` where needed
- Prefer explicit error handling over silent failures
- No dead code — remove unused imports, variables, and functions
- Every public function has a doc comment
- No hardcoded secrets, URLs, or environment-specific values

# Core Code Lineage

`config.py` and `templates.py` are adapted from an earlier project and will continue to diverge.
Do not attempt to re-merge or share them with external codebases.
Key design decisions:
- `EspansoConfig` is the primary config dataclass
- Config dir is `automatr-espanso`
- `TemplateManager` has `iter_with_triggers()` method

# Testing

- Write tests before implementation
- Place tests under `/tests/` using `test_*.py` naming
- For UI behavior, use `pytest-qt` and prefer deterministic widget-level tests over timing-dependent flows
- Each acceptance criterion requires at least one test
- Do not modify existing tests to accommodate new code — fix the implementation
- Run the full test suite before committing
- Tests must be deterministic — no flaky tests in the main suite

# Dependencies

- PyYAML: required for Espanso YAML file generation
- PyQt6: required for GUI
- No `requests` dependency

# Planning

- Features with more than 3 implementation steps require a written plan
- Plans go in `/tasks/[feature-name].md` or as an ExecPlan per `/.codex/PLANS.md`
- Plans are living documents — update progress, decisions, and surprises as work proceeds
- A plan that cannot fit in 5 tasks indicates the feature should be split. Call this out.
- Small-fix fast path: if a change is <= 3 files and has no behavior change, a full spec/task lifecycle is optional; still document intent in the PR and run lint + relevant tests.

# Commits

- One logical change per commit
- Present-tense imperative subject line, under 72 characters
- Reference the spec or task file in the commit body when applicable
- Commit after each completed task, not after all tasks

# Branches

- Branch from the latest target branch immediately before starting work
- One feature per branch
- Delete after merge
- Never commit directly to the target branch
- Naming: `[type]/[slug]` (e.g., `feat/user-auth`, `fix/null-check`). Include the issue number if one exists: `feat/42-user-auth`

# Worktrees

- Use git worktrees for concurrent features across agents
- Worktree root: `.trees/[branch-name]/`
- Each worktree is isolated: agents operate only within their assigned worktree
- Artifacts (specs, tasks, decisions) live in the main worktree and are shared read-only
- Never switch branches inside a worktree — create a new one

# Pull Requests

- Link to the spec file
- Diff under 300 lines; if larger, split the feature
- All CI checks pass before requesting review
- PR description states: what changed, why, how to verify

# Review

- Reviewable in under 15 minutes
- Tests cover every acceptance criterion
- No unrelated changes in the diff
- Cross-agent review encouraged: use a different model than the one that wrote the code

# Security

- No secrets in code or instruction files
- Use environment variables for all credentials
- Sanitize all external input
- Log security-relevant events

# Agent Boundaries

- Agents do not create or modify GitHub issues, labels, milestones, or projects
- Agents do not push to main/master directly
- Agents do not modify CI/CD workflows without explicit human instruction
- Agents work within local files: specs, tasks, decisions, and source code
