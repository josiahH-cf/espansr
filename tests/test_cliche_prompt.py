"""Contract tests for the standalone :cliche prose-naturalization prompt.

These tests are self-contained: they read the checked-in ``templates/cliche.json``
and compare it against an in-repo copy of the authoritative seed-pattern list, so
they never depend on an uploaded checklist being mounted in CI.

The command shipped first as ``:humanize`` and was renamed to ``:cliche``; the
bundled file is ``cliche.json`` and reconciliation migrates a previously
installed ``humanize.json`` live copy to it.
"""

import json
import re
import shutil
from pathlib import Path

from espansr.core.command_catalog import build_command_catalog
from espansr.core.config import Config
from espansr.core.discovery import (
    prompt_note_triggers,
    render_docs_note_list,
    render_quick_help,
)
from espansr.core.templates import (
    _RENAMED_BUNDLED_TEMPLATE_FILES,
    _RETIRED_BUNDLED_TEMPLATE_FILES,
    Template,
    TemplateManager,
    apply_bundled_template_report,
    build_bundled_template_report,
)
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
CLICHE_PATH = TEMPLATES_DIR / "cliche.json"
HELP_PATH = TEMPLATES_DIR / "espansr_help.json"
DOCS_PATH = ROOT / "docs" / "TEMPLATES.md"

INLINE_CONTEXT_FOOTER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n"

# The 84 authoritative seed-pattern labels reproduced verbatim from the
# normative prompt (section 4). Curly apostrophes and the em dash are preserved
# exactly so the coverage check matches the prompt content byte for byte.
SEED_LABELS = (
    # Repetitive formulas, staged insight, and therapist-style phrasing
    "No X, no Y",
    "That’s the whole ...",
    "Did not X, did not Y",
    "Don’t VERB it ... VERB it",
    "Sit with that",
    "You already know",
    "Is the entire ...",
    "The entire ... is",
    "Is real ... and / not",
    "The punchline is",
    "Worth naming",
    "That’s not nothing",
    "It’s important to note",
    "It’s worth noting",
    # Formulaic scene-setting and topic transitions
    "In today’s ... world",
    "In an ever-evolving ...",
    "In the realm of",
    "Delve into",
    "Dive into",
    "Navigate the ... landscape",
    "Navigate the complexities",
    "At its core",
    "When it comes to",
    "The key takeaway",
    "Here’s the thing",
    "Let’s unpack / explore",
    # Contrast and escalation formulas
    "Not just X, but Y",
    "It’s not about X, it’s about Y",
    "This isn’t just X—it’s Y",
    "More than just",
    "The question is no longer X, but Y",
    "The real question is",
    "Whether you’re X or Y",
    "From X to Y",
    # Staged imagery and rhetorical fragments
    "Picture this / Imagine a world",
    "The result? / The catch?",
    # Inflated significance and metaphor
    "A testament to",
    "Serves as a reminder",
    "A powerful reminder",
    "Underscores the importance",
    "Sheds light on",
    "Paves the way",
    "Bridge the gap",
    "At the intersection of",
    "Intricate interplay",
    # Marketing, corporate, and uplift language
    "Unlock the power / potential",
    "Harness the power",
    "Leverage X to Y",
    "Game-changer",
    "Seamless / seamlessly",
    "Robust and scalable",
    "Holistic approach",
    "Multifaceted / nuanced",
    "Transformative",
    "Actionable insights",
    "Foster / empower / elevate",
    "Rich tapestry",
    "Journey",
    "Cornerstone / catalyst",
    "Paradigm shift / new era",
    # Generic urgency, future, balance, and inevitability
    "Now more than ever",
    "No longer optional",
    "The possibilities are endless",
    "Only scratching the surface",
    "No one-size-fits-all",
    "A delicate balance",
    "Challenges and opportunities",
    "Moving forward",
    "As we look ahead",
    # Formulaic conclusions and transitions
    "Ultimately / In conclusion",
    "At the end of the day",
    "Simply put",
    "That said",
    "With that in mind",
    "The answer lies in",
    "X is poised to",
    "The future of X",
    "Only time will tell",
    "Clear, concise, and compelling",
    "By doing so",
    "What this means is",
    "Make no mistake",
    "The reality / truth is",
    "Against this backdrop",
)


def _load() -> dict:
    return json.loads(CLICHE_PATH.read_text(encoding="utf-8"))


def _content() -> str:
    return _load()["content"]


# ── Template identity ────────────────────────────────────────────────────────


