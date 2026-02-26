# Roadmap — Automatr Espanso v1.0

## Backlog

> Each item below requires scoping (`/specs/`) before implementation begins.
> See the Feature Lifecycle in `/AGENTS.md`.

### CI Hardening
- Add ruff lint step to CI
- Pin dependency versions in pyproject.toml
- Add Python 3.13 to test matrix when available

### Lint Cleanup
- Run ruff check and fix all warnings
- Enforce consistent code style with black

### Espanso Config Validation
- Validate generated YAML against Espanso schema
- Warn on unsupported trigger patterns
- Surface config errors in the UI

### Template Import
- Import template JSON files from external sources
- Strip fields not applicable to Espanso
- Map template variables to Espanso trigger variables

### First Public Release (v1.0)
- README polish with screenshots and usage guide
- License file
- Tag v1.0.0 release on GitHub

## Active

_No active work — ready for v1.0 planning._

## Completed

### v0.1.0 — Initial Standalone Build
- Template CRUD with JSON storage
- Espanso YAML generation
- CLI and GUI interfaces
- 14 tests passing
- CI/CD with GitHub Actions (Python 3.11–3.12)
- Governance docs (AGENTS.md)
