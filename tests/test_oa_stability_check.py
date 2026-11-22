"""The OA check stays callable, bounded and honest about actual execution."""

import json
from pathlib import Path

import pytest

from espansr.core.command_catalog import build_command_catalog
from espansr.core.command_groups import command_cue, groups_for
from espansr.core.config import Config
from espansr.core.discovery import prompt_note_triggers, render_docs_note_list, render_quick_help
from espansr.core.templates import Template, TemplateManager
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def note():
    return json.loads((ROOT / "templates/oa_stability_check.json").read_text(encoding="utf-8"))


def test_oa_check_renders_without_new_access_or_execution_metadata(note):
    assert note["name"] == "OA Stability Check"
    assert note["trigger"] == ":oa-stability-check"
    assert note["category"] == "review"
    assert note["stage"] == "verification"
    assert note["next_triggers"] == note["replaces"] == []
    assert not note.get("execution")
    template = Template.from_dict(note)
    assert validate_template(template) == []
    assert template.render({}) == note["content"]
    assert note["content"].endswith("USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n")


def test_oa_check_is_discoverable_once_in_the_real_catalog():
    manager = TemplateManager(templates_dir=ROOT / "templates")
    matches = [
        entry
        for entry in build_command_catalog(manager, Config())
        if entry.trigger == ":oa-stability-check"
    ]
    assert len(matches) == 1
    assert {group.id for group in groups_for(matches[0])} == {"check-work"}
    assert command_cue(matches[0])[0] == "Check OA stability"
    assert prompt_note_triggers().count(":oa-stability-check") == 1
    assert (
        sum(
            line.strip().startswith(":oa-stability-check ")
            for line in render_quick_help().splitlines()
        )
        == 1
    )
    assert render_docs_note_list().count("`:oa-stability-check`") == 1


@pytest.mark.parametrize(
    "obligation",
    [
        "Keep the dirty primary checkout outside the read and write scope.",
        "A prior policy denial stays blocked until its supported owner provides materially new, "
        "relevant evidence.",
        "Honor an explicit user model, effort or speed choice instead of substituting it.",
        "An authenticated read, schema discovery, preview, fixture, accepted dispatch, "
        "completed live model turn and verified external effect are different evidence.",
        "report the unresolved identity rather than silently treating it as OpenClaw.",
        "Reconcile timeouts or lost acknowledgments under the original operation identity",
        "cleanup only for reconciled, exact owned disposable artifacts",
        "Desktop, browser, phone and Voice access need their own evidence",
    ],
)
def test_oa_check_preserves_critical_evidence_and_effect_boundaries(note, obligation):
    assert obligation in note["content"]


def test_oa_check_requires_a_fresh_live_claude_code_canary(note):
    section = note["content"].split("## Required live retained Dot to Claude Code check\n\n")[1]
    section = section.split("\n\n## ", 1)[0]
    for required in (
        "Every stability run requires a fresh, single-turn, no-write canary",
        "Personal WSL Claude Code (`P-L-Claude`)",
        "trusted registered checkout for the exact Project, repository and route",
        "`oa_launch_managed_local` with the fixed `kind: route-check`",
        "only when the fixed interface accepts those controls. Otherwise use the route default.",
        "`oa_launch_status` with `managed=true` under the original operation ID",
        "`oa_result_read` for that outcome",
        "a succeeded original outcome with its checked checkout and a completed native turn",
        "authentication, catalog discovery, fixture results, queued acknowledgments "
        "and earlier turns",
        "blocked or unverified and holds the overall pass",
        "Dispatch once on the bound route",
        "Reconcile uncertainty only under the original operation identity",
    ):
        assert required in section


def test_oa_check_covers_named_tools_without_equating_opencloud_with_openclaw(note):
    content = note["content"]
    assert all(name in content for name in ("Telegram:", "Todoist:", "OpenClaw:"))
    assert "Claude and Codex:" in content
    assert "Dots and applicable ChatGPT Work connections:" in content
    assert "Resolve the user's name OpenCloud against the actual registry" in content
    assert "smallest adequate available model and effort" in content
    assert (
        "fresh observations, cached observations, historical receipts, blocked checks " in content
    )
    assert "and untested checks separately" in content
    assert (
        "subscription, callback receipt, actual Dot processing, an answer and human acceptance"
        in content
    )
