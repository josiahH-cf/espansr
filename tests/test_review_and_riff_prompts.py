"""Contracts and product discovery for the six review and reconciliation notes.

These checks qualify reusable instructions and exact rendered prompt delivery;
they do not claim a receiving assistant ran a review or changed another system.
"""

import json
import re
from pathlib import Path

import pytest

from espansr.core.capability_catalog import build_catalog
from espansr.core.command_catalog import build_command_catalog
from espansr.core.command_groups import command_cue, groups_for
from espansr.core.config import Config
from espansr.core.discovery import prompt_note_triggers, render_docs_note_list, render_quick_help
from espansr.core.templates import Template, TemplateManager
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
MARKER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK."
NOTES = (
    ("annotate", ":annotate", "annotation-review", {"explain-communicate"}),
    ("tldr", ":tldr", "item-summary", {"explain-communicate"}),
    (
        "repo_reconcile",
        ":repo-reconcile",
        "repository-reconciliation",
        {"check-work", "tools-setup"},
    ),
    ("dot_morning", ":dot-morning", "dot-morning-review", {"personal-programs"}),
    ("dot_night", ":dot-night", "dot-night-review", {"personal-programs"}),
    ("riff", ":riff", "idea-riff", {"clarify-specs"}),
)


def load(stem):
    return json.loads((ROOT / "templates" / f"{stem}.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def catalogs():
    return (
        build_command_catalog(TemplateManager(templates_dir=ROOT / "templates"), Config()),
        build_catalog(ROOT / "templates"),
    )


@pytest.mark.parametrize("stem,trigger,capability,groups", NOTES)
def test_complete_prompt_reaches_all_discovery_surfaces(
    stem, trigger, capability, groups, catalogs
):
    data = load(stem)
    template = Template.from_dict(data)
    assert data["trigger"] == trigger
    assert data["capability_id"] == capability
    assert data["description"] and data["category"] and data["stage"]
    assert validate_template(template) == []
    assert template.render({}) == data["content"]
    assert template.content.endswith(MARKER + "\n\n")
    assert template.next_triggers == []
    assert not data["replaces"]
    assert prompt_note_triggers().count(trigger) == 1
    assert any(line.strip().startswith(trigger + " ") for line in render_quick_help().splitlines())
    assert f"`{trigger}`" in render_docs_note_list()
    entries, catalog = catalogs
    assert catalog["validation"] == "passed"
    entry = next(e for e in entries if e.trigger == trigger)
    assert {g.id for g in groups_for(entry)} == groups
    assert command_cue(entry)[1]
    descriptor = next(e for e in catalog["entries"] if e["capability_id"] == capability)
    assert descriptor["execution"]["classification"] == "prompt-only"
    assert all(t not in data["content"] for t in prompt_note_triggers() if t != trigger)
    # Both the generated list and the actual explanatory paragraph name each note.
    docs = (ROOT / "docs/TEMPLATES.md").read_text(encoding="utf-8")
    assert docs.count(f"`{trigger}`") >= 2


def assert_instructions(stem, *phrases):
    content = load(stem)["content"]
    assert [phrase for phrase in phrases if phrase not in content] == []


def test_annotation_covers_any_material_and_revises_with_advice():
    assert_instructions(
        "annotate",
        "workflow-agnostic",
        "questions, blockers, specifications, repository findings, a plan",
        "show the substance itself immediately and comprehensively in console/chat",
        "stable identifiers",
        "native methods only when the current app actually supports them",
        "ordinary console replies by number, quoted text or name",
        "partial or out of order",
        "edit the affected material and give your advice in the same pass",
        "Annotation or approval of wording does not by itself authorize",
    )


def test_tldr_preserves_each_item_outcome_and_human_decision():
    assert_instructions(
        "tldr",
        "workflow-agnostic",
        "one simple TLDR for each relevant item",
        "no arbitrary three-bullet rule, fixed item count, or quota",
        "outcome, suggestion, recommendation, update, action, open question, blocker or decision",
        "what to check, answer, choose or approve",
        "explain <number>",
        "Put any approval request together at the end",
        "Preserve prior authorization",
        "imply silence approves anything",
    )


def test_reconciliation_integrates_and_prunes_without_bypassing_ownership_or_ci():
    assert_instructions(
        "repo_reconcile",
        "Global means the whole selected repository",
        "unique commits and equivalent squash-merged changes",
        "both tracked and untracked work, worktree ownership, active sessions",
        "continue clear authorized work",
        "Merge relevant code through the repository's established branch and pull-request process",
        "ask when competing intentions cannot be established",
        "policy permit a justified change",
        "never use an administrative merge bypass",
        "not permission to force-push main",
        "confirmed owned, inactive, clean, obsolete",
        "their unique work is integrated or otherwise preserved",
        "resolved absolute paths remain within",
        "Preserve dirty, active, unique, unknown or third-party work",
        "Age alone proves nothing",
        "obtain any required specific confirmation before acting",
    )


@pytest.mark.parametrize("stem", ["dot_morning", "dot_night"])
def test_dot_reviews_reuse_owners_and_preserve_actual_source_and_effect_state(stem):
    assert_instructions(
        stem,
        "on-demand",
        "Console means the existing Obsidian Agent Console",
        "timezone",
        "business",
        "work calendars",
        "Todoist",
        "unknown, not empty",
        "material questions",
        "approval round",
    )
    content = load(stem)["content"].lower()
    for distinction in ("queued", "running", "delivered", "uncertain", "original", "read-only"):
        assert distinction in content


def test_morning_explicitly_starts_suitable_context_backed_work():
    assert_instructions(
        "dot_morning",
        "current Week context, known answers and original work receipts",
        "one Console calendar feed does not establish complete coverage",
        "Check Console and Todoist stability",
        "physical or human-only tasks, ready AI work and work needing context",
        "This invocation requests the review and suitable context-backed background work",
        "a task title alone is insufficient context",
        "Do not duplicate launches, clear a Stop or invent delegation permission",
        "Start independent ready work while unrelated questions remain open",
        "A queued response does not prove execution",
    )


def test_night_prepares_and_reschedules_without_changing_deadline_or_recurrence_meaning():
    assert_instructions(
        "dot_night",
        "today and tomorrow in the user's local timezone",
        "Read tomorrow's business and work calendars",
        "Perform supported preparation within the invocation's scope",
        "current intent, calendar commitments, dependencies and task context",
        "Preserve every unrelated field",
        "Do not blindly roll all overdue tasks forward",
        "pass a real deadline, end or reinterpret a repetition",
        "existing owning records",
        "If persistence is unavailable, provide the handoff inline",
    )


@pytest.mark.parametrize(
    "stem,instruction",
    [
        ("annotate", "apply unambiguous requested revisions directly"),
        ("tldr", "Produce the summary immediately without a format-approval step"),
        ("repo_reconcile", "do not stop after the audit to seek blanket or per-item approval"),
        (
            "dot_morning",
            "start eligible work without another permission question or per-task approval",
        ),
        ("dot_night", "do not ask for another blanket or per-task approval"),
        ("riff", "begin exploring, challenging and testing it immediately"),
    ],
)
def test_settled_intent_proceeds_without_an_extra_approval_gate(stem, instruction):
    assert_instructions(stem, instruction)


def test_automaticity_retains_requested_approval_and_required_boundaries():
    assert_instructions("tldr", "Put any approval request together at the end")
    assert_instructions("repo_reconcile", "Required specific confirmations still apply")
    assert_instructions("dot_morning", "actual available grants and routes")
    assert_instructions("dot_night", "pass a real deadline, end or reinterpret a repetition")
    assert_instructions("riff", "This is an advisory conversation")


def test_riff_tests_the_simplest_option_in_wider_context_without_implementing():
    assert_instructions(
        "riff",
        "relevant wider context",
        "Always consider and recommend the simplest thing that could work",
        "prior attempts",
        "existing solution, a manual approach, a smaller version, reuse",
        "deferral or doing nothing",
        "Challenge the premise",
        "concrete example, counterexample, walkthrough, boundary case or available evidence",
        "Distinguish an illustrative thought experiment from an observed real-world test",
        "confirm or falsify the key assumption",
        "Do not implement, buy, publish, launch background work, alter tasks",
    )


@pytest.mark.parametrize("stem,trigger,capability,groups", NOTES)
def test_public_notes_have_no_personal_instance_values(stem, trigger, capability, groups):
    text = (ROOT / "templates" / f"{stem}.json").read_text(encoding="utf-8")
    private_values = r"\b\d{4}-\d{2}-\d{2}\b|[A-Z]:\\|/home/|\.ts\.net|@[^\s]+\.[a-z]"
    assert re.search(private_values, text) is None
