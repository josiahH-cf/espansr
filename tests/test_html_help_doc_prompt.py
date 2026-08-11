"""Contract tests for the :html-help-doc interactive HTML runbook prompt.

These tests read the checked-in ``templates/html_help_doc.json`` and guard the
trigger, metadata, and the core behavioral requirements of the reusable prompt
without overfitting the exact prose. The prompt is a standalone bundled note; it
is not an alias or variation of ``:audit`` and does not depend on it.
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
HHD_PATH = TEMPLATES_DIR / "html_help_doc.json"

INLINE_MARKER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n"


def _load() -> dict:
    return json.loads(HHD_PATH.read_text(encoding="utf-8"))


def _content() -> str:
    return _load()["content"]


# ── Template identity ────────────────────────────────────────────────────────


def test_html_help_doc_exists_and_parses():
    """The canonical bundled file exists and parses as a JSON object."""
    assert HHD_PATH.exists()
    assert isinstance(_load(), dict)


def test_html_help_doc_metadata_matches_spec():
    """Metadata exactly matches the normative template."""
    data = _load()
    assert data["name"] == "HTML Help Document"
    assert data["trigger"] == ":html-help-doc"
    assert data["category"] == "analysis"
    assert data["stage"] == "interactive-help-doc"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []


def test_html_help_doc_ends_with_context_marker():
    """The prompt ends with the standard freeform context marker."""
    assert _content().endswith(INLINE_MARKER)


def test_html_help_doc_validates_through_product_path():
    """The template loads and validates with no warnings and no variables."""
    template = Template.from_dict(_load())
    assert validate_template(template) == []
    assert template.variables == []


# ── Discovery surfacing ──────────────────────────────────────────────────────


def test_html_help_doc_registered_once_in_all_surfaces():
    """The trigger appears once in discovery, the quick help, and the docs list."""
    listed = prompt_note_triggers()
    assert listed.count(":html-help-doc") == 1
    help_lines = render_quick_help().splitlines()
    assert any(line.strip().startswith(":html-help-doc ") for line in help_lines)
    assert "`:html-help-doc`" in render_docs_note_list()


# ── Core behavioral contract (stable anchors, not exact prose) ───────────────


def test_html_help_doc_builds_a_self_contained_offline_artifact():
    """The prompt requires one self-contained, offline, local HTML5 file."""
    content = _content()
    assert "self-contained" in content
    assert "HTML5" in content
    assert "file://" in content
    assert "inline" in content


def test_html_help_doc_defines_step_result_tracking():
    """The prompt centers on stable-ID steps and the full status set."""
    content = _content()
    assert "stable identifier" in content
    for status in ("Not run", "Pass", "Fail", "Blocked", "Skipped / N/A"):
        assert status in content, status


def test_html_help_doc_uses_conservative_overall_result():
    """The overall-result logic exposes every conservative outcome label."""
    content = _content()
    for label in ("FAIL", "BLOCKED", "INCOMPLETE", "PASS WITH EXCEPTIONS", "PASS"):
        assert label in content, label


def test_html_help_doc_protects_secret_values():
    """Secret handling never persists or copies back secret values."""
    content = _content()
    assert "localStorage" in content
    assert "provided, missing, or not applicable" in content
    assert "[REDACTED]" in content


def test_html_help_doc_makes_missing_substitutions_loud():
    """Missing required substitutions produce a loud copy token, not a blank."""
    assert "<FIELD_LABEL_NOT_ENTERED>" in _content()


def test_html_help_doc_generates_model_ready_copy_back():
    """The copy-back response ends with the authoritative-feedback instruction."""
    assert "authoritative execution feedback" in _content()
