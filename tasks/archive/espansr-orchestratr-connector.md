# Tasks: espansr-orchestratr-connector

**Spec:** /specs/espansr-orchestratr-connector.md

## Status

- Total: 4
- Complete: 4
- Remaining: 0

## Task List

### Task 1: Write failing tests

- **Files:** `tests/test_orchestratr_connector.py`
- **Done when:** All acceptance criteria have at least one failing test
- **Criteria covered:** All 7
- **Status:** [x] Complete

### Task 2: Create orchestratr integration module

- **Files:** `espansr/integrations/orchestratr.py`
- **Done when:** `generate_manifest()` and `get_status_json()` pass their tests
- **Criteria covered:** AC 1 (manifest), AC 3 (status --json), AC 5 (ready_cmd), AC 6 (passive)
- **Status:** [x] Complete

### Task 3: Wire `status --json` into CLI

- **Files:** `espansr/__main__.py`
- **Done when:** `espansr status --json` outputs valid JSON matching spec schema
- **Criteria covered:** AC 2 (launchable), AC 3 (status --json)
- **Status:** [x] Complete

### Task 4: Wire manifest generation into `setup`

- **Files:** `espansr/__main__.py`
- **Done when:** `espansr setup` writes/regenerates `orchestratr.yml` and prints confirmation
- **Criteria covered:** AC 7 (setup regenerates manifest)
- **Status:** [x] Complete

## Test Strategy

| Acceptance Criterion | Test(s) |
|---|---|
| AC 1: manifest in config dir | `test_generate_manifest_writes_yaml`, `test_manifest_content_matches_schema` |
| AC 2: GUI launchable with PID | `test_status_json_reports_pid` (status is the readiness signal) |
| AC 3: status --json | `test_status_json_ok`, `test_status_json_degraded` |
| AC 4: bring-to-front | Out of scope — existing WM behavior, no custom code |
| AC 5: ready_cmd in manifest | `test_manifest_content_matches_schema` |
| AC 6: passive if no orchestratr | `test_generate_manifest_no_side_effects`, `test_status_works_without_orchestratr` |
| AC 7: setup regenerates | `test_setup_generates_manifest`, `test_setup_regenerates_outdated_manifest` |

## Session Log

<!-- Append after each session: date, completed, blockers -->
