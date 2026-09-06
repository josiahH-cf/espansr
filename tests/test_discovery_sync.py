"""Guarantees the static discovery surfaces stay in sync with the templates.

The ``:espansr`` quick help and the ``docs/TEMPLATES.md`` prompt-note list are
both rendered from :mod:`espansr.core.discovery`. These tests make drift
impossible: a new bundled note that is not surfaced everywhere fails CI.
"""

import json
import re
from pathlib import Path

from espansr.core.discovery import (
    SYSTEM_TRIGGERS,
    prompt_note_triggers,
    render_docs_note_list,
    render_quick_help,
)

ROOT = Path(__file__).resolve().parents[1]
HELP_PATH = ROOT / "templates" / "espansr_help.json"
DOCS_PATH = ROOT / "docs" / "TEMPLATES.md"
TEMPLATES_DIR = ROOT / "templates"

BEGIN = (
    "<!-- BEGIN generated note list: run "
    "`python scripts/sync_discovery.py --apply` after changing templates -->"
)
END = "<!-- END generated note list -->"


def _bundled_triggers() -> set:
    triggers = set()
    for path in TEMPLATES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        trigger = data.get("trigger", "")
        if trigger:
            triggers.add(trigger)
    return triggers


def test_quick_help_content_matches_generator():
    """templates/espansr_help.json content is generated from the single source."""
    content = json.loads(HELP_PATH.read_text(encoding="utf-8"))["content"]
    assert (
        content == render_quick_help()
    ), "Quick help is stale. Run: python scripts/sync_discovery.py"


def test_docs_note_list_matches_generator():
    """The docs prompt-note list block is generated from the same source."""
    text = DOCS_PATH.read_text(encoding="utf-8")
    match = re.search(re.escape(BEGIN) + r"\n(.*?)\n" + re.escape(END), text, re.S)
    assert match, "Generated note-list markers are missing from docs/TEMPLATES.md"
    assert (
        match.group(1) == render_docs_note_list()
    ), "Docs note list is stale. Run: python scripts/sync_discovery.py"


def test_every_bundled_trigger_is_in_quick_help():
    """Every bundled template trigger has its own row in the :espansr quick help."""
    help_lines = render_quick_help().splitlines()
    for path in TEMPLATES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        trigger = data.get("trigger", "")
        if not trigger:
            continue
        # A whole-row match: a bare substring check would let ":reality" pass
        # via the ":reality-max" row.
        assert any(
            line.strip().startswith(f"{trigger} ") for line in help_lines
        ), f"{path.name} trigger {trigger} is not in the quick help"


def test_every_prompt_note_is_in_docs_list():
    """Every non-system bundled note appears in the generated docs list."""
    listed = set(prompt_note_triggers())
    for path in TEMPLATES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        trigger = data.get("trigger", "")
        if not trigger or trigger in SYSTEM_TRIGGERS:
            continue
        assert trigger in listed, f"{path.name} trigger {trigger} is missing from the note list"


def test_no_phantom_discovery_entries():
    """Every trigger the discovery surfaces list is backed by a bundled template."""
    triggers = _bundled_triggers()
    for trigger in prompt_note_triggers():
        assert trigger in triggers, f"Discovery lists {trigger} with no bundled template"


# ── Pruned prompt guardrails ─────────────────────────────────────────────────

_REMOVED_TRIGGERS = (
    ":feat-plan",
    ":feat-runner",
    ":feat",
    ":feedback-loop",
    ":agent-scaffold",
    ":merge",
    ":rebase",
    ":save",
    ":pocket-system",
    ":distill",
    ":summarize",
    ":qa",
    ":critique",
    ":gaps-2",
    ":principles",
    ":fp",
    ":plain",
    ":dumb",
    ":simplify",
    ":explain-1",
    ":hide-ai",
    ":defaults",
    ":pocket-note",
    ":work-merge-safe",
    ":reality",
    ":project-init",
)


