"""Contract tests for the :tddh reliability-default prompt.

The command shipped first as ``:defaults`` (name "Default Working Style") and was
simplified and renamed to ``:tddh`` in the same canonical file
``templates/tddh_defaults.json``; normal same-filename reconciliation migrates a
previously installed ``:defaults`` live copy to ``:tddh`` with a backup.
"""

import json
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
TDDH_PATH = TEMPLATES_DIR / "tddh_defaults.json"
HELP_PATH = TEMPLATES_DIR / "espansr_help.json"
DOCS_PATH = ROOT / "docs" / "TEMPLATES.md"

INLINE_MARKER = "ADDITIONAL INSTRUCTIONS OR OUTPUT PREFERENCES BELOW. IGNORE IF BLANK.\n\n"


def _load() -> dict:
    return json.loads(TDDH_PATH.read_text(encoding="utf-8"))


def _content() -> str:
    return _load()["content"]


# ── Template identity ────────────────────────────────────────────────────────


def test_tddh_template_exists_and_parses():
    """The canonical file exists, parses, and no duplicate defaults file remains."""
    assert TDDH_PATH.exists()
    assert not (TEMPLATES_DIR / "defaults.json").exists()
    assert isinstance(_load(), dict)


def test_tddh_metadata_matches_spec():
    """Metadata exactly matches the normative template."""
    data = _load()
    assert data["name"] == "Think Deeply, Don't Hallucinate"
    assert data["trigger"] == ":tddh"
    assert data["category"] == "preference"
    assert data["stage"] == "reliability-defaults"
    assert data["next_triggers"] == []
    assert data["replaces"] == [":defaults"]
    assert data.get("variables", []) == []


def test_tddh_content_ends_with_optional_instructions_marker():
    """The prompt ends exactly with the optional-instructions marker."""
    assert _content().endswith(INLINE_MARKER)


def test_tddh_validates_through_product_path():
    """The template loads and validates with no warnings and no variables."""
    template = Template.from_dict(_load())
    assert validate_template(template) == []
    assert template.variables == []


# ── Prompt contract: required content ────────────────────────────────────────


def test_tddh_prompt_contract_invariants():
    """Maintainable invariants that lock the reliability contract in place."""
    content = _content()

    assert (
        "Apply these defaults to the request above unless the user explicitly overrides" in content
    )
    assert "Think deeply before responding or acting." in content
    assert "Do not hallucinate or make anything up." in content
    assert (
        "Never invent facts, sources, quotations, files, commands, results, requirements, "
        "events, or user intent." in content
    )
    # Fact preservation.
    assert "Preserve material facts accurately." in content
    # Fact / inference / assumption / unknown separation.
    assert (
        "Keep confirmed facts, reasonable inferences, assumptions, and unknowns distinct."
        in content
    )
    assert "Never present an inference or assumption as a confirmed fact." in content
    # Verification when needed and possible.
    assert "when verification is needed and possible" in content
    # No false claims of access or execution.
    assert (
        "Never claim to have read, accessed, run, tested, changed, completed, or verified "
        "something that you did not actually read, access, run, test, change, complete, or verify."
        in content
    )
    # Explicit uncertainty responses.
    assert "`I don't know.`" in content
    assert "`I couldn't verify that.`" in content
    assert "briefly state what information is missing" in content
    # Resolve ambiguity from context; one concise question only when material.
    assert "Resolve ambiguity from reliable context when possible." in content
    assert (
        "Ask one concise question only when different interpretations would materially change "
        "the result" in content
    )
    # Accurate partial answer over a confident guess.
    assert (
        "Prefer an accurate partial answer or an explicit limitation over a confident guess."
        in content
    )
    # Optional additional instructions / output preferences.
    assert "Follow any additional instructions or output preferences below" in content
    assert "IGNORE IF BLANK" in content


# ── Prompt contract: forbidden content ───────────────────────────────────────


def test_tddh_prompt_omits_format_and_guarantee_language():
    """The compact modifier imposes no format and promises no perfect factuality."""
    content = _content()
    lowered = content.lower()

    assert "markdown" not in lowered
    assert "optional markdown guidance" not in lowered
    assert "#" not in content  # no required heading format
    assert "bullet" not in lowered  # no required bullet format
    assert "heading" not in lowered
    assert "chain-of-thought" not in lowered
    assert "chain of thought" not in lowered
    assert "step-by-step" not in lowered
    assert "confidence" not in lowered
    assert "%" not in content  # no confidence percentages
    assert "guarantee" not in lowered
    assert "zero hallucination" not in lowered


def test_tddh_prompt_stays_compact():
    """A word-count ceiling keeps this modifier from growing into a workflow."""
    assert len(_content().split()) < 300


# ── Discovery and runtime catalog ────────────────────────────────────────────


def test_tddh_registered_once_and_defaults_absent_in_discovery():
    """Canonical discovery lists :tddh once and no longer lists :defaults."""
    listed = prompt_note_triggers()
    assert listed.count(":tddh") == 1
    assert ":defaults" not in listed


def test_tddh_discovery_row_uses_required_description():
    """The quick help row carries the exact required discovery wording."""
    help_lines = render_quick_help().splitlines()
    rows = [line for line in help_lines if line.strip().startswith(":tddh ")]
    assert len(rows) == 1
    assert "\u2014 think deeply, verify facts, and never make things up" in rows[0]


