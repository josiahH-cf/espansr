"""Contract tests for the standalone :litmus human-verification prompt.

These read the checked-in ``templates/litmus.json`` and guard its identity,
metadata, discovery surfacing, and core behavioral requirements without
overfitting exact prose. ``:litmus`` is an independent bundled note with the
stable capability ID ``human-litmus``: it creates, audits, or revises one
consolidated plain-language human-verification checklist for supplied
material. It never implements the feature, never claims the feature is
verified, never chains to another trigger, and leaves human verdicts blank.
"""

import json
from pathlib import Path

from espansr.core.discovery import (
    prompt_note_triggers,
    render_docs_note_list,
    render_quick_help,
)
from espansr.core.templates import Template
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
LITMUS_PATH = TEMPLATES_DIR / "litmus.json"

INLINE_MARKER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n"


def _load() -> dict:
    return json.loads(LITMUS_PATH.read_text(encoding="utf-8"))


def _content() -> str:
    return _load()["content"]


# ── Template identity ────────────────────────────────────────────────────────


def test_litmus_exists_and_parses():
    assert LITMUS_PATH.exists()
    assert isinstance(_load(), dict)


def test_litmus_metadata_matches_spec():
    data = _load()
    assert data["name"] == "Human Litmus"
    assert data["trigger"] == ":litmus"
    assert data["capability_id"] == "human-litmus"
    assert data["category"] == "review"
    assert data["stage"] == "human-litmus"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []
    assert data["produces"] == ["human-litmus"]
    # It accepts the full range of upstream material named by the contract.
    for artifact in (
        "rough-intent",
        "goal-contract",
        "evidence-report",
        "gap-review",
        "implementation-handoff",
        "human-litmus",
    ):
        assert artifact in data["accepts"], artifact


def test_litmus_filename_is_exact():
    assert LITMUS_PATH.name == "litmus.json"


def test_litmus_ends_with_context_marker():
    assert _content().endswith(INLINE_MARKER)


def test_litmus_validates_through_product_path():
    template = Template.from_dict(_load())
    assert validate_template(template) == []
    assert template.variables == []


def test_litmus_trigger_is_unique_among_bundled():
    owners = [
        path.name
        for path in TEMPLATES_DIR.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("trigger") == ":litmus"
    ]
    assert owners == ["litmus.json"]


# ── Discovery surfacing ──────────────────────────────────────────────────────


def test_litmus_registered_once_in_all_surfaces():
    listed = prompt_note_triggers()
    assert listed.count(":litmus") == 1
    help_lines = render_quick_help().splitlines()
    assert any(line.strip().startswith(":litmus ") for line in help_lines)
    assert "`:litmus`" in render_docs_note_list()


# ── Standalone role and behavior ─────────────────────────────────────────────


def test_litmus_declares_standalone_checklist_role():
    content = _content()
    assert content.startswith("You are `litmus`, a standalone human-verification contract author.")


def test_litmus_defines_the_canonical_entry_shape():
    content = _content()
    assert "**If this was built correctly:**" in content
    assert "Model verdict: PASS | FAIL - why:" in content
    assert "Human verdict: PASS | FAIL - why:" in content


def test_litmus_keeps_human_verdicts_blank():
    content = _content()
    assert "blank" in content.lower()
    assert "left blank" in content.lower()


def test_litmus_entries_stay_plain_language():
    """Entries must avoid internal references a non-technical person can't judge."""
    content = _content()
    for term in ("file", "class", "function", "schema"):
        assert term in content.lower(), f"prompt must forbid {term} references in entries"


def test_litmus_covers_non_visual_and_operator_outcomes():
    content = _content()
    assert "non-visual" in content.lower() or "not visual" in content.lower()
    assert "operator" in content.lower()
    assert "maintainer" in content.lower()
    assert "downstream" in content.lower()


def test_litmus_audits_existing_checklists_for_missing_coverage():
    content = _content()
    assert "audit" in content.lower()
    assert "missing" in content.lower()
    assert "coverage" in content.lower()


def test_litmus_inspects_before_asking():
    content = _content()
    assert "before asking" in content.lower() or "inspect before" in content.lower()


def test_litmus_does_not_implement_or_certify():
    content = _content()
    assert "do not implement" in content.lower()
    assert "verified" in content.lower()


def test_litmus_does_not_chain_to_adjacent_triggers():
    content = _content()
    for token in (
        ":feature",
        ":goal",
        ":research",
        ":gaps",
        ":verify",
        ":feedback",
        ":context",
    ):
        assert token not in content, token


def test_litmus_requires_no_workflow_or_feature_invocation():
    """Directly invocable: no workflow, packet, or predecessor requirement."""
    content = _content()
    assert "workflow" not in content.lower().replace("workflow state", "")
    data = _load()
    assert data["next_triggers"] == []


def test_litmus_declares_output_contract():
    data = _load()
    contract = data.get("output_contract")
    assert isinstance(contract, dict) and contract
    assert "HUMAN LITMUS" in contract.get("required_sections", [])
