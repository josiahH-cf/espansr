"""Contract tests for the refined :feature feature-handoff prompt.

These freeze the refined ``templates/feature.json`` contract: the established
nine-phase handoff workflow and A–M meta-prompt sections are preserved, and the
refinement adds honest input coverage, an explicit clarification status, a
structural output contract, and manifest-owned process navigation (no trigger
routing inside the prompt body).
"""

import json
from pathlib import Path

from espansr.core.discovery import prompt_note_triggers, render_quick_help
from espansr.core.templates import Template
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
FEATURE_PATH = TEMPLATES_DIR / "feature.json"

INLINE_MARKER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n"


def _load() -> dict:
    return json.loads(FEATURE_PATH.read_text(encoding="utf-8"))


def _content() -> str:
    return _load()["content"]


def _assert_ordered(content: str, anchors: list) -> None:
    pos = -1
    for anchor in anchors:
        idx = content.find(anchor)
        assert idx != -1, f"missing anchor: {anchor}"
        assert idx > pos, f"anchor out of order: {anchor}"
        pos = idx


# ── Identity ─────────────────────────────────────────────────────────────────


def test_feature_identity_and_capability_metadata():
    data = _load()
    assert data["name"] == "Feature"
    assert data["trigger"] == ":feature"
    assert data["capability_id"] == "feature-handoff"
    assert data["next_triggers"] == []
    assert data.get("variables", []) == []
    assert data["produces"] == ["implementation-handoff"]
    for artifact in (
        "rough-intent",
        "goal-contract",
        "evidence-report",
        "gap-review",
        "human-litmus",
    ):
        assert artifact in data["accepts"], artifact


def test_feature_validates_and_ends_with_marker():
    template = Template.from_dict(_load())
    assert validate_template(template) == []
    assert _content().endswith(INLINE_MARKER)


def test_feature_registered_in_discovery():
    assert prompt_note_triggers().count(":feature") == 1
    assert any(line.strip().startswith(":feature ") for line in render_quick_help().splitlines())


# ── Preserved internal workflow ──────────────────────────────────────────────


def test_feature_preserves_nine_phase_sequence():
    _assert_ordered(
        _content(),
        [
            "# Phase 1: Contextualize",
            "# Phase 2: Establish the Core Feature Outcome",
            "# Phase 3: Ground Requirements in Evidence",
            "# Phase 4: Compile the Three Verification Outcomes",
            "# Phase 5: Pin the Preservation Gate",
            "# Phase 6: Establish the Kickoff Inputs",
            "# Phase 7: Adversarial Specification Review",
            "# Phase 8: Pre-Write and Single Approval Round",
            "# Phase 9: Incorporate the Reply and Produce the Delivery",
        ],
    )


def test_feature_preserves_meta_prompt_sections_a_through_m():
    content = _content()
    sections = [
        "### A. Role and Mission",
        "### B. Authority and Source Priority",
        "### C. Core Feature Outcome",
        "### D. Evidence Map and Clean-Start Audit",
        "### E. Three-Outcome Package",
        "### F. Acceptance and Preservation Matrix",
        "### G. Simple Linear Implementation Loop",
        "### H. Localized Feedback",
        "### I. External Completion Predicate and Budget",
        "### J. Verification and Adversarial Review",
        "### K. Mechanical Deliverable Extraction",
        "### L. Scope Traceability",
        "### M. Consolidated Delivery Package",
    ]
    _assert_ordered(content, sections)


def test_feature_preserves_core_strengths():
    content = _content()
    for anchor in (
        "fail-first",
        "accept all recommendations",
        "ALL_GATES_GREEN",
        "BUDGET_EXHAUSTED",
        "BLOCKED",
        "REALITY SUMMARY",
        "preservation",
        "adversarial",
        "kickoff input",
        "self-certif",
        "Human verdict",
        "Model verdict",
        "**If this was built correctly:**",
    ):
        assert anchor in content, anchor


def test_feature_stays_single_approval_round():
    content = _content()
    assert "one consolidated approval round" in content
    assert "single reply" in content


# ── Refinement: honest input coverage ────────────────────────────────────────


def test_feature_approval_packet_headings_in_order():
    _assert_ordered(
        _content(),
        [
            "FEATURE SPECIFICATION DECISIONS",
            "CONTEXTUALIZED FEATURE",
            "INPUT COVERAGE",
            "CLARIFICATION STATUS",
            "KICKOFF INPUTS",
            "ARCHITECTURE OUTCOME",
            "BEHAVIOR OUTCOME",
            "HUMAN LITMUS",
            "PRESERVATION SET",
            "DECISIONS AND RECOMMENDATIONS",
            "REALITY SUMMARY",
            "REPLY FORMAT",
        ],
    )


def test_feature_input_coverage_classifies_every_upstream_artifact():
    content = _content()
    for row in (
        "Goal contract",
        "Project evidence",
        "External research",
        "Independent gap review",
        "Human litmus",
        "Human-approved acceptance tests",
        "Preservation set",
        "Project-native feature process",
        "Material unresolved decisions",
    ):
        assert row in content, row


def test_feature_never_implies_unperformed_processes():
    content = _content()
    assert "occurred when it did not" in content


def test_feature_accepts_upstream_artifacts_without_requiring_them():
    content = _content()
    for phrase in ("goal contract", "research report", "gap review", "human-litmus"):
        assert phrase in content.lower(), phrase
    assert "must never require the user to run" in content or (
        "does not require" in content.lower()
    )


# ── Refinement: clarification status ─────────────────────────────────────────


def test_feature_requires_exactly_one_clarification_status():
    content = _content()
    assert "CLARIFICATION STATUS" in content
    assert "REQUIRED" in content
    assert "NOT REQUIRED" in content
    assert "exactly one" in content.lower()


def test_feature_clarification_required_contract():
    content = _content()
    # When REQUIRED: stable IDs, why answers differ, recommendation, safe default.
    assert "stable" in content.lower()
    assert "No safe default" in content
    assert "Recommendation:" in content


def test_feature_clarification_not_required_needs_evidence_basis():
    content = _content()
    assert "evidence-based" in content.lower() or "evidence-backed" in content.lower()


# ── Refinement: process navigation stays outside the prompt ──────────────────


def test_feature_does_not_route_to_other_triggers():
    content = _content()
    for token in (":goal", ":research", ":gaps", ":litmus", ":verify", ":feedback", ":context"):
        assert token not in content, token
    assert "Do not require, invoke, reference, or direct the user to another prompt" in content


# ── Refinement: output contract ──────────────────────────────────────────────


def test_feature_declares_structural_output_contract():
    data = _load()
    contract = data.get("output_contract")
    assert isinstance(contract, dict) and contract
    required = contract.get("required_sections", [])
    for section in (
        "INPUT COVERAGE",
        "CLARIFICATION STATUS",
        "ARCHITECTURE OUTCOME",
        "BEHAVIOR OUTCOME",
        "HUMAN LITMUS",
        "PRESERVATION SET",
        "KICKOFF INPUTS",
        "DECISIONS AND RECOMMENDATIONS",
        "FINAL IMPLEMENTATION META-PROMPT",
        "REALITY SUMMARY",
    ):
        assert section in required, section


def test_feature_final_delivery_names_the_meta_prompt():
    content = _content()
    assert "FINAL IMPLEMENTATION META-PROMPT" in content
