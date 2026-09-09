"""Contract tests for the bundled :project-personal-growth session guide.

The note projects the vault's ``Personal Growth - Meta-Prompt.md``: its
``content`` is that note's body (2026-09-02 revision) followed by the standard
freeform context footer. These tests guard the template identity and the rules
the vault's 2026-08-24 ("Personal Growth guide revised") and 2026-08-27
("Bulk-first engagement repair") decisions introduced, without depending on
the vault being mounted in CI.
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
GUIDE_PATH = TEMPLATES_DIR / "project_personal_growth.json"

INLINE_CONTEXT_FOOTER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n"

SECTION_ORDER = (
    "## Context Rules",
    "## Session Start",
    "## Understand Before Method",
    "## Aiding the Work",
    "## Litmus Rules",
    "### Explicit closure dispositions",
    "## Update Rules",
    "## Constraints",
    "## Output Rules",
)


def _load() -> dict:
    return json.loads(GUIDE_PATH.read_text(encoding="utf-8"))


def _content() -> str:
    return _load()["content"]


# ── Template identity ────────────────────────────────────────────────────────


def test_guide_exists_and_parses():
    assert GUIDE_PATH.exists()
    assert isinstance(_load(), dict)


def test_guide_metadata_is_unchanged():
    """Regenerating the body never touches the note's identity or metadata."""
    data = _load()
    assert data["name"] == "Personal Growth Guide"
    assert data["description"] == (
        "Frictionless session guide and record-keeper for the vault's Personal Growth program."
    )
    assert data["trigger"] == ":project-personal-growth"
    assert data["category"] == "workflow"
    assert data["stage"] == "personal-growth-guide"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []
    assert data.get("capability_id", "") == ""


def test_guide_ends_with_context_footer():
    assert _content().endswith(INLINE_CONTEXT_FOOTER)


def test_guide_validates_through_product_path():
    template = Template.from_dict(_load())
    assert validate_template(template) == []
    assert template.variables == []


def test_guide_registered_once_in_all_surfaces():
    listed = prompt_note_triggers()
    assert listed.count(":project-personal-growth") == 1
    help_lines = render_quick_help().splitlines()
    assert any(line.strip().startswith(":project-personal-growth ") for line in help_lines)
    assert "`:project-personal-growth`" in render_docs_note_list()


# ── Guide role and section layout ────────────────────────────────────────────


def test_guide_opens_with_the_working_guide_role():
    assert _content().startswith(
        "You are my working guide for the Personal Growth program in this vault."
    )


def test_guide_sections_appear_in_order():
    content = _content()
    positions = [content.find(heading) for heading in SECTION_ORDER]
    assert all(position >= 0 for position in positions), dict(zip(SECTION_ORDER, positions))
    assert positions == sorted(positions)


def test_guide_does_not_chain_to_other_triggers():
    """The body never routes the reader to another bundled trigger."""
    content = _content()
    for path in TEMPLATES_DIR.glob("*.json"):
        trigger = json.loads(path.read_text(encoding="utf-8")).get("trigger", "")
        if trigger and trigger != ":project-personal-growth":
            assert trigger not in content, trigger


# ── Rules the 2026-08-24 and 2026-08-27 vault decisions introduced ────────────


def test_guide_active_project_rule_follows_the_tracker():
    """The active project is the one the tracker names, not a dependency-order scan."""
    content = _content()
    assert (
        "the project named Active in the tracker's Now section and marked In progress "
        "in its Status Board"
    ) in content
    assert "the first project in dependency order not marked Done" not in content


def test_guide_carries_explicit_closure_dispositions():
    content = _content()
    assert "### Explicit closure dispositions" in content
    assert (
        "keep the original Done When unchecked and unsupported litmus answers unanswered" in content
    )
    assert "or I explicitly choose a logged closure disposition" in content
    assert (
        "An explicit closure disposition changes sequencing state without changing "
        "either record's evidence state."
    ) in content
    assert "never mistake that disposition for passed evidence" in content


def test_guide_output_rules_are_batch_first():
    content = _content()
    assert (
        "Be concrete and proportionate. Move in coherent batches rather than serial "
        "one-question turns"
    ) in content
    assert "Keep one coherent work package in view at a time" in content
    assert "One thing at a time." not in content
    assert "Be brief and concrete." not in content
