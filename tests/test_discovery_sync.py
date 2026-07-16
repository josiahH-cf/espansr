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
    """Every bundled template trigger is surfaced in the :espansr quick help."""
    content = render_quick_help()
    for path in TEMPLATES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        trigger = data.get("trigger", "")
        if not trigger:
            continue
        assert trigger in content, f"{path.name} trigger {trigger} is not in the quick help"


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
