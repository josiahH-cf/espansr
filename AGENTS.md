# AGENTS

This file is the lightweight agent entrypoint for `espansr`.

## Project

`espansr` is a Python 3.11+ CLI and GUI manager for Espanso text expansion templates. It stores editable templates as JSON, validates them, publishes managed Espanso YAML, and supports optional Git-backed template sync.

## Product Surface

`espansr` exists to manage reusable prompt "notes" (bundled templates) and to
surface them everywhere they can be discovered. The `:coms` popup is generated
from the live templates at runtime; the static `:espansr` quick help and the
`docs/TEMPLATES.md` note list are rendered from a single source,
`espansr/core/discovery.py`. When you add or rename a bundled prompt note, add
its template JSON in `templates/`, register it once in
`espansr/core/discovery.py`, and run `python scripts/sync_discovery.py` to
regenerate the two static surfaces. `tests/test_discovery_sync.py` fails if any
bundled note is not surfaced everywhere, so keeping notes in sync is automatic,
not a special request that needs asking.

Change these areas only when the request calls for it, and keep edits scoped and
behavior-preserving:

- `espansr/` application code, UI behavior, styles, and generated `:aopen` / `:coms` behavior
- `install.ps1`, `install.sh`, WSL/PowerShell install or setup behavior
- `README.md`, packaging metadata, product tests, and docs unrelated to the prompt-note set

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
