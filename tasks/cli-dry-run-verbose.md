# Tasks: CLI Dry-Run and Verbose Modes

**Spec:** /specs/cli-dry-run-verbose.md

## Status

- Total: 3
- Complete: 3
- Remaining: 0

## Task List

### Task 1: Write failing tests

- **Files:** `tests/test_dry_run.py`
- **Done when:** All tests exist and fail because the flags/logic are not yet implemented
- **Criteria covered:** AC-1, AC-2, AC-3, AC-4, AC-5
- **Status:** [x] Complete

#### Tests to write

1. `test_sync_dry_run_no_file_written` — `espansr sync --dry-run` prints planned YAML writes but does not create `espansr.yml`
2. `test_sync_dry_run_exit_zero` — `espansr sync --dry-run` returns 0
3. `test_sync_dry_run_lists_files` — output mentions which files would be written/deleted
4. `test_setup_dry_run_no_copy` — `espansr setup --dry-run` does not copy templates or generate launcher
5. `test_setup_dry_run_prints_plan` — output describes what would happen (templates, Espanso, launcher)
6. `test_setup_verbose_per_file` — `espansr setup --verbose` prints one line per template with reason
7. `test_setup_dry_run_verbose_combined` — both flags work together
8. `test_flags_in_help` — `--dry-run` and `--verbose` appear in argparse help for sync and setup

### Task 2: Implement `sync --dry-run`

- **Files:** `espansr/__main__.py`, `espansr/integrations/espanso.py`
- **Done when:** `espansr sync --dry-run` lists planned writes and exits 0 without writing; existing sync behavior unchanged without flag; tests pass
- **Criteria covered:** AC-1, AC-5
- **Status:** [x] Complete

#### Implementation details

1. Add `--dry-run` flag to `sync` subparser in `main()`
2. Pass `dry_run=args.dry_run` to `sync_to_espanso()` in `cmd_sync()`
3. In `sync_to_espanso()`, add `dry_run: bool = False` parameter
4. When `dry_run=True`: build matches as normal, print what would be written, return `True` without writing

### Task 3: Implement `setup --dry-run` and `setup --verbose`

- **Files:** `espansr/__main__.py`
- **Done when:** `espansr setup --dry-run` previews actions without acting; `--verbose` shows per-template detail; both combine; tests pass
- **Criteria covered:** AC-2, AC-3, AC-4, AC-5
- **Status:** [x] Complete

#### Implementation details

1. Add `--dry-run` and `--verbose` flags to `setup` subparser in `main()`
2. In `cmd_setup()`, read `dry_run` and `verbose` from args
3. Dry-run: skip `shutil.copy2`, `clean_stale_espanso_files()`, `generate_launcher_file()` — print what would happen instead
4. Verbose: print per-template decisions ("copied" / "skipped: already exists")

## Test Strategy

| Criterion | Test(s) |
|-----------|---------|
| AC-1: sync --dry-run lists files, exits 0, no writes | `test_sync_dry_run_no_file_written`, `test_sync_dry_run_exit_zero`, `test_sync_dry_run_lists_files` |
| AC-2: setup --dry-run previews without acting | `test_setup_dry_run_no_copy`, `test_setup_dry_run_prints_plan` |
| AC-3: setup --verbose per-file detail | `test_setup_verbose_per_file` |
| AC-4: flags combine | `test_setup_dry_run_verbose_combined` |
| AC-5: flags in help | `test_flags_in_help` |

## Session Log

<!-- Append after each session: date, completed, blockers -->
