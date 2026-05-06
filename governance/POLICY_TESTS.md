# Policy Tests

Map active policy expectations to validation signals. These checks are intended
to keep the repository coherent without making routine maintenance depend on
archived lifecycle scaffolding.

## Required Checks

| Requirement | Signal | Source |
|---|---|---|
| Stable maintenance path is documented | `AGENTS.md` describes routine template/docs/prompt cleanup without new specs/tasks | `/AGENTS.md` |
| Active workflow files exist | `STATE.json`, `COMMANDS.md`, and `ROUTING.md` are present and linked from `AGENTS.md` | `/workflow/` |
| Continue state is valid | `workflow/STATE.json` parses and points to an existing task file when `currentTaskFile` is set | `/workflow/STATE.json` |
| Build, lint, and test commands are defined | Commands are concrete and match project tooling | `/workflow/COMMANDS.md` |
| Adapter files do not redefine canon | Adapters reference `AGENTS.md` and active workflow docs instead of inventing separate policy | `/CLAUDE.md`, `/.github/copilot-instructions.md` |
| PR includes verification and rollback guidance | PR template checklist covers verification; routine maintenance may use request/check evidence instead of spec/task evidence | `/.github/PULL_REQUEST_TEMPLATE.md` |
| Constitution placeholders resolved | Fail if `[PROJECT-SPECIFIC]` remains in constitution for active work | `/.specify/constitution.md` |
| Archived workflow links are explicit | References to archived lifecycle files use `workflow/archive/...` paths | `/workflow/`, `/governance/`, adapters |
| Workflow lint is non-destructive when available | `scripts/workflow-lint.sh` exists; skip on native Windows per `workflow/COMMANDS.md` | `/scripts/workflow-lint.sh`, `/workflow/COMMANDS.md` |
| Routine maintenance is scoped | Diff only touches requested files and direct counterparts; final/PR evidence names request type and checks | Assistant summary / PR body |

## CI Mapping

- Run language-specific checks from `workflow/COMMANDS.md`.
- Run policy or workflow lint only where its environment is available.
- Treat routine maintenance as valid without new specs/tasks when it stays
  inside the stable-maintenance scope defined in `AGENTS.md`.

## Failure Semantics

- Policy test failure means repository drift, not an optional warning.
- Fix policy references or artifact shape before relying on an affected
  workflow gate.
- Archived lifecycle files are retained as historical references unless the
  maintainer explicitly requests archival deletion or restoration.
