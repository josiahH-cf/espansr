"""Contract tests for the standalone :litmus verification-handoff author.

These read the checked-in ``templates/litmus.json`` and guard its identity,
metadata, discovery surfacing, and core behavioral requirements without
overfitting exact prose. ``:litmus`` is an independent bundled note with the
stable capability ID ``human-litmus``: it authors a small fresh-model brief and
binary human-outcome checks. The receiving model executes scoped verification;
the authoring invocation never implements, runs canaries, or prefills results.
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
        "implemented-feature",
        "verification-report",
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


def test_litmus_declares_fresh_session_handoff_author_role():
    content = _content()
    assert content.startswith(
        "You are `litmus`, a context-grounded author of fresh-session verification handoffs."
    )


def test_litmus_prepends_small_brief_to_flat_binary_checks():
    content = _content()
    assert "very short contextual verification brief followed by tight Yes/No checks" in content
    assert "the short contextual verification brief first, then the unanswered flat `- `" in content
    assert "criteria-only request may omit the brief; otherwise include it automatically" in content
    assert "Keep the brief to a few concise sentences or short paragraphs" in content


def test_litmus_does_not_prefill_results_or_human_acceptance():
    content = _content()
    assert "prefilled Yes/No answers, checkboxes, scores, model or human verdict fields" in content
    assert "Do not infer human acceptance from your own opinion." in content
    for token in (
        "HUMAN LITMUS",
        "If this was built correctly:",
        "Model verdict:",
        "Human verdict:",
    ):
        assert token not in content, token


def test_litmus_carries_scope_and_check_meaning_into_a_fresh_session():
    content = _content()
    assert "Make every check understandable from the generated handoff." in content
    assert "Source pointers may help locate the implementation but cannot replace" in content
    assert "do not assume the receiving model remembers implementing them" in content


def test_litmus_applies_across_artifact_types():
    content = _content()
    assert (
        "The work may be an implementation, dashboard, interface, specification, article, "
        "research output, prompt, process, or another deliverable." in content
    )
    assert "do not assume every outcome is software or a visible screen" in content


def test_litmus_consolidates_supplied_checklists():
    content = _content()
    assert (
        "Consolidate an existing checklist against the controlling requirements, remove "
        "duplicates, and retain distinct obligations." in content
    )


def test_litmus_grounds_criteria_in_available_context():
    content = _content()
    assert "Inspect relevant available material before asking" in content
    assert "Use recent commits, diffs, branch history, and merges" in content
    assert (
        "Do not invent feature IDs, commit hashes, branches, commands, or completion claims."
        in content
    )
    assert "not from whatever the candidate implementation happens to contain" in content


def test_litmus_authors_criteria_without_implementing_or_evaluating():
    content = _content()
    assert (
        "Author the handoff only. Do not implement changes, execute tests or canaries, "
        "evaluate the candidate, answer the checks" in content
    )
    assert (
        "Instructions to execute belong inside the generated prompt and are addressed "
        "to its receiving model." in content
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
    assert (
        "No preceding command, workflow manifest, separate prompt, or permanent tracking system"
        in content
    )
    data = _load()
    assert data["next_triggers"] == []


def test_litmus_declares_no_output_contract():
    data = _load()
    assert "output_contract" not in data


def test_litmus_keeps_checks_binary_but_does_not_fabricate_evidence():
    content = _content()
    assert "Yes meaning the intended outcome is satisfied and No meaning it is not" in content
    assert "one independently assessable criterion per bullet" in content
    assert "Mark a check UNVERIFIED" in content
    assert "not a changed criterion or fabricated binary verdict" in content


def test_litmus_preserves_human_visual_and_behavioral_nuance():
    content = _content()
    assert "including small but consequential nuances" in content
    assert "Do not silently drop a meaningful requirement because it sounds subjective." in content
    assert "inspect the actual rendered screen or produced artifact" in content
    assert (
        "A file existing, a function being written, a button appearing, a test passing" in content
    )


def test_litmus_clarifies_material_ambiguity_without_review_files():
    content = _content()
    assert "without a fixed question or round limit" in content
    assert "stream-of-consciousness speech-to-text replies" in content
    assert (
        "Do not create a separate review file, HTML packet, form, or questionnaire artifact"
        in content
    )
    assert "If enough is already known, draft immediately." in content


def test_litmus_receiver_can_execute_canaries_and_cleans_only_owned_resources():
    content = _content()
    assert "You are authorized to run relevant tests and bounded canaries" in content
    assert "Invoke the real supported implementation" in content
    assert "Remove only data, temporary helpers, outputs, pending work" in content
    assert "including failed attempts after capturing concise evidence" in content
    assert "preserve pre-existing data, shared resources, and real project deliverables" in content


def test_litmus_receiver_repairs_in_scope_and_honors_verify_only():
    content = _content()
    assert "By default, repair observed failures within the agreed feature scope" in content
    assert "Honor an explicit verify-only or no-edit request instead." in content
    assert "Never weaken the criteria, disable checks, hide a failure" in content
    assert (
        "Distinguish initial failures, repairs made, final observations, and remaining blockers."
        in content
    )