def test_tddh_present_once_in_generated_help_and_defaults_gone():
    """Generated :espansr help lists :tddh once and drops :defaults entirely."""
    content = json.loads(HELP_PATH.read_text(encoding="utf-8"))["content"]
    rows = [line for line in content.splitlines() if line.strip().startswith(":tddh ")]
    assert len(rows) == 1
    assert ":defaults" not in content


def test_tddh_present_in_docs_note_list_and_defaults_gone():
    """The generated docs note list surfaces :tddh and drops :defaults."""
    note_list = render_docs_note_list()
    assert "`:tddh`" in note_list
    assert "`:defaults`" not in note_list
    assert "`:tddh`" in DOCS_PATH.read_text(encoding="utf-8")


def test_neighbor_utility_prompts_remain_registered():
    """Renaming to :tddh leaves the neighboring utility prompts registered."""
    listed = prompt_note_triggers()
    for trigger in (":listen", ":revise", ":cliche"):
        assert trigger in listed


def test_tddh_surfaced_once_in_runtime_catalog(tmp_path):
    """The runtime :coms catalog surfaces :tddh once and no :defaults."""
    live = tmp_path / "templates"
    live.mkdir()
    for path in TEMPLATES_DIR.glob("*.json"):
        shutil.copy2(path, live / path.name)

    manager = TemplateManager(templates_dir=live)
    entries = build_command_catalog(template_manager=manager, config=Config())
    triggers = [entry.trigger for entry in entries]

    assert triggers.count(":tddh") == 1
    assert triggers.count(":defaults") == 0
    assert triggers.count(":revise") == 1
    assert triggers.count(":cliche") == 1

    tddh = next(entry for entry in entries if entry.trigger == ":tddh")
    assert tddh.category == "preference"
    assert tddh.stage == "reliability-defaults"


def test_exactly_one_bundled_tddh_trigger():
    """Only one bundled template owns :tddh and none still owns :defaults."""
    triggers = []
    for path in TEMPLATES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("trigger"):
            triggers.append(data["trigger"])
    assert triggers.count(":tddh") == 1
    assert triggers.count(":defaults") == 0


# ── Bundled reconciliation ───────────────────────────────────────────────────


def test_defaults_live_copy_is_backed_up_and_updated_to_tddh(tmp_path):
    """An installed :defaults copy is detected as changed, backed up, and updated."""
    bundled = tmp_path / "bundled"
    local = tmp_path / "local"
    bundled.mkdir()
    local.mkdir()
    shutil.copy2(TDDH_PATH, bundled / "tddh_defaults.json")

    # Seed the previously installed :defaults live copy at the same filename.
    old = {
        "name": "Default Working Style",
        "content": "Use my default working style unless I explicitly override it.",
        "trigger": ":defaults",
        "category": "preference",
        "stage": "style",
        "next_triggers": [],
    }
    (local / "tddh_defaults.json").write_text(json.dumps(old), encoding="utf-8")

    report = build_bundled_template_report(templates_dir=local, bundled_dir=bundled)
    statuses = {entry.filename: entry.status for entry in report.entries}
    assert statuses["tddh_defaults.json"] == "changed_local"

    manager = TemplateManager(templates_dir=local)
    result = apply_bundled_template_report(report, manager=manager)
    assert result.updated >= 1

    updated = json.loads((local / "tddh_defaults.json").read_text(encoding="utf-8"))
    assert updated["trigger"] == ":tddh"
    assert updated["trigger"] != ":defaults"

    backups = list((local / "_versions").rglob("v*.json"))
    assert backups, "expected a backup of the old :defaults copy before update"
    backed_up = json.loads(backups[0].read_text(encoding="utf-8"))
    assert backed_up["template_data"]["trigger"] == ":defaults"


def test_reconciliation_preserves_unrelated_local_template(tmp_path):
    """Unrelated local-only templates are preserved during reconciliation."""
    bundled = tmp_path / "bundled"
    local = tmp_path / "local"
    bundled.mkdir()
    local.mkdir()
    shutil.copy2(TDDH_PATH, bundled / "tddh_defaults.json")

    mine = {"name": "Mine", "content": "keep me", "trigger": ":mine"}
    (local / "mine.json").write_text(json.dumps(mine), encoding="utf-8")

    report = build_bundled_template_report(templates_dir=local, bundled_dir=bundled)
    manager = TemplateManager(templates_dir=local)
    apply_bundled_template_report(report, manager=manager)

    assert (local / "mine.json").exists()
    assert json.loads((local / "mine.json").read_text(encoding="utf-8")) == mine


def test_tddh_needs_no_rename_or_retire_entry():
    """Same-filename migration needs no rename-map or retirement entry."""
    assert "tddh_defaults.json" not in _RENAMED_BUNDLED_TEMPLATE_FILES
    assert "tddh_defaults.json" not in _RETIRED_BUNDLED_TEMPLATE_FILES
    assert "defaults.json" not in _RENAMED_BUNDLED_TEMPLATE_FILES
    assert "defaults.json" not in _RETIRED_BUNDLED_TEMPLATE_FILES
    for old_filenames in _RENAMED_BUNDLED_TEMPLATE_FILES.values():
        assert "tddh_defaults.json" not in old_filenames
        assert "defaults.json" not in old_filenames
