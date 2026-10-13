"""Contract and discovery checks for the approved Meeting Actions prompt."""

import hashlib
import json
from pathlib import Path

import pytest

from espansr.core.command_catalog import build_command_catalog
from espansr.core.command_groups import command_cue, groups_for
from espansr.core.config import Config
from espansr.core.discovery import render_docs_note_list, render_quick_help
from espansr.core.output_contract import check_output
from espansr.core.templates import Template, TemplateManager
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "templates" / "meeting_actions.json"
APPROVED_BODY_SHA256 = "958d72c3b35a92fd4acb1d4db4deb1febcbc004a6a24b763fbb32c22ccff0439"


def _load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_meeting_actions_preserves_the_approved_body_and_new_identity():
    data = _load()
    assert data["name"] == "Meeting Actions"
    assert data["trigger"] == ":meeting-actions"
    assert data["category"] == "workflow"
    assert data["stage"] == "meeting-summary"
    assert data["next_triggers"] == data["replaces"] == []
    content = data["content"]
    assert hashlib.sha256(content.rstrip("\n").encode("utf-8")).hexdigest() == APPROVED_BODY_SHA256
    assert content.endswith("TRANSCRIPT, NOTES, USER ANSWERS, OR PROJECT CONTEXT BELOW\n\n")
    template = Template.from_dict(data, PATH)
    assert template.variables == []
    assert template.render({}) == content
    assert validate_template(template) == []


def test_meeting_actions_is_discoverable_with_its_live_content_and_browse_cue():
    manager = TemplateManager(templates_dir=ROOT / "templates")
    entries = [
        entry
        for entry in build_command_catalog(manager, Config())
        if entry.trigger == ":meeting-actions"
    ]
    assert len(entries) == 1
    entry = entries[0]
    assert entry.capability_id == "meeting_actions"
    assert entry.content == _load()["content"]
    assert {group.id for group in groups_for(entry)} == {"explain-communicate"}
    assert command_cue(entry)[0] == "Meeting actions"
    assert ":meeting-actions" in render_quick_help()
    assert "`:meeting-actions`" in render_docs_note_list()


@pytest.mark.parametrize(
    "actions",
    [
        "- Prepare [Confirmed] the draft for Morgan after Riley sends figures, by tomorrow.",
        "No actions are clearly mine.",
    ],
)
def test_synthetic_response_sections_are_compatible_with_the_existing_checker(actions):
    output = (
        "Meeting summary\nThe team reviewed a draft with an open dependency.\n\nMy actions\n"
        + actions
    )
    report = check_output(_load()["output_contract"], output)
    assert report.passed, report.summary()


def test_the_output_checker_reports_a_missing_actions_section():
    report = check_output(
        _load()["output_contract"], "Meeting summary\nA synthetic meeting summary."
    )
    assert not report.passed
    assert [failure.message for failure in report.failures] == [
        "missing required section: My actions"
    ]