def test_cliche_template_exists_and_parses():
    """The bundled template file exists and is a JSON object."""
    assert CLICHE_PATH.exists()
    assert isinstance(_load(), dict)


def test_cliche_metadata_matches_spec():
    """Metadata matches the normative template with the :cliche trigger."""
    data = _load()
    assert data["name"] == "Humanize Text"
    assert data["trigger"] == ":cliche"
    assert data["category"] == "communication"
    assert data["stage"] == "style-normalization"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []


def test_cliche_content_ends_with_inline_marker():
    """The prompt ends exactly with the shared inline-context footer."""
    assert _content().endswith(INLINE_CONTEXT_FOOTER)


def test_cliche_validates_through_product_path():
    """The template loads and validates with no warnings and no variables."""
    template = Template.from_dict(_load())
    assert validate_template(template) == []
    assert template.variables == []


def test_cliche_has_no_template_variables():
    """The prompt uses the inline marker instead of popup variables."""
    assert "{{" not in _content()


# ── Prompt contract invariants ───────────────────────────────────────────────


def test_cliche_prompt_contract_invariants():
    """Maintainable invariants that lock the behavioral contract in place."""
    content = _content()

    # Accepts pasted text, references, and optional editing direction.
    assert (
        "The user may provide source text, a source reference, audience information, "
        "tone direction, length preferences, phrases to preserve, or other editing "
        "instructions after the final marker." in content
    )
    # Blank-context fallback.
    assert (
        "If the marker is blank, edit the most recent coherent block of eligible prose "
        "already in view." in content
    )
    # Does not select its own instructions as source.
    assert "Do not select this prompt’s own instructions as the source." in content
    # Exact no-text behavior.
    assert (
        "If no editable text is available, return exactly: `No text available to humanize.`"
        in content
    )
    # Meaning preservation.
    assert "- The actual meaning and requested action" in content
    # Fact and uncertainty preservation.
    assert "- All factual claims, numbers, dates, names, qualifications, and uncertainty" in content
    # Protected quotations, citations, code, commands, and structured data.
    assert (
        "- Code fences, inline code, commands, URLs, formulas, data, and configuration exactly "
        "unless explicitly targeted" in content
    )
    assert (
        "- Direct quotations exactly unless the user explicitly asks to edit or paraphrase them"
        in content
    )
    assert "- Markdown links, citations, footnotes, references, filenames, paths" in content
    # Same-language behavior by default.
    assert "- The original language unless translation is explicitly requested" in content
    assert "Multilingual text: edit in the source language" in content
    # No blind string deletion; contextual pattern library.
    assert "Do not rely on literal string matching alone." in content
    assert "Do not remove a phrase merely because it appears in the pattern inventory." in content
    assert "This inventory is a seed, not a closed blacklist." in content
    # Safe replacement strategy and format-specific behavior.
    assert "## 6. Safe Replacement Strategy" in content
    assert "## 8. Format-Specific Handling" in content
    # Natural rhythm without artificial randomness.
    assert (
        "Vary sentence length and structure naturally without creating artificial randomness."
        in content
    )
    # No fake mistakes, anecdotes, or slang.
    assert (
        "Do not add typos, grammatical errors, random contractions, filler words, slang, jokes, "
        "emotional asides, false memories, personal anecdotes, or invented opinions." in content
    )
    # No living-author imitation.
    assert "Do not imitate a living author’s distinctive style." in content
    # No authorship claim.
    assert "Do not state or imply that a human wrote the source." in content
    assert "authorship claim, or detector-evasion guarantee" in content
    # No detector guarantee.
    assert "Do not mention AI detection, scoring, provenance, or the editing process" in content
    # Output-only behavior.
    assert "Return only the revised text." in content
    assert (
        "If the text is already natural and no supported edit improves it, return it unchanged."
        in content
    )


def test_cliche_output_contract_forbids_commentary():
    """The output contract forbids prefaces, change logs, scores, and offers."""
    content = _content()
    for forbidden in (
        "- A preface",
        "- An explanation of the edits",
        "- A change log",
        "- Before-and-after versions",
        "- A cliché count",
        "- A detector score",
        "- A claim about authorship",
        "- An offer to make additional revisions",
    ):
        assert forbidden in content, forbidden


# ── Checklist coverage ───────────────────────────────────────────────────────


def test_seed_label_count_is_exactly_84():
    """The authoritative seed set has exactly 84 unique labels."""
    assert len(SEED_LABELS) == 84
    assert len(set(SEED_LABELS)) == 84


