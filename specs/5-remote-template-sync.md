# Feature: 5-remote-template-sync

**Feature ID:** 5-remote-template-sync

## Description

Enable git-backed remote synchronization of espansr templates so that a user's template library stays consistent across multiple machines (e.g., home desktop, work laptop, WSL environments). Templates are stored in a user-provided git remote; `pull`/`push` commands transfer changes with per-template selectivity. Auto-pull on startup is the default behavior.

**Constitution mapping:** Core Capability #2 (CLI-first automation), #3 (Safe sync pipeline), #4 (Platform-aware setup)

## Acceptance Criteria

- [x] **AC-1:** Remote configuration lifecycle
  - GIVEN espansr is installed with no remote configured,
  - WHEN the user runs `espansr remote set <git-url>`,
  - THEN the URL is persisted in `config.json → remote.url`, the templates directory is initialized as a git repo (if not already), and the remote is configured.

- [x] **AC-2:** Remote status reporting
  - GIVEN a remote is configured,
  - WHEN the user runs `espansr remote status`,
  - THEN the command prints the remote URL, last pull/push timestamps, and lists any locally modified templates not yet pushed.

- [x] **AC-3:** Remote removal
  - GIVEN a remote is configured,
  - WHEN the user runs `espansr remote remove`,
  - THEN the remote config is cleared from `config.json`, the `.git` directory is removed from the templates directory, and local templates are preserved.

- [x] **AC-4:** Pull all templates from remote
  - GIVEN a remote is configured and the remote repo has templates,
  - WHEN the user runs `espansr pull`,
  - THEN all remote template changes are pulled (rebase strategy), new templates appear locally, and last_pull timestamp is updated.

- [x] **AC-5:** Pull specific templates
  - GIVEN a remote is configured,
  - WHEN the user runs `espansr pull --template <name>` (one or more),
  - THEN only the specified template file(s) are checked out from the remote, leaving other local state unchanged.

- [x] **AC-6:** Push all templates to remote
  - GIVEN a remote is configured and local templates have changes,
  - WHEN the user runs `espansr push`,
  - THEN all changed templates are staged, committed with an auto-generated message, pushed, and last_push timestamp is updated.

- [x] **AC-7:** Push specific templates
  - GIVEN a remote is configured,
  - WHEN the user runs `espansr push --template <name>` (one or more),
  - THEN only the specified template file(s) are staged, committed, and pushed.

- [x] **AC-8:** Push with custom commit message
  - GIVEN a remote is configured,
  - WHEN the user runs `espansr push --message "my note"`,
  - THEN the commit uses the provided message instead of the auto-generated one.

- [x] **AC-9:** Auto-pull on startup
  - GIVEN a remote is configured and `remote.auto_pull` is true (the default),
  - WHEN any espansr command that loads templates is invoked (sync, list, validate, gui, doctor),
  - THEN a pull is attempted silently before the command runs; failures are warned but do not block the command.

- [x] **AC-10:** Conflict detection
  - GIVEN a remote is configured and a pull encounters merge conflicts,
  - WHEN espansr detects the conflict,
  - THEN it reports which template file(s) conflict, does not silently overwrite, and exits with a non-zero code with remediation instructions.

- [x] **AC-11:** Git-not-found guard
  - GIVEN git is not installed on the system,
  - WHEN the user runs any remote/pull/push command,
  - THEN the command fails with a clear message ("git is required for remote sync") and exits non-zero.

- [x] **AC-12:** .gitignore for local-only state
  - GIVEN a remote is configured and the templates dir is git-initialized,
  - WHEN the repo is initialized or first pull/push occurs,
  - THEN a `.gitignore` file is created/maintained in the templates directory excluding `_versions/` and `_meta/`.

## Affected Areas

- `espansr/core/config.py` — new `RemoteConfig` dataclass
- `espansr/core/remote.py` — **new file**: git operations module
- `espansr/__main__.py` — new CLI commands: `remote`, `pull`, `push`
- `espansr/core/templates.py` — auto-pull hook integration point
- `docs/TEMPLATES.md` — remote sync documentation
- `tests/test_remote_sync.py` — **new file**: full test suite

