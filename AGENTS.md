# AGENTS

This file is the lightweight agent entrypoint for `espansr`.

## Project

`espansr` is a Python 3.11+ CLI and GUI manager for Espanso text expansion templates. It stores editable templates as JSON, validates them, publishes managed Espanso YAML, and supports optional Git-backed template sync.

## Protected Product Surface

Do not modify these areas unless the user explicitly asks for a product or template change:

- `templates/` bundled templates, including `feat.json` and helper prompts
- `espansr/` application code, UI behavior, styles, and generated `:aopen` / `:coms` behavior
- `install.ps1`, `install.sh`, WSL/PowerShell install or setup behavior
- `README.md`, product docs under `docs/`, packaging metadata, and product tests

## Normal Maintenance Flow

For focused repository maintenance:

1. Inspect the relevant files and the current git state.
2. Keep edits tightly scoped to the user request.
3. Preserve existing product behavior unless the request explicitly changes it.
4. Run the relevant checks: `pytest`, `ruff check .`, and `black --check .`.
5. Report changed files, verification, and any skipped checks.

Routine work in this repository only needs clear scope, focused edits, normal tests, and normal CI.

## Branches

Use short descriptive branches when needed, such as `agent/type-short-description` or `user/type-short-description`, where `type` is usually `feat`, `bug`, `refactor`, `chore`, or `docs`.
