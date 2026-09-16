"""Contract tests for the standalone :litmus criteria-author prompt.

These read the checked-in ``templates/litmus.json`` and guard its identity,
metadata, discovery surfacing, and core behavioral requirements without
overfitting exact prose. ``:litmus`` is an independent bundled note with the
stable capability ID ``human-litmus``: it consolidates the agreed requirements
for supplied material into self-contained, deterministic Yes/No criteria another
model can evaluate without the originating conversation. It authors the criteria
only — it never implements the work, runs tests, answers the statements, chains
to another trigger, or declares an output contract.
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
    assert data["name"] == "Litmus"
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


def test_litmus_declares_yes_no_criteria_role():
    content = _content()
    assert content.startswith(
        "You are `litmus`, a context-grounded author of deterministic Yes/No criteria."
    )


def test_litmus_requires_flat_bullet_statements():
    content = _content()
    assert "Return only flat `- ` bulleted statements." in content


def test_litmus_forbids_answers_verdicts_and_retired_format():
    content = _content()
    assert (
        "Do not supply Yes/No answers, verdicts, scores, checkboxes, answer fields, "
        "or placeholders." in content
    )
    for token in (
        "HUMAN LITMUS",
        "If this was built correctly:",
        "Model verdict:",
        "Human verdict:",
    ):
        assert token not in content, token


def test_litmus_requires_self_contained_bullets():
    content = _content()
    assert "Make every bullet self-contained." in content


def test_litmus_applies_across_artifact_types():
    content = _content()
    assert (
        "The work may be an implementation, article, research output, specification, "
        "prompt, process, or another artifact" in content
    )
    assert "Do not assume the subject is software" in content


def test_litmus_consolidates_supplied_checklists():
    content = _content()
    assert (
        "If an existing checklist is supplied, consolidate it against the controlling "
        "requirements and return only the resulting statements." in content
    )


def test_litmus_grounds_criteria_in_available_context():
    content = _content()
    assert (
        "Inspect relevant available material only as needed to establish the criteria." in content
    )


def test_litmus_authors_criteria_without_implementing_or_evaluating():
    content = _content()
    assert (
        "Author the criteria only. Do not perform the underlying work, run tests, "
        "assess the result, or answer the statements." in content
    )
    assert (
        "Do not implement changes, run tests, assess the work, or claim that any "
        "criterion has been met." in content
    )


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


def test_litmus_declares_no_output_contract():
    data = _load()
    assert "output_contract" not in data
