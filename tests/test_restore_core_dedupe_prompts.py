"""Contracts for :bring-back-feature, :core-behaviors, and :dedupe.

Each note carries one requested job. These tests pin that job's defining
instructions to the bundled text, prove the note reaches every discovery
surface and the prompt-only catalog, and keep the neighboring notes whose jobs
overlap (:troubleshoot, :stabilize, :prune, :friction) unchanged.
"""

import json
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from espansr.core.capability_catalog import build_catalog
from espansr.core.command_catalog import build_command_catalog
from espansr.core.command_groups import CUSTOM_GROUP, command_cue, groups_for
from espansr.core.config import Config
from espansr.core.discovery import prompt_note_triggers, render_docs_note_list, render_quick_help
from espansr.core.recommend import RecommendationQuery, recommend
from espansr.core.templates import Template, TemplateManager
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
MARKER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK."

# stem, trigger, capability, browse groups, phrases that define the job
PROMPTS = (
    (
        "bring_back_feature",
        ":bring-back-feature",
        "feature-restoration",
        {"keep-moving"},
        (
            "This is a forward fix.",
            "Do not revert commits wholesale, reset or rewrite history, force-push",
            "Do not stash, discard, or commit changes you did not make",
            "Preserve what changed on purpose.",
            "## 2. Prove it used to work",
            "## 3. Reproduce the loss now",
            "Keep the change's intended purpose separate from its accidental side effect.",
            "fails on the current broken state and passes once the behavior is back",
            "Also confirm that the newer behavior the breaking change introduced still works.",
        ),
    ),
    (
        "core_behaviors",
        ":core-behaviors",
        "core-behavior-stabilization",
        {"check-work"},
        (
            "- Core behaviors:",
            "- Other identified behaviors:",
            "in exactly one comprehensive round of questions",
            "ask whether it is what the user intended",
            "which should also be protected, with your recommendation for each",
            "recommend any additional behaviors",
            "give a recommended answer for every item",
            "Omission is never approval.",
            "A core behavior is dropped only when the user explicitly says to drop that item.",
            "Do not ask a second round: after the answers, proceed with the confirmed items",
            "## Phase 3: One shot",
            "## Verification at the end",
        ),
    ),
    (
        "dedupe",
        ":dedupe",
        "dedupe-reconciliation",
        {"check-work", "research-challenge"},
        (
            "- Code:",
            "- Tests:",
            "- Governance and process:",
            "## 1. Establish the current direction",
            "identify the project's own instruction hierarchy",
            "never authority to override a governing instruction",
            "Do not edit anything yet.",
            "the recommended resolution",
            'approve by number ("approve: 1, 4")',
            '"audit only"',
            "Items the user does not approve stay unchanged;",
            "Apply only the approved items",
            "Do not add a new governance layer, registry, or framework",
        ),
    ),
)


def _load(stem: str) -> dict:
    return json.loads((ROOT / "templates" / f"{stem}.json").read_text(encoding="utf-8"))


@pytest.fixture(params=PROMPTS, ids=[p[0] for p in PROMPTS])
def prompt(request):
    stem, trigger, capability, groups, phrases = request.param
    return _load(stem), trigger, capability, groups, phrases


@pytest.fixture(scope="module")
def entries():
    return build_command_catalog(TemplateManager(templates_dir=ROOT / "templates"), Config())


def test_prompt_validates_and_renders_without_a_prerequisite(prompt):
    data, trigger, capability, _, _ = prompt
    template = Template.from_dict(data)
    assert template.trigger == trigger
    assert template.capability_id == capability
    assert template.variables == []
    assert template.next_triggers == []
    assert validate_template(template) == []
    assert template.render({}) == data["content"]
    assert template.content.endswith(MARKER + "\n\n")


def test_prompt_carries_its_requested_job(prompt):
    data, _, _, _, phrases = prompt
    missing = [phrase for phrase in phrases if phrase not in data["content"]]
    assert missing == []


def test_core_behaviors_confirms_only_what_the_reply_covers():
    """A selective approval confirms its items; omission never becomes approval."""
    content = _load("core_behaviors")["content"]
    rules = (
        # Each reply form states exactly what it confirms.
        '"approve all" accepts every recommendation',
        '"all except 3, 5" accepts every recommendation except the items named',
        '"approve: 1, 4" confirms only the items named',
        "Your recommendation is accepted only through one of those.",
        # Omission is told apart from approval.
        "An item the reply does not cover is not confirmed: do not apply your recommendation to it",
        'never read a selective approval such as "approve: 1, 4" as approval of the other items',
        'An item named in "all except" without an answer is not confirmed either.',
        # Unconfirmed items wait, unchanged, and core behaviors survive.
        "Every item that is not confirmed is deferred and stays unchanged.",
        "A deferred core behavior is neither dropped nor altered",
        "or deferred because the reply did not cover it",
        # One round only; the confirmed subset still runs.
        "even when they are only a subset",
        "Turn the confirmed items, and only those, into the stabilization contract",
        "Deferred items get no changes of their own",
        "confirm that deferred core behaviors still behave as they did before",
        "2. Deferred: every item the reply did not confirm, left unchanged",
    )
    assert [rule for rule in rules if rule not in content] == []
    defaulting = re.compile(
        r"(unanswered|unmentioned|silen\w*|omitted)[^.]*\btakes?\b[^.]*recommendation", re.I
    )
    assert defaulting.search(content) is None