def test_every_seed_label_present_in_prompt():
    """Every seed-pattern label is represented in the prompt content."""
    content = _content()
    for label in SEED_LABELS:
        assert f"`{label}`" in content, label


def test_seed_labels_match_section_four_exactly():
    """The test constant mirrors the prompt's seed inventory exactly."""
    content = _content()
    start = content.index("## 4. Seed Pattern Inventory")
    end = content.index("## 5. Related Patterns Beyond the Seed List")
    section = content[start:end]
    extracted = re.findall(r"\n- `([^`]+)`", section)
    assert len(extracted) == 84
    assert set(extracted) == set(SEED_LABELS)


def test_representative_grammatical_variants_are_addressed():
    """The prompt asks for grammatical and semantic variant matching."""
    content = _content()
    assert (
        "Match grammatical, tense, punctuation, contraction, capitalization, and close "
        "semantic variants." in content
    )


def test_related_pattern_section_present_beyond_seed_list():
    """A separate related-pattern section extends the seed inventory."""
    content = _content()
    assert "## 5. Related Patterns Beyond the Seed List" in content
    for related in (
        "In a world where ...",
        "It goes without saying",
        "Cutting-edge",
        "Mission-critical",
        "Faster. Smarter. Better.",
    ):
        assert f"`{related}`" in content, related


# ── Discovery and runtime catalog ────────────────────────────────────────────


def test_cliche_registered_once_in_canonical_discovery():
    """The trigger is registered exactly once in the discovery source."""
    assert prompt_note_triggers().count(":cliche") == 1


def test_cliche_discovery_row_uses_required_description():
    """The quick help row carries the exact required discovery wording."""
    help_lines = render_quick_help().splitlines()
    rows = [line for line in help_lines if line.strip().startswith(":cliche ")]
    assert len(rows) == 1
    assert "\u2014 remove AI clichés and restore natural prose" in rows[0]


def test_cliche_present_once_in_generated_help_file():
    """Generated :espansr help lists the trigger exactly once."""
    content = json.loads(HELP_PATH.read_text(encoding="utf-8"))["content"]
    rows = [line for line in content.splitlines() if line.strip().startswith(":cliche ")]
    assert len(rows) == 1


def test_cliche_present_in_docs_note_list():
    """The trigger appears in the generated docs prompt-note list."""
    assert "`:cliche`" in render_docs_note_list()
    assert "`:cliche`" in DOCS_PATH.read_text(encoding="utf-8")


def test_humanize_trigger_fully_retired_from_discovery():
    """The old :humanize trigger no longer appears in any discovery surface."""
    assert ":humanize" not in prompt_note_triggers()
    assert ":humanize" not in render_quick_help()
    assert ":humanize" not in render_docs_note_list()


def test_revise_and_sanitize_remain_registered():
    """Renaming to :cliche leaves the neighboring prompts registered."""
    listed = prompt_note_triggers()
    assert ":revise" in listed
    assert ":sanitize" in listed


def test_cliche_surfaced_once_in_runtime_catalog(tmp_path):
    """The runtime :coms catalog surfaces :cliche exactly once."""
    live = tmp_path / "templates"
    live.mkdir()
    for path in TEMPLATES_DIR.glob("*.json"):
        shutil.copy2(path, live / path.name)

    manager = TemplateManager(templates_dir=live)
    entries = build_command_catalog(template_manager=manager, config=Config())
    triggers = [entry.trigger for entry in entries]

    assert triggers.count(":cliche") == 1
    assert triggers.count(":humanize") == 0
    assert triggers.count(":revise") == 1
    assert triggers.count(":sanitize") == 1

    cliche = next(entry for entry in entries if entry.trigger == ":cliche")
    assert cliche.category == "communication"
    assert cliche.stage == "style-normalization"


# ── Bundled reconciliation ───────────────────────────────────────────────────


def test_missing_live_cliche_is_copied(tmp_path):
    """A missing live copy is copied through normal bundled reconciliation."""
    bundled = tmp_path / "bundled"
    local = tmp_path / "local"
    bundled.mkdir()
    local.mkdir()
    shutil.copy2(CLICHE_PATH, bundled / "cliche.json")

    report = build_bundled_template_report(templates_dir=local, bundled_dir=bundled)
    statuses = {entry.filename: entry.status for entry in report.entries}
    assert statuses["cliche.json"] == "missing_local"

    manager = TemplateManager(templates_dir=local)
    result = apply_bundled_template_report(report, manager=manager)
    assert result.copied >= 1

    copied = json.loads((local / "cliche.json").read_text(encoding="utf-8"))
    assert copied["trigger"] == ":cliche"


