"""Contract tests for the :ui-ux-audit standalone UI/UX audit workbench prompt.

These read the checked-in ``templates/ui_ux_audit.json`` and guard the trigger,
metadata, and the core behavioral requirements without overfitting exact prose.
The prompt is a standalone bundled note: it operationalizes a self-contained
usability baseline, audits before recommending, and is not an alias of, and does
not chain to, ``:audit``, ``:sanitize``, ``:cliche``, or any other trigger.
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
UXA_PATH = TEMPLATES_DIR / "ui_ux_audit.json"

INLINE_MARKER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n"


def _load() -> dict:
    return json.loads(UXA_PATH.read_text(encoding="utf-8"))


def _content() -> str:
    return _load()["content"]


# ── Template identity ────────────────────────────────────────────────────────


def test_ui_ux_audit_exists_and_parses():
    """The canonical bundled file exists and parses as a JSON object."""
    assert UXA_PATH.exists()
    assert isinstance(_load(), dict)


def test_ui_ux_audit_metadata_matches_spec():
    """Metadata exactly matches the approved template identity."""
    data = _load()
    assert data["name"] == "UI/UX Audit Workbench"
    assert data["description"] == (
        "Audit every in-scope screen, flow, and state against a standalone "
        "usability baseline and produce an interactive, prioritized "
        "recommendation workbench."
    )
    assert data["trigger"] == ":ui-ux-audit"
    assert data["category"] == "analysis"
    assert data["stage"] == "experience-audit"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []


def test_ui_ux_audit_filename_is_exact():
    """The bundled file is named ui_ux_audit.json."""
    assert UXA_PATH.name == "ui_ux_audit.json"


def test_ui_ux_audit_ends_with_context_marker():
    """The prompt ends with the standard freeform context marker."""
    assert _content().endswith(INLINE_MARKER)


def test_ui_ux_audit_validates_through_product_path():
    """The template loads and validates with no warnings and no variables."""
    template = Template.from_dict(_load())
    assert validate_template(template) == []
    assert template.variables == []


def test_ui_ux_audit_trigger_is_unique_among_bundled():
    """No other bundled template shares the :ui-ux-audit trigger."""
    owners = [
        path.name
        for path in TEMPLATES_DIR.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("trigger") == ":ui-ux-audit"
    ]
    assert owners == ["ui_ux_audit.json"]


# ── Discovery surfacing ──────────────────────────────────────────────────────


def test_ui_ux_audit_registered_once_in_all_surfaces():
    """The trigger appears once in discovery, the quick help, and the docs list."""
    listed = prompt_note_triggers()
    assert listed.count(":ui-ux-audit") == 1
    help_lines = render_quick_help().splitlines()
    assert any(line.strip().startswith(":ui-ux-audit ") for line in help_lines)
    assert "`:ui-ux-audit`" in render_docs_note_list()


# ── Standalone role and independence ─────────────────────────────────────────


def test_ui_ux_audit_declares_standalone_role():
    """The content opens with the standalone evidence-led audit role."""
    content = _content()
    assert content.startswith(
        "You are ui-ux-audit, a standalone evidence-led UI and UX audit assistant."
    )
    assert "independent" in content
    assert "run another command" in content


def test_ui_ux_audit_does_not_chain_to_adjacent_triggers():
    """The content never invokes or chains to another trigger."""
    content = _content()
    for token in (":audit", ":sanitize", ":cliche", ":research", ":feature", ":verify"):
        assert token not in content, token


def test_ui_ux_audit_disclaims_adjacent_responsibilities():
    """The content states it is not sanitization, prose editing, or redesign."""
    content = _content()
    for phrase in (
        "workspace sanitization",
        "prose humanizer",
        "automatic redesign",
    ):
        assert phrase in content, phrase


# ── Operationalized baseline coverage ────────────────────────────────────────


def test_ui_ux_audit_covers_all_seventeen_principles():
    """All 17 core principles are present with stable P01-P17 identifiers."""
    content = _content()
    for principle in [f"P{n:02d}" for n in range(1, 18)]:
        assert principle in content, principle


def test_ui_ux_audit_preserves_baseline_numeric_heuristics():
    """The P05 and P10 numeric heuristics are preserved as targets."""
    content = _content()
    assert "sub-~400ms" in content
    assert "5-7" in content


def test_ui_ux_audit_covers_all_decision_rules():
    """All six screen-change decision rules are present as DR-01..DR-06."""
    content = _content()
    for rule in [f"DR-0{n}" for n in range(1, 7)]:
        assert rule in content, rule


def test_ui_ux_audit_covers_all_per_screen_checks():
    """All ten per-screen self-check items are present as SC-01..SC-10."""
    content = _content()
    for check in [f"SC-{n:02d}" for n in range(1, 11)]:
        assert check in content, check


def test_ui_ux_audit_covers_all_anti_patterns():
    """All nine anti-patterns are present as AP-01..AP-09."""
    content = _content()
    for anti in [f"AP-0{n}" for n in range(1, 10)]:
        assert anti in content, anti


# ── Audit-before-recommendation ordering ─────────────────────────────────────


def test_ui_ux_audit_audits_before_recommending():
    """The audit sequence is enforced ahead of recommendation derivation."""
    content = _content()
    assert "You must audit before you recommend." in content
    assert content.index("Required audit sequence") < content.index("Deriving recommendations")


# ── Evidence and result models ───────────────────────────────────────────────


def test_ui_ux_audit_defines_evidence_model():
    """The five evidence states are present."""
    content = _content()
    for state in ("Verified", "Supported inference", "Assumption", "Unknown", "Contradictory"):
        assert state in content, state


def test_ui_ux_audit_defines_result_states():
    """The five per-check result states are present."""
    content = _content()
    for state in ("Pass", "Partial", "Fail", "Not applicable", "Not verified"):
        assert state in content, state


# ── Deterministic scoring model ──────────────────────────────────────────────


def test_ui_ux_audit_defines_frequency_and_impact_scales():
    """Both 1-5 scales are present with their labels."""
    content = _content()
    for label in ("Rare", "Occasional", "Recurring", "Common", "Core"):
        assert label in content, label
    for label in ("Cosmetic", "Minor friction", "Material friction", "Critical"):
        assert label in content, label


def test_ui_ux_audit_defines_priority_formula_and_bands():
    """The frequency-times-impact formula and P0-P3 bands are present."""
    content = _content()
    assert "Frequency × Impact" in content
    for band in ("P0", "P1", "P2", "P3", "Evidence needed"):
        assert band in content, band
    for span in ("20-25", "12-19", "6-11", "1-5"):
        assert span in content, span


def test_ui_ux_audit_defines_hard_gates():
    """Hard-gate conditions force P0 regardless of the product."""
    content = _content()
    assert "Hard-gate conditions force P0" in content
    assert "keyboard trap" in content


# ── Recommendation classes and readiness ─────────────────────────────────────


def test_ui_ux_audit_defines_recommendation_classes_and_add_gate():
    """All seven recommendation classes and the Add gate are present."""
    content = _content()
    for cls in ("Preserve", "Slim / remove", "Hide", "Merge", "Rename", "Reorganize", "Add"):
        assert cls in content, cls
    assert "Do not default to adding UI." in content
    assert "sunset" in content
    assert "unmet" in content


def test_ui_ux_audit_defines_readiness_states():
    """The three readiness states are present."""
    content = _content()
    for state in ("Not ready", "Conditionally ready", "Ready for the reviewed scope"):
        assert state in content, state


# ── Inventory and state coverage ─────────────────────────────────────────────


def test_ui_ux_audit_requires_experience_and_state_inventory():
    """The experience inventory and meaningful-state coverage are required."""
    content = _content()
    assert "experience inventory" in content
    assert "stable surface ID" in content
    for state in ("empty", "loading", "destructive-action", "assistive-technology-relevant"):
        assert state in content, state
    assert "Do not mark a state reviewed" in content


# ── Self-contained HTML artifact ─────────────────────────────────────────────


def test_ui_ux_audit_builds_a_self_contained_offline_artifact():
    """The prompt requires one self-contained, offline HTML workbench."""
    content = _content()
    assert "self-contained" in content
    assert "without a server" in content
    assert "file://" in content
    assert "inline" in content


def test_ui_ux_audit_prohibits_external_dependencies():
    """The artifact forbids external libraries, CDNs, and network requests."""
    content = _content()
    assert "Do not use external libraries" in content
    for banned in ("CDNs", "network requests", "build steps"):
        assert banned in content, banned


def test_ui_ux_audit_defines_interaction_requirements():
    """Accessibility, persistence, copy fallback, reset, and print are required."""
    content = _content()
    for req in (
        "aria-live",
        "localStorage",
        "navigator.clipboard.writeText",
        "window.print()",
        "visible focus",
        "responsive",
        "confirmed reset",
        "data-*",
        "fallback",
    ):
        assert req in content, req
    assert "no color-only status" in content


# ── Generated Markdown contract ──────────────────────────────────────────────


def test_ui_ux_audit_defines_markdown_copyback_contract():
    """The generated Markdown response contract is present and non-authorizing."""
    content = _content()
    assert "UI/UX audit response" in content
    for heading in (
        "## Scope and coverage",
        "## Readiness assessment",
        "## Finding decisions",
        "## Accepted recommendations",
        "## Revised recommendations",
        "## Deferred or rejected recommendations",
        "## Evidence requests and unresolved items",
        "## Accepted exceptions",
        "## Implementation direction",
        "## Additional reviewer context",
    ):
        assert heading in content, heading
    assert "No response yet" in content
    assert "does not authorize" in content


# ── Change safety ────────────────────────────────────────────────────────────


def test_ui_ux_audit_is_read_only_by_default():
    """The prompt is audit-first and read-only unless implementation is requested."""
    content = _content()
    assert "read-only by default" in content
    assert "audit-first" in content


def test_ui_ux_audit_implementation_requires_audit_first():
    """Explicit implementation still completes the audit first with narrow changes."""
    content = _content()
    assert "Complete the audit first." in content
    assert "narrow, reversible, project-native changes" in content
