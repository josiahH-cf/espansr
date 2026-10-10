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

- `espansr/` application code, UI behavior, styles, and generated `:aopen` / `:coms` / `:sync` behavior
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

## Install and Reinstall

- "Reinstall" means `espansr refresh`, which reruns `install.ps1` on Windows or `install.sh` on Linux, macOS, and WSL2. `espansr sync` pulls, commits and pushes local changes, and then reinstalls. `espansr publish` only re-syncs templates to Espanso and is not a reinstall.
- When asked to reinstall, run `espansr refresh`, never a lighter step, and name the exact command you ran in your report.
- After any step that restarts Espanso, run `espansr doctor` and confirm it reports `Espanso process: running independently`. A Windows daemon left inside the calling program's process group stops, with every trigger, when that program closes.

## Template Delivery Loop

Running `:template-builder`, or any request to add or change a prompt note, follows one repeatable loop in this repository, whichever model or client runs it:

1. **Ask.** When no change is named yet, ask what to change and wait.
2. **Clarify.** Inspect the current notes, the git state, and any existing command or note that already covers the idea. Then ask one consolidated batch of questions with a recommended answer for each. Answers may be dictated, partial, or out of order.
3. **Go.** "Go", "do it", or "approve" authorizes everything below without further questions or approval rounds. "Draft only" or "plan only" stops at that stage.
4. **Implement.** Write the template JSON, register it in `espansr/core/discovery.py`, run `python scripts/sync_discovery.py`, add a command group and cue when one fits, and add a docs paragraph, an Unreleased `CHANGELOG.md` entry, and a contract test.
5. **Deliver with one command**, never step by step:

   ```bash
   python scripts/deliver.py --branch agent/<type>-<short-name> --message-file <message.txt> --path <file> [--path <file> ...]
   ```

   List every file you changed. The script commits only those paths, runs `pytest`, `ruff`, `black`, and the discovery check in a clean worktree with the repository's `.venv`, pushes, opens a pull request, waits for CI, squash-merges as `<subject> (#N)`, reinstalls with `espansr refresh`, and verifies with `espansr doctor` and installed-copy parity. End the commit message with your client's attribution lines.
6. **Recover.** When it stops, it prints the stage and exit code (2 preflight, 3 local checks, 4 push or pull request, 5 CI, 6 merge, 7 reinstall, 8 verification). Fix the cause and rerun the same command; it resumes on the branch. After two failed attempts at the same stage, report the blocker with the output.
7. **Report and continue.** Say briefly what changed, then give the pull request, the merge commit, the exact commands, the delivery summary's evidence, and anything unverified. Then ask for the next change.

House rules for this loop:

- Present plans and review findings as numbered items; the user approves by number, for example "approve: 1, 4".
- This repository is public. Personal notes keep their structure and standing rules but never actual values such as amounts, account digits, dates, or private names.
- Other sessions may edit this checkout. Never revert, stash, or commit changes you did not make; the path list keeps them out of your delivery.
- Use prompts the user supplies verbatim, and flag stale passages instead of editing them.
- Before building a new note, check whether an existing command or note already covers the idea.
- `main` requires the five CI checks (`ci (3.11)`, `ci (3.12)`, `ci (3.13)`, `ci-windows`, `ci-macos`) before a pull request merges; never merge with `--admin` or otherwise bypass them.

Running the loop unattended:

- `gh` must be authenticated with push access to the repository.
- Claude Code: `.claude/settings.json` allows the commands the loop needs; see `CLAUDE.md` for its delivery rules.
- Codex: delivery writes outside the repository (the installed templates and the Espanso configuration) and needs the network, so run it with full access and no approval prompts, for example `codex -s danger-full-access -a never`.

## Branches

Use short descriptive branches when needed, such as `agent/type-short-description` or `user/type-short-description`, where `type` is usually `feat`, `bug`, `refactor`, `chore`, or `docs`.