## Constraints

- **Git required:** `git` must be installed and on PATH. No bundled git.
- **Auth via git:** SSH keys or credential helpers. espansr stores no credentials.
- **No force-push:** Push failures due to diverged history require the user to pull first.
- **Platform parity:** Must work on Linux, WSL2, macOS, and Windows (all platforms where git is available).
- **Backward compatible:** Users who never configure a remote see zero behavior change.

## Out of Scope

- GUI sync button (deferred, can be added later)
- Cloud-specific API integration (GitHub API, etc.) — git protocol only
- Automatic conflict resolution / merge strategies beyond rebase
- Branch management in the template repo (always operates on default branch)
- Syncing config.json itself (only templates)

## Dependencies

- `git` CLI on PATH
- Existing `TemplateManager` and `ConfigManager` infrastructure

## Test Planning Intent

**Test approach:** Unit tests with mocked git subprocess calls; integration tests with real temporary git repos.

**Rough test scenarios:**
- [x] `remote set` persists URL and initializes git repo
- [x] `remote status` reports correct state (clean, dirty, no remote)
- [x] `remote remove` clears config and removes `.git`
- [x] `pull` fetches remote changes into templates dir
- [x] `pull --template` selectively checks out specific files
- [x] `push` stages, commits, pushes changed templates
- [x] `push --template` selectively pushes specific files
- [x] `push --message` uses custom commit message
- [x] Auto-pull fires silently before template-loading commands
- [x] Conflict on pull is detected and reported, not silently resolved
- [x] Missing git produces clear error
- [x] `.gitignore` is created with correct exclusions

## Verification Map

| AC | Test File | Test Function | Assertion |
|----|-----------|---------------|-----------|
| AC-1 | tests/test_remote_sync.py | test_remote_set_persists_url | config.json has remote.url after set |
| AC-1 | tests/test_remote_sync.py | test_remote_set_initializes_git | .git exists in templates dir after set |
| AC-2 | tests/test_remote_sync.py | test_remote_status_shows_state | Output includes URL, timestamps, dirty list |
| AC-3 | tests/test_remote_sync.py | test_remote_remove_clears_config | remote.url is empty after remove |
| AC-3 | tests/test_remote_sync.py | test_remote_remove_preserves_templates | Templates still exist after remove |
| AC-4 | tests/test_remote_sync.py | test_pull_fetches_remote_templates | New remote template appears locally |
| AC-5 | tests/test_remote_sync.py | test_pull_selective_template | Only named template updated |
| AC-6 | tests/test_remote_sync.py | test_push_commits_and_pushes | Remote repo has new commit |
| AC-7 | tests/test_remote_sync.py | test_push_selective_template | Only named template in commit |
| AC-8 | tests/test_remote_sync.py | test_push_custom_message | Commit message matches --message arg |
| AC-9 | tests/test_remote_sync.py | test_auto_pull_on_template_load | Pull attempted when listing templates |
| AC-10 | tests/test_remote_sync.py | test_pull_conflict_detected | Non-zero exit and conflict report |
| AC-11 | tests/test_remote_sync.py | test_git_not_found_error | Clear error when git missing |
| AC-12 | tests/test_remote_sync.py | test_gitignore_created | .gitignore excludes _versions/ and _meta/ |

## Contracts

- **Exposes:** `RemoteConfig` dataclass (in `config.py`)
- **Exposes:** `RemoteManager` class (in `remote.py`) with methods: `init_repo()`, `set_remote()`, `remove_remote()`, `pull()`, `pull_templates()`, `push()`, `push_templates()`, `status()`, `ensure_gitignore()`, `auto_pull()`
- **Exposes:** CLI subcommands: `remote set|status|remove`, `pull [--template NAME]`, `push [--template NAME] [--message MSG]`
- **Consumes:** `ConfigManager`, `TemplateManager`, `get_templates_dir()`

## Execution Linkage

Execution planning is authoritative in `/tasks/5-remote-template-sync.md`.