def test_changed_live_cliche_is_backed_up_before_update(tmp_path):
    """A changed bundled-matching live copy is backed up before it is updated."""
    bundled = tmp_path / "bundled"
    local = tmp_path / "local"
    bundled.mkdir()
    local.mkdir()
    shutil.copy2(CLICHE_PATH, bundled / "cliche.json")

    variant = _load()
    variant["content"] = "old local cliche prompt"
    (local / "cliche.json").write_text(json.dumps(variant), encoding="utf-8")

    report = build_bundled_template_report(templates_dir=local, bundled_dir=bundled)
    statuses = {entry.filename: entry.status for entry in report.entries}
    assert statuses["cliche.json"] == "changed_local"

    manager = TemplateManager(templates_dir=local)
    result = apply_bundled_template_report(report, manager=manager)
    assert result.updated >= 1

    backups = list((local / "_versions").rglob("v*.json"))
    assert backups, "expected a backup version before the update"

    updated = json.loads((local / "cliche.json").read_text(encoding="utf-8"))
    assert updated["content"] == _content()


def test_reconciliation_preserves_unrelated_local_template(tmp_path):
    """Unrelated local-only templates are preserved during reconciliation."""
    bundled = tmp_path / "bundled"
    local = tmp_path / "local"
    bundled.mkdir()
    local.mkdir()
    shutil.copy2(CLICHE_PATH, bundled / "cliche.json")

    mine = {"name": "Mine", "content": "keep me", "trigger": ":mine"}
    (local / "mine.json").write_text(json.dumps(mine), encoding="utf-8")

    report = build_bundled_template_report(templates_dir=local, bundled_dir=bundled)
    manager = TemplateManager(templates_dir=local)
    apply_bundled_template_report(report, manager=manager)

    assert (local / "mine.json").exists()
    assert json.loads((local / "mine.json").read_text(encoding="utf-8")) == mine


def test_live_humanize_copy_migrates_to_cliche(tmp_path):
    """A previously installed :humanize copy migrates to cliche.json with a backup."""
    bundled = tmp_path / "bundled"
    local = tmp_path / "local"
    bundled.mkdir()
    local.mkdir()
    shutil.copy2(CLICHE_PATH, bundled / "cliche.json")

    # Seed the old live humanize.json copy carrying the previous :humanize trigger.
    old = _load()
    old["trigger"] = ":humanize"
    (local / "humanize.json").write_text(json.dumps(old), encoding="utf-8")

    report = build_bundled_template_report(templates_dir=local, bundled_dir=bundled)
    renamed = [entry for entry in report.entries if entry.status == "renamed_local"]
    assert len(renamed) == 1
    assert renamed[0].filename == "cliche.json"

    manager = TemplateManager(templates_dir=local)
    result = apply_bundled_template_report(report, manager=manager)
    assert result.migrated >= 1

    assert not (local / "humanize.json").exists()
    migrated = json.loads((local / "cliche.json").read_text(encoding="utf-8"))
    assert migrated["trigger"] == ":cliche"

    backups = list((local / "_versions").rglob("v*.json"))
    assert backups, "expected a backup of the old humanize.json before migration"


def test_cliche_migrates_from_humanize_predecessor():
    """The rename map records humanize.json as the sole predecessor of cliche.json."""
    assert _RENAMED_BUNDLED_TEMPLATE_FILES["cliche.json"] == ("humanize.json",)
    assert "cliche.json" not in _RETIRED_BUNDLED_TEMPLATE_FILES
    assert not (TEMPLATES_DIR / "humanize.json").exists()


def test_cliche_does_not_alter_revise_or_sanitize():
    """Renaming to :cliche does not touch the revise or sanitize prompts."""
    revise = json.loads((TEMPLATES_DIR / "revise.json").read_text(encoding="utf-8"))
    sanitize = json.loads((TEMPLATES_DIR / "sanitize.json").read_text(encoding="utf-8"))

    assert revise["trigger"] == ":revise"
    assert sanitize["trigger"] == ":sanitize"
    assert ":cliche" not in revise["content"]
    assert ":cliche" not in sanitize["content"]
    assert ":cliche" not in revise.get("replaces", [])
    assert ":cliche" not in sanitize.get("replaces", [])
    assert _load()["replaces"] == []
