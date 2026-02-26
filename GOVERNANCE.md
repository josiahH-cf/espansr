# Governance — Automatr Espanso

## Scope

Espanso text expansion template manager:
- Template CRUD with JSON-based storage
- Template-to-trigger sync (Espanso match file generation)
- YAML config generation for Espanso integration
- CLI and GUI interfaces for template management

## Non-Goals

- LLM integration or prompt optimization (see [automatr-prompt](https://github.com/josiahH-cf/automatr-prompt))
- Cloud LLM APIs (OpenAI, Anthropic, etc.)
- Multi-tenant or multi-user access
- Mobile or web deployment
- PyPI publishing

## Architecture Constraints

- **Framework:** PyQt6 desktop application + CLI
- **Dependencies:** PyYAML for Espanso YAML generation; no `requests`, no llama.cpp
- **Storage:** JSON-only template format; Espanso config directory integration
- **Network:** No network access required

## Deployment Model

Single-user desktop install:
- Recommended: `./install.sh`
- Alternative: `pip install -e .` for development
- No containerization, no cloud infrastructure

## Ownership

- Solo maintainer project
- Cross-agent code review encouraged
- Contributions welcome via pull requests

## Roadmap Structure

- Milestones tracked in `/tasks/`
- Feature specs in `/specs/`
- Architectural decisions in `/decisions/`
- See `AGENTS.md` for conventions on planning, testing, and commits
