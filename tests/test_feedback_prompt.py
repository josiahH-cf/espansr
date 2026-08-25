"""Contract tests for the standalone :feedback apply-and-verify prompt.

These read the checked-in ``templates/feedback.json`` and guard its identity,
metadata, discovery surfacing, and the core behavioral requirements without
overfitting exact prose. ``:feedback`` is an independent bundled note: one
invocation applies current-cycle feedback to an existing project and verifies
the change. It does not chain to another trigger and does not establish a
persistent feedback log or cross-session memory. The retired ``:feedback-loop``
command stays retired.
"""

import json
from pathlib import Path

from espansr.core.discovery import (
    prompt_note_triggers,
    render_docs_note_list,
    render_quick_help,
)
from espansr.core.templates import _RETIRED_BUNDLED_TEMPLATE_FILES, Template
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
FEEDBACK_PATH = TEMPLATES_DIR / "feedback.json"

INLINE_MARKER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n"


def _load() -> dict:
    return json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))


def _content() -> str:
    return _load()["content"]


# ── Template identity ────────────────────────────────────────────────────────


def test_feedback_exists_and_parses():
    """The canonical bundled file exists and parses as a JSON object."""
    assert FEEDBACK_PATH.exists()
    assert isinstance(_load(), dict)


def test_feedback_metadata_matches_spec():
    """Metadata exactly matches the approved template identity."""
    data = _load()
    assert data["name"] == "Feedback"
    assert data["description"] == (
        "Apply current-cycle feedback and appended directives to the existing "
        "project, then verify the resulting changes."
    )
    assert data["trigger"] == ":feedback"
    assert data["category"] == "workflow"
    assert data["stage"] == "feedback"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []


def test_feedback_filename_is_exact():
    """The bundled file is named feedback.json."""
    assert FEEDBACK_PATH.name == "feedback.json"


def test_feedback_ends_with_context_marker():
    """The prompt ends with the standard freeform context marker."""
    assert _content().endswith(INLINE_MARKER)


def test_feedback_validates_through_product_path():
    """The template loads and validates with no warnings and no variables."""
    template = Template.from_dict(_load())
    assert validate_template(template) == []
    assert template.variables == []


def test_feedback_trigger_is_unique_among_bundled():
    """No other bundled template shares the :feedback trigger."""
    owners = [
        path.name
        for path in TEMPLATES_DIR.glob("*.json")
        if json.loads(path.read_text(encoding="utf-8")).get("trigger") == ":feedback"
    ]
    assert owners == ["feedback.json"]


# ── Discovery surfacing ──────────────────────────────────────────────────────


def test_feedback_registered_once_in_all_surfaces():
    """The trigger appears once in discovery, the quick help, and the docs list."""
    listed = prompt_note_triggers()
    assert listed.count(":feedback") == 1
    help_lines = render_quick_help().splitlines()
    assert any(line.strip().startswith(":feedback ") for line in help_lines)
    assert "`:feedback`" in render_docs_note_list()


# ── Standalone role and behavior ─────────────────────────────────────────────


def test_feedback_declares_standalone_apply_and_verify_role():
    """The content opens with the standalone apply-and-verify role."""
    content = _content()
    assert content.startswith(
        "You are `feedback`, a standalone assistant that applies current-cycle feedback"
    )
    assert "one bounded feedback-application cycle" in content


def test_feedback_describes_apply_then_verify():
    """The prompt directs direct change application followed by verification."""
    content = _content()
    assert "### 3. Apply the changes" in content
    assert "### 4. Verify the result" in content
    assert "When write access exists" in content
    assert "When write access does not exist" in content


def test_feedback_reports_bounded_status_outcomes():
    """The prompt reports one of the bounded completion statuses."""
    content = _content()
    for status in ("applied", "partial", "patch-ready", "blocked"):
        assert status in content, status


def test_feedback_does_not_chain_to_adjacent_triggers():
    """The content never requires or chains to another trigger."""
    content = _content()
    for token in (":feature", ":verify", ":troubleshoot", ":context", ":unblock", ":feedback-loop"):
        assert token not in content, token


def test_feedback_forbids_persistent_feedback_storage():
    """The prompt bars a command-owned log, persistent memory, and a live observer."""
    content = _content()
    assert "log.jsonl" not in content
    assert "What feedback do you have" not in content
    assert "cross-session feedback memory" in content
    assert "persistent feedback-capture" in content


# ── Retirement guardrails ────────────────────────────────────────────────────


def test_feedback_loop_remains_retired():
    """The former :feedback-loop starter stays retired and out of active discovery."""
    assert _RETIRED_BUNDLED_TEMPLATE_FILES["feedback_loop.json"] == ":feedback-loop"
    assert not (TEMPLATES_DIR / "feedback_loop.json").exists()
    assert ":feedback-loop" not in prompt_note_triggers()
