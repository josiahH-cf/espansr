"""Contract tests for the bundled :project-decision-helper note.

The note embeds a copy of the operator's value model so a decision session can
continue when the vault is unreachable. The vault's ``Values Working System
v1.md`` owns that model: the embedded block is a dated mirror, and the prompt
must say so rather than treating the two as co-equal. These tests guard the
template identity, that ownership statement, and the note's input-marker
exemption, without depending on the vault being mounted in CI.
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
HELPER_PATH = TEMPLATES_DIR / "project_decision_helper.json"

VALUES_NOTE = "goals/projects/personal-growth/MAIN-Plan/Values Working System v1.md"


def _load() -> dict:
    return json.loads(HELPER_PATH.read_text(encoding="utf-8"))


def _content() -> str:
    return _load()["content"]


def _flat() -> str:
    """The body with hard wraps collapsed, so sentences can be matched whole."""
    return " ".join(_content().split())


# ── Template identity ────────────────────────────────────────────────────────


def test_helper_exists_and_parses():
    assert HELPER_PATH.exists()
    assert isinstance(_load(), dict)


def test_helper_metadata_is_unchanged():
    data = _load()
    assert data["name"] == "Aligned Decision Partner"
    assert data["description"] == (
        "Read-only personal decision partner that frames the real choice and aligns it "
        "with your accepted values, responsibilities, and decision-quality standards "
        "while you keep ownership."
    )
    assert data["trigger"] == ":project-decision-helper"
    assert data["category"] == "workflow"
    assert data["stage"] == "aligned-decision"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []


def test_helper_has_no_input_marker():
    """The note stays self-contained: it is exempt from the shared input-marker rule."""
    assert "USER CONTEXT, GOAL, OR NOTES BELOW" not in _content()


def test_helper_validates_through_product_path():
    warnings = validate_template(Template.from_dict(_load()))
    assert [w.message for w in warnings if w.severity == "error"] == []


def test_helper_registered_once_in_all_surfaces():
    listed = prompt_note_triggers()
    assert listed.count(":project-decision-helper") == 1
    help_lines = render_quick_help().splitlines()
    assert any(line.strip().startswith(":project-decision-helper ") for line in help_lines)
    assert "`:project-decision-helper`" in render_docs_note_list()


# ── Value-model ownership ────────────────────────────────────────────────────


def test_helper_lists_the_vault_values_note_as_a_standing_reference():
    assert VALUES_NOTE in _content()


def test_helper_declares_the_vault_note_authoritative_and_dates_the_mirror():
    """The vault file wins when reachable; the embedded copy is a dated mirror."""
    flat = _flat()
    assert "When `Values Working System v1.md` is accessible it is authoritative" in flat
    assert "the embedded baseline below mirrors it as of 2026-09-02" in flat
    assert "used only when the Vault is unavailable" in flat
    assert "state that limitation once" in flat


def test_helper_no_longer_treats_the_copy_as_co_equal():
    assert (
        "If the local sources are unavailable, continue from the embedded baseline" not in _flat()
    )


def test_helper_keeps_the_embedded_baseline_for_offline_use():
    assert "MY ACCEPTED VALUE MODEL" in _content()