def test_removed_triggers_absent_from_discovery():
    """Pruned prompt triggers are not registered in the discovery source."""
    listed = set(prompt_note_triggers())
    for trigger in _REMOVED_TRIGGERS:
        assert trigger not in listed, trigger


def test_removed_triggers_absent_from_generated_surfaces():
    """Pruned triggers are gone from the quick help and docs note list."""
    help_lines = render_quick_help().splitlines()
    docs_list = render_docs_note_list()
    for trigger in _REMOVED_TRIGGERS:
        assert not any(line.strip().startswith(f"{trigger} ") for line in help_lines), trigger
        assert f"`{trigger}`" not in docs_list, trigger


def test_preserved_prompts_remain_registered():
    """Preserved merge/rebase helpers and neighbors stay in discovery after the prune."""
    listed = set(prompt_note_triggers())
    for trigger in (
        ":work-merge",
        ":git-rebase-sh",
        ":git-rebase-ps",
        ":git-yolo-sh",
        ":project-init-llm",
        ":feature",
        ":telegram",
        ":troubleshoot",
        ":verify",
    ):
        assert trigger in listed, trigger


def test_feature_prompt_registered_in_all_surfaces():
    """The new :feature prompt appears once in discovery, quick help, and the docs list."""
    listed = prompt_note_triggers()
    assert listed.count(":feature") == 1
    help_lines = render_quick_help().splitlines()
    assert any(line.strip().startswith(":feature ") for line in help_lines)
    assert "`:feature`" in render_docs_note_list()


def test_unblock_prompt_registered_in_all_surfaces():
    """The new :unblock prompt appears once in discovery, quick help, and the docs list."""
    listed = prompt_note_triggers()
    assert listed.count(":unblock") == 1
    help_lines = render_quick_help().splitlines()
    assert any(line.strip().startswith(":unblock ") for line in help_lines)
    assert "`:unblock`" in render_docs_note_list()


def test_goal_prompt_registered_in_all_surfaces():
    """The reworked :goal prompt appears once in discovery, quick help, and the docs list."""
    listed = prompt_note_triggers()
    assert listed.count(":goal") == 1
    help_lines = render_quick_help().splitlines()
    assert any(line.strip().startswith(":goal ") for line in help_lines)
    assert "`:goal`" in render_docs_note_list()


# ── Static scaffolding stays aligned with the CLI and the system triggers ────


def test_quick_help_cli_rows_cover_every_user_facing_subcommand():
    """Every parser subcommand except the installer-only one has a quick-help row."""
    import argparse

    from espansr.__main__ import _build_parser
    from espansr.core.discovery import _CLI

    parser = _build_parser()
    subcommands = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            subcommands.update(action.choices.keys())
    assert subcommands, "the CLI parser declares no subcommands"

    listed = {label for label, _blurb in _CLI}
    missing = (subcommands - {"record-install"}) - listed
    assert not missing, f"CLI subcommands missing from the :espansr quick help: {sorted(missing)}"
    assert "record-install" not in listed


def test_quick_help_discovery_rows_cover_every_system_trigger():
    """Every generated system trigger is listed under Discovery in the quick help."""
    from espansr.core.discovery import _DISCOVERY

    labels = {label for label, _blurb in _DISCOVERY}
    for trigger in SYSTEM_TRIGGERS:
        assert trigger in labels, f"{trigger} is missing from the Discovery rows"
    help_lines = render_quick_help().splitlines()
    for trigger in SYSTEM_TRIGGERS:
        assert any(line.strip().startswith(f"{trigger} ") for line in help_lines), trigger


def test_quick_help_footer_names_every_platform_config_path():
    """The footer no longer assumes Linux; it names each platform and points at status."""
    content = render_quick_help()
    for path in (
        "~/.config/espansr/",
        "%APPDATA%\\espansr\\",
        "~/Library/Application Support/espansr/",
    ):
        assert path in content, path
    assert "espansr status prints the active path" in content
