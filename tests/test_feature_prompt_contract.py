"""Contract tests for the adaptive :feature authoring prompt.

Guard authoring, grounding, clarification, and native delivery without freezing
a universal runner or verification grammar.
"""

import json
from pathlib import Path

from espansr.core.discovery import prompt_note_triggers, render_quick_help
from espansr.core.templates import Template
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
FEATURE_PATH = ROOT / "templates" / "feature.json"
INLINE_MARKER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n"


def _load() -> dict:
    return json.loads(FEATURE_PATH.read_text(encoding="utf-8"))


def _content() -> str:
    return _load()["content"]


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
        assert artifact in data["accepts"]


def test_feature_validates_and_ends_with_marker():
    template = Template.from_dict(_load())
    assert validate_template(template) == []
    assert _content().endswith(INLINE_MARKER)


def test_feature_registered_in_discovery():
    assert prompt_note_triggers().count(":feature") == 1
    assert any(line.strip().startswith(":feature ") for line in render_quick_help().splitlines())


def test_feature_authors_without_implementing_or_starting_execution():
    content = _content()
    assert "Do not implement the requested feature." in content
    assert "Do not start an agent loop, deploy, or ship it" in content
    assert "Do not defer ready authoring work to another command" in content


def test_feature_uses_verified_native_mechanism_by_default():
    content = _content()
    assert "Use the verified project-native flow by default" in content
    assert "historical example, unused folder, or mentioned loop" in content
    assert "file locations, schema, readiness rules, and required registration" in content


def test_feature_respects_format_override_and_standalone_fallback():
    content = _content()
    assert "console-only delivery, or another format overrides this packaging default" in content
    assert "When no native mechanism exists, return one self-contained" in content
    assert "Do not scaffold a spec runner, create a state file" in content


def test_feature_inspects_implementation_and_shared_consumers():
    content = _content()
    assert "actual implementation and relevant consumers" in content
    assert "Preserve valid existing behavior, unrelated work, and shared consumers." in content


def test_feature_preserves_scope_and_evidence_honesty():
    content = _content()
    assert "do not silently narrow it to the easiest portion" in content
    assert "occurred when it did not" in content
    assert "current behavior, desired behavior, supported inference" in content


def test_feature_upstream_artifacts_are_optional():
    content = _content()
    for artifact in ("goal contract", "research report", "gap review", "human-litmus"):
        assert artifact in content
    assert "none is a compulsory upstream artifact" in content


def test_feature_clarifies_in_console_without_review_artifacts():
    content = _content()
    assert "Print clarification and review directly in the console or ordinary chat." in content
    assert "Do not create a separate review file" in content
    assert "do not use a question tool" in content


def test_feature_clarification_repeats_until_materially_unblocked():
    content = _content()
    assert "There is no fixed question count, turn count, or approval-round limit." in content
    assert "Ask follow-ups on unresolved or newly exposed material issues" in content
    assert "Accept partial, out-of-order, dictated, or natural answers" in content
    assert "speech-to-text mistakes" in content


def test_feature_ready_context_writes_without_ceremonial_approval():
    content = _content()
    assert "write the final handoff immediately" in content
    assert "proceed once unblocked without a ceremonial approval round" in content
    assert "Authorization persists across turns" in content
    assert "any genuine native approval requirement" in content


def test_feature_distinguishes_blocking_and_nonblocking_unknowns():
    content = _content()
    assert "Nonblocking unknowns may remain" in content
    assert (
        "Do not present an essential unresolved product decision as implementation-ready."
        in content
    )


def test_feature_acceptance_and_verification_fit_the_change():
    content = _content()
    assert "observable acceptance criteria" in content
    assert "verification proportional to the actual change and its risks" in content
    assert "Required project checks remain required." in content
    assert "Do not weaken a requirement or a meaningful existing check" in content
    assert "Never prefill human acceptance" in content


def test_feature_does_not_require_universal_runner_grammar():
    content = _content()
    assert "Do not force every feature into three verification outcomes" in content
    assert "Do not invent numeric budgets, metrics, or tests" in content
    assert "output_contract" not in _load()
    for retired in ("ALL_GATES_GREEN", "BUDGET_EXHAUSTED", "# Phase 8:", "### M."):
        assert retired not in content


def test_feature_adversarial_review_checks_intent_and_scope():
    content = _content()
    assert "adversarial specification review" in content
    assert "satisfy the words while missing the purpose" in content
    assert "leave an essential decision unresolved" in content


def test_feature_delivery_is_ready_and_truthful():
    content = _content()
    assert "create or revise the final native specifications" in content
    assert "complete copy-ready content and the exact limitation" in content
    assert "Describe future implementation conditionally" in content
    assert "do not claim the target feature exists because its handoff is complete" in content


def test_feature_does_not_route_to_other_triggers():
    content = _content()
    for token in (":goal", ":research", ":gaps", ":litmus", ":verify", ":feedback", ":context"):
        assert token not in content
    assert "Do not require, invoke, reference, or direct the user to another prompt" in content
