"""Structural invariants every bundled prompt note in ``templates/`` must satisfy.

These run over the real checked-in JSON so a new or edited note that would
break Espanso publishing, discovery, output-contract checking, or the shared
input-marker convention fails here rather than on a user's machine.
"""

import json
import re
from pathlib import Path

import pytest

from espansr.core.output_contract import normalize_contract
from espansr.core.templates import Template
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
BUNDLED_PATHS = sorted(TEMPLATES_DIR.glob("*.json"))
BUNDLED_IDS = [path.name for path in BUNDLED_PATHS]

# Every prompt note closes with one of these so the user's pasted material
# lands in a labeled slot.
INPUT_MARKERS = (
    "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.",
    "PROJECT, MEETING SCOPE, OR NOTES BELOW",
    "TRANSCRIPT, NOTES, USER ANSWERS, OR PROJECT CONTEXT BELOW",
    "ADDITIONAL INSTRUCTIONS OR OUTPUT PREFERENCES BELOW",
    "SOURCE, LOCATION, FILE TYPE, OR NOTES BELOW",
    "OPTIONAL CALLOUTS (IGNORE IF EMPTY BULLET):",
)

# Notes with no user-supplied input by design: the quick help, shell
# snippets, and self-contained utilities.
INPUT_MARKER_EXEMPT = frozenset(
    {
        "q_and_a.json",
        "docs_qa.json",
        "speechify.json",
        "project_systems.json",
        "project_decision_helper.json",
        "espansr_help.json",
        "git_yolo_sh.json",
        "git_rebase_sh.json",
        "git_branch_sh.json",
        "git_yolo_ps.json",
        "git_rebase_ps.json",
        "git_branch_ps.json",
        "refresh_espansr_sh.json",
        "refresh_espansr_ps.json",
        "pocket_extract.json",
        "tenable_scans.json",
    }
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _has_input_marker(content: str) -> bool:
    return any(marker in content for marker in INPUT_MARKERS)


@pytest.fixture(scope="module")
def bundled() -> dict:
    """Every bundled note keyed by filename."""
    return {path.name: _load(path) for path in BUNDLED_PATHS}


def test_bundled_directory_is_populated():
    assert BUNDLED_PATHS, f"no bundled notes found under {TEMPLATES_DIR}"


# ── Validation through the product path ──────────────────────────────────────


@pytest.mark.parametrize("path", BUNDLED_PATHS, ids=BUNDLED_IDS)
def test_validate_template_reports_no_errors(path):
    """validate_template() returns no error-severity findings (warnings are allowed)."""
    warnings = validate_template(Template.from_dict(_load(path)))
    errors = [w.message for w in warnings if w.severity == "error"]
    assert errors == []


# ── Identity ─────────────────────────────────────────────────────────────────


def test_triggers_start_with_colon_and_are_unique(bundled):
    owners = {}
    for filename, data in bundled.items():
        trigger = data.get("trigger", "")
        assert trigger.startswith(":"), f"{filename}: trigger {trigger!r} must start with ':'"
        owners.setdefault(trigger, []).append(filename)
    duplicates = {trigger: files for trigger, files in owners.items() if len(files) > 1}
    assert duplicates == {}


def test_names_are_unique(bundled):
    owners = {}
    for filename, data in bundled.items():
        owners.setdefault(data["name"], []).append(filename)
    duplicates = {name: files for name, files in owners.items() if len(files) > 1}
    assert duplicates == {}


def test_replaces_never_names_a_trigger_another_note_owns(bundled):
    """A retired trigger listed in ``replaces`` must not still be live elsewhere."""
    owner_by_trigger = {data["trigger"]: filename for filename, data in bundled.items()}
    for filename, data in bundled.items():
        for replaced in data.get("replaces", []):
            owner = owner_by_trigger.get(replaced)
            assert owner in (
                None,
                filename,
            ), f"{filename} replaces {replaced}, which {owner} currently owns"


# ── Output contracts ─────────────────────────────────────────────────────────


@pytest.mark.parametrize("path", BUNDLED_PATHS, ids=BUNDLED_IDS)
def test_output_contract_markers_are_well_formed(path):
    """Every regex marker compiles and every literal marker/section is a non-empty string."""
    contract = _load(path).get("output_contract") or {}
    if not contract:
        return

    assert normalize_contract(contract) is not None, f"{path.name}: declared contract is unusable"
    for section in contract.get("required_sections", []):
        assert isinstance(section, str) and section.strip(), f"{path.name}: empty section name"
    for key in ("required_markers", "forbidden_markers"):
        for marker in contract.get(key, []):
            pattern = marker.get("pattern")
            assert isinstance(pattern, str) and pattern, f"{path.name}: {key} entry has no pattern"
            if marker.get("regex"):
                re.compile(pattern)  # raises re.error when the pattern is invalid


# ── Input marker convention ──────────────────────────────────────────────────


@pytest.mark.parametrize("path", BUNDLED_PATHS, ids=BUNDLED_IDS)
def test_note_carries_an_input_marker_unless_exempt(path):
    if path.name in INPUT_MARKER_EXEMPT:
        return
    has_marker = _has_input_marker(_load(path)["content"])
    assert has_marker, f"{path.name} has no input marker and is not in INPUT_MARKER_EXEMPT"


def test_input_marker_exemptions_are_current(bundled):
    """Every exemption names a real note that still has no marker."""
    for filename in sorted(INPUT_MARKER_EXEMPT):
        assert filename in bundled, f"{filename} is exempt but no longer bundled"
        assert not _has_input_marker(
            bundled[filename]["content"]
        ), f"{filename} now carries an input marker; drop it from INPUT_MARKER_EXEMPT"
