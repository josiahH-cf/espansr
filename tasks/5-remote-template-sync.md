# Tasks: 5-remote-template-sync

**Feature ID:** 5-remote-template-sync
**Spec:** /specs/5-remote-template-sync.md

## Status

- Total: 5
- Complete: 4
- Remaining: 1
- Blocked: 0

## Pre-Implementation Tests

| AC | Test File | Status |
|----|-----------|--------|
| AC-1 | tests/test_remote_sync.py::test_remote_set_persists_url | [ ] Not written |
| AC-1 | tests/test_remote_sync.py::test_remote_set_initializes_git | [ ] Not written |
| AC-2 | tests/test_remote_sync.py::test_remote_status_shows_state | [ ] Not written |
| AC-3 | tests/test_remote_sync.py::test_remote_remove_clears_config | [ ] Not written |
| AC-3 | tests/test_remote_sync.py::test_remote_remove_preserves_templates | [ ] Not written |
| AC-4 | tests/test_remote_sync.py::test_pull_fetches_remote_templates | [ ] Not written |
| AC-5 | tests/test_remote_sync.py::test_pull_selective_template | [ ] Not written |
| AC-6 | tests/test_remote_sync.py::test_push_commits_and_pushes | [ ] Not written |
| AC-7 | tests/test_remote_sync.py::test_push_selective_template | [ ] Not written |
| AC-8 | tests/test_remote_sync.py::test_push_custom_message | [ ] Not written |
| AC-9 | tests/test_remote_sync.py::test_auto_pull_on_template_load | [ ] Not written |
| AC-10 | tests/test_remote_sync.py::test_pull_conflict_detected | [ ] Not written |
| AC-11 | tests/test_remote_sync.py::test_git_not_found_error | [ ] Not written |
| AC-12 | tests/test_remote_sync.py::test_gitignore_created | [ ] Not written |

## Task List

### T-1: RemoteConfig dataclass and config wiring

- **Files:** `espansr/core/config.py`
- **Test File:** `tests/test_remote_sync.py` (config-related tests)
- **Done when:** `RemoteConfig` dataclass exists with `url`, `auto_pull` (default True), `last_pull`, `last_push` fields; wired into `Config` and round-trips through `to_dict` / `from_dict`; existing configs without `remote` key still load cleanly (backward compat).
- **Criteria covered:** AC-1 (config persistence), AC-9 (auto_pull default true)
- **Branch:** `copilot/feat-remote-config`
- **Status:** [x] Complete

### T-2: RemoteManager core git operations

- **Files:** `espansr/core/remote.py` (new)
- **Test File:** `tests/test_remote_sync.py` (git operation tests)
- **Done when:** `RemoteManager` class implements: `check_git()` (AC-11), `init_repo()` + `set_remote()` (AC-1), `remove_remote()` (AC-3), `ensure_gitignore()` (AC-12), `status()` (AC-2), `pull()` + `pull_templates()` (AC-4, AC-5, AC-10), `push()` + `push_templates()` (AC-6, AC-7, AC-8), `auto_pull()` (AC-9). All git calls go through subprocess with proper error handling.
- **Criteria covered:** AC-1 through AC-12
- **Branch:** `copilot/feat-remote-manager`
- **Status:** [x] Complete

### T-3: CLI commands for remote, pull, push

- **Files:** `espansr/__main__.py`
- **Test File:** `tests/test_remote_sync.py` (CLI integration tests)
- **Done when:** `espansr remote set <url>`, `espansr remote status`, `espansr remote remove` subcommands exist; `espansr pull [--template NAME ...]` and `espansr push [--template NAME ...] [--message MSG]` top-level commands exist; all wire through to `RemoteManager`. Help text is clear.
- **Criteria covered:** AC-1, AC-2, AC-3, AC-4, AC-5, AC-6, AC-7, AC-8
- **Branch:** `copilot/feat-remote-cli`
- **Status:** [x] Complete

### T-4: Auto-pull integration

- **Files:** `espansr/__main__.py`, `espansr/core/remote.py`
- **Test File:** `tests/test_remote_sync.py::test_auto_pull_on_template_load`
- **Done when:** Commands that load templates (`sync`, `list`, `validate`, `gui`, `doctor`) call `RemoteManager.auto_pull()` before template loading; auto-pull is silent on success, warns on failure, and is skipped when `remote.auto_pull` is false or no remote is configured.
- **Criteria covered:** AC-9
- **Branch:** `copilot/feat-remote-autopull`
- **Status:** [x] Complete

### T-5: Documentation update

- **Files:** `docs/TEMPLATES.md`
- **Test File:** N/A (documentation)
- **Done when:** Remote sync section added to TEMPLATES.md covering: setup (`remote set`), daily workflow (`pull`/`push`), per-template selectivity, auto-pull behavior, conflict handling, auth prerequisites (SSH keys / credential helpers), and `.gitignore` behavior.
- **Criteria covered:** All (documentation)
- **Branch:** `copilot/docs-remote-sync`
- **Status:** [ ] Not started

## Routing Plan

| Task | Suggested Model | Rationale | Reviewer | Parallel? | Context Needs |
|------|-----------------|-----------|----------|-----------|---------------|
| T-1 | Copilot | Small, focused dataclass addition | Claude | Yes (with T-2) | Small — config.py only |
| T-2 | Claude | Core logic with subprocess handling, conflict detection | Copilot | Yes (with T-1) | Medium — new module, references config + templates |
| T-3 | Copilot | CLI wiring follows established argparse patterns | Claude | No — depends on T-1, T-2 | Medium — __main__.py + remote.py |
| T-4 | Copilot | Small integration hook into existing commands | Claude | No — depends on T-2, T-3 | Small — two files, targeted edits |
| T-5 | Copilot | Documentation generation | Claude | Yes (with T-4) | Small — docs only |

## Test Strategy

- AC-1: test_remote_set_persists_url, test_remote_set_initializes_git
- AC-2: test_remote_status_shows_state
- AC-3: test_remote_remove_clears_config, test_remote_remove_preserves_templates
- AC-4: test_pull_fetches_remote_templates
- AC-5: test_pull_selective_template
- AC-6: test_push_commits_and_pushes
- AC-7: test_push_selective_template
- AC-8: test_push_custom_message
- AC-9: test_auto_pull_on_template_load
- AC-10: test_pull_conflict_detected
- AC-11: test_git_not_found_error
- AC-12: test_gitignore_created

## Evidence Log

- 2026-03-28 T-1 through T-4 — commands run: pytest (391 passed), ruff check (clean), result: pass, notes: all 14 AC tests pass

## Session Log

| Date | Last Completed | Next Action | Blockers | State Link |
|------|---------------|-------------|----------|------------|
| 2026-03-28 | Plan created | T-1 (RemoteConfig) + T-2 (RemoteManager) in parallel | None | [workflow/STATE.json](../workflow/STATE.json) |
| 2026-03-28 | T-1 through T-4 complete | Phase 7 test post | None | [workflow/STATE.json](../workflow/STATE.json) |
