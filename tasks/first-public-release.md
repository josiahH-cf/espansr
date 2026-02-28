# Tasks: first-public-release

**Spec:** /specs/first-public-release.md

## Status

- Total: 4
- Complete: 4
- Remaining: 0

## Task List

### Task 1: Write tests

- **Files:** `tests/test_release.py`
- **Done when:** Tests for version string, `--version` flag, CHANGELOG existence, and README content markers exist and fail
- **Criteria covered:** All acceptance criteria
- **Status:** [x] Complete

### Task 2: Version bump and --version flag

- **Files:** `pyproject.toml`, `espansr/__init__.py`, `espansr/__main__.py`
- **Done when:** Version is `1.0.0` everywhere, `espansr --version` prints correct output
- **Criteria covered:** Criteria 1, 2, 3
- **Status:** [x] Complete

### Task 3: Create CHANGELOG.md

- **Files:** `CHANGELOG.md`
- **Done when:** File exists with entries for all completed features and correct version headings
- **Criteria covered:** Criterion 4
- **Status:** [x] Complete

### Task 4: README polish

- **Files:** `README.md`
- **Done when:** CI badge, platform matrix, and complete development section are present
- **Criteria covered:** Criteria 5, 6, 7
- **Status:** [x] Complete

## Test Strategy

| Criterion | Test |
|-----------|------|
| pyproject.toml version | `test_pyproject_version` |
| __init__.py version | `test_init_version` |
| --version flag | `test_version_flag` |
| CHANGELOG exists | `test_changelog_exists` |
| README CI badge | `test_readme_ci_badge` |
| README platform matrix | `test_readme_platform_matrix` |
| README dev commands | `test_readme_dev_section` |

## Session Log

<!-- Append after each session: date, completed, blockers -->
