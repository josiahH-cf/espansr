# Tasks: CLI Tab Completion

**Spec:** /specs/cli-tab-completion.md

## Status

- Total: 5
- Complete: 5
- Remaining: 0

## Task List

### Task 1: Write failing tests

- **Files:** `tests/test_completions.py`
- **Done when:** All tests exist and fail because the `completions` subcommand and generator module do not yet exist
- **Criteria covered:** AC-1, AC-2, AC-3, AC-4, AC-6
- **Status:** [x] Complete

#### Tests to write

1. `test_completions_bash_prints_script` — `espansr completions bash` prints a bash completion script to stdout
2. `test_completions_zsh_prints_script` — `espansr completions zsh` prints a zsh completion script to stdout
3. `test_bash_script_contains_subcommands` — bash script contains all registered subcommands (sync, status, list, validate, import, setup, doctor, gui, completions)
4. `test_bash_script_contains_top_level_flags` — bash script contains `--version` and `--help`
5. `test_zsh_script_contains_subcommands` — zsh script contains all registered subcommands
6. `test_zsh_script_contains_top_level_flags` — zsh script contains `--version` and `--help`
7. `test_completions_generated_from_parser` — completion output changes when a subparser is dynamically added, proving generation is from argparse not hardcoded
8. `test_completions_in_help` — `completions` appears in top-level `--help` output

### Task 2: Implement completion generators

- **Files:** `espansr/core/completions.py`
- **Done when:** `build_bash_completion(parser)` and `build_zsh_completion(parser)` return valid shell scripts derived from argparse introspection
- **Criteria covered:** AC-1, AC-2, AC-3, AC-4, AC-6
- **Status:** [x] Complete

### Task 3: Wire CLI subcommand

- **Files:** `espansr/__main__.py`
- **Done when:** `espansr completions bash` and `espansr completions zsh` print scripts to stdout and exit 0; all tests pass
- **Criteria covered:** AC-1, AC-2
- **Status:** [x] Complete

### Task 4: Add install.sh hint

- **Files:** `install.sh`
- **Done when:** Installer prints a one-line hint about sourcing completions after setup; does not auto-install
- **Criteria covered:** AC-5
- **Status:** [x] Complete

### Task 5: Full validation and commit

- **Files:** all
- **Done when:** `pytest` passes, `ruff check .` clean, manual spot-check of `espansr completions bash|zsh`
- **Criteria covered:** all
- **Status:** [x] Complete

## Test Strategy

| Criterion | Test(s) |
|-----------|---------|
| AC-1: `espansr completions bash` prints bash script | `test_completions_bash_prints_script` |
| AC-2: `espansr completions zsh` prints zsh script | `test_completions_zsh_prints_script` |
| AC-3: bash script completes subcommand names | `test_bash_script_contains_subcommands` |
| AC-4: bash script completes top-level flags | `test_bash_script_contains_top_level_flags`, `test_zsh_script_contains_top_level_flags` |
| AC-5: install.sh prints sourcing hint | (manual / integration-level) |
| AC-6: generated from argparse, not hardcoded | `test_completions_generated_from_parser` |

## Session Log

### 2026-03-01
- All 5 tasks completed in a single session
- 8 tests in `tests/test_completions.py`, all passing (298 total)
- `espansr/core/completions.py` generates bash/zsh scripts from argparse introspection
- `espansr completions bash|zsh` subcommand wired in `__main__.py`
- `install.sh` prints sourcing hint after install
- Merged to main