def test_dedupe_keeps_the_projects_instruction_hierarchy():
    """Behavior and freshness inform recommendations; they never outrank governing text."""
    content = _load("dedupe")["content"]
    rules = (
        "That hierarchy decides which source controls, not this prompt and not which source "
        "looks newer.",
        "Current behavior, recent merges, and how recently a document was edited are evidence "
        "for your recommendations, never authority to override a governing instruction.",
        "Current behavior may be the very regression or violation under investigation",
        "a newer file is not automatically the controlling one",
        "Where the hierarchy settles a disagreement, cite the rule that settles it.",
        "do not pick a winner: record the conflict and ask it in the step 3 batch",
        "an item the reply does not mention is not approved",
        "First response: the instruction hierarchy you found",
    )
    assert [rule for rule in rules if rule not in content] == []
    # No ranking of its own: nothing "wins", and behavior never decides precedence.
    assert re.search(r"\bwins?\b", content) is None
    assert "intended observed behavior" not in content


def test_docs_describe_selective_approval_and_the_instruction_hierarchy():
    docs = (ROOT / "docs" / "TEMPLATES.md").read_text(encoding="utf-8")
    flat = " ".join(docs.split())
    assert '"approve: 1, 4" confirms only those items' in flat
    assert "anything your reply does not cover stays deferred and unchanged" in flat
    assert "a core behavior is dropped only when you say so" in flat
    assert "An unanswered item takes the recommendation" not in flat
    assert "It follows the project's own instruction hierarchy" in flat
    assert "never authority over a governing instruction" in flat
    assert "the newest explicit decisions, and intended current behavior" not in flat


def test_prompt_is_self_contained_and_names_no_other_trigger(prompt):
    data, trigger, _, _, _ = prompt
    others = [t for t in prompt_note_triggers() if t != trigger]
    assert [t for t in others if t in data["content"]] == []


def test_prompt_reaches_every_discovery_surface_and_prompt_only_catalog(prompt, entries):
    _, trigger, capability, groups, _ = prompt
    assert prompt_note_triggers().count(trigger) == 1
    assert any(line.strip().startswith(f"{trigger} ") for line in render_quick_help().splitlines())
    assert f"`{trigger}`" in render_docs_note_list()
    catalog = build_catalog(ROOT / "templates")
    assert catalog["validation"] == "passed"
    descriptor = next(e for e in catalog["entries"] if e.get("capability_id") == capability)
    assert descriptor["execution"]["classification"] == "prompt-only"
    assert "definition_bytes" not in descriptor
    entry = next(e for e in entries if e.trigger == trigger)
    assert CUSTOM_GROUP not in groups_for(entry)
    assert {group.id for group in groups_for(entry)} == groups
    assert command_cue(entry)[1]


def test_docs_paragraph_explains_the_note(prompt):
    _, trigger, _, _, _ = prompt
    docs = (ROOT / "docs" / "TEMPLATES.md").read_text(encoding="utf-8")
    assert f"Use `{trigger}`" in docs
    assert f"| `{trigger}` |" in docs


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("bring back a feature that used to work", ":bring-back-feature"),
        ("a recent change broke something that worked before", ":bring-back-feature"),
        ("identify the core behaviors of the project", ":core-behaviors"),
        ("stabilize what the project must always do", ":core-behaviors"),
        ("deduplicate code, tests, and governance", ":dedupe"),
        ("find where rules, docs, and tests disagree", ":dedupe"),
        # Neighbors keep their own jobs.
        ("architecture mismatch duplicated logic owner", ":stabilize"),
        ("audit what to delete", ":prune"),
    ],
)
def test_intent_search_finds_the_distinct_job(entries, query, expected):
    results = recommend(entries, RecommendationQuery(text=query))
    assert results[0].entry.trigger == expected


def test_typing_stabilize_surfaces_both_stabilizers(entries):
    results = recommend(entries, RecommendationQuery(text="stabilize"))
    assert [r.entry.trigger for r in results[:2]] == [":stabilize", ":core-behaviors"]


def test_prompt_copy_receives_complete_instructions(prompt, entries, qtbot):
    from espansr.core.workflows import WorkflowCatalog
    from espansr.ui.commands_popup import CommandsPopupDialog

    data, trigger, _, _, _ = prompt
    entry = next(e for e in entries if e.trigger == trigger)
    with (
        patch("espansr.ui.commands_popup.get_config", return_value=Config()),
        patch("espansr.ui.commands_popup.save_config", return_value=True),
        patch("espansr.ui.commands_popup.load_config_fresh", side_effect=Config),
        patch("espansr.ui.commands_popup.copy_text") as copy,
    ):
        dialog = CommandsPopupDialog(entries=entries, workflow_catalog=WorkflowCatalog())
        qtbot.addWidget(dialog)
        dialog._search_edit.setText(trigger)
        assert entry in dialog._shown_entries
        dialog._copy_prompt(entry)
        assert copy.call_args.args[0] == data["content"]


@pytest.mark.parametrize(
    ("stem", "trigger", "capability", "produces"),
    [
        ("troubleshoot", ":troubleshoot", "troubleshooting", ["verification-report"]),
        (
            "architecture_stabilizer",
            ":stabilize",
            "architecture-stabilization",
            ["implementation-handoff"],
        ),
        (
            "deletion_simplification_audit",
            ":prune",
            "deletion-simplification-audit",
            ["deletion-audit"],
        ),
        ("maintenance_friction", ":friction", "maintenance-friction", ["verification-report"]),
    ],
)
def test_neighboring_notes_keep_their_existing_jobs(stem, trigger, capability, produces):
    data = _load(stem)
    assert data["trigger"] == trigger
    assert data["capability_id"] == capability
    assert data["produces"] == produces
