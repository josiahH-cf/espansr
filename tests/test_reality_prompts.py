"""Contract tests for the bundled :reality-max and :reality-min notes.

Both notes carry explicit, stable ``capability_id`` values (``reality-max`` and
``reality-min``) so external consumers that do not implement the file-stem
fallback see the same identity the bundled-capabilities table in
``docs/PROCESS.md`` documents. Their bodies stay tool-neutral: per PROCESS.md,
prompt bodies never route the reader to the host tool or another trigger.
"""

import json
from pathlib import Path

from espansr.core.capabilities import effective_capability_id
from espansr.core.templates import Template, TemplateManager
from espansr.integrations.validate import validate_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"
PROCESS_DOC = ROOT / "docs" / "PROCESS.md"

REALITY_NOTES = {
    "reality.json": (":reality-max", "reality-max"),
    "reality_min.json": (":reality-min", "reality-min"),
}


def _load(filename: str) -> dict:
    return json.loads((TEMPLATES_DIR / filename).read_text(encoding="utf-8"))


# ── Stable capability identity ───────────────────────────────────────────────


def test_reality_notes_declare_explicit_capability_ids():
    for filename, (trigger, capability_id) in REALITY_NOTES.items():
        data = _load(filename)
        assert data["trigger"] == trigger
        assert data.get("capability_id") == capability_id, filename


def test_explicit_ids_win_over_the_file_stem_fallback():
    manager = TemplateManager(templates_dir=TEMPLATES_DIR)
    by_trigger = {t.trigger: t for t in manager.list_all()}
    for trigger, capability_id in REALITY_NOTES.values():
        assert effective_capability_id(by_trigger[trigger]) == capability_id, trigger


def test_reality_capability_ids_are_unique_among_bundled():
    owners = {}
    for path in TEMPLATES_DIR.glob("*.json"):
        capability_id = json.loads(path.read_text(encoding="utf-8")).get("capability_id", "")
        if capability_id:
            owners.setdefault(capability_id, []).append(path.name)
    for _trigger, capability_id in REALITY_NOTES.values():
        assert owners.get(capability_id) == [
            next(f for f, (_t, c) in REALITY_NOTES.items() if c == capability_id)
        ], capability_id
    assert {k: v for k, v in owners.items() if len(v) > 1} == {}


def test_process_doc_lists_reality_capabilities_explicitly():
    text = PROCESS_DOC.read_text(encoding="utf-8")
    assert "| `reality-max` | `:reality-max` | `evidence-report` |" in text
    assert "| `reality-min` | `:reality-min` | `evidence-report` |" in text
    assert "(derived from" not in text


# ── Identity and validation ──────────────────────────────────────────────────


def test_reality_notes_keep_their_artifact_metadata():
    for filename in REALITY_NOTES:
        data = _load(filename)
        assert data["produces"] == ["evidence-report"], filename
        assert "context-packet" in data["accepts"], filename
        assert data["next_triggers"] == [], filename


def test_reality_notes_validate_through_product_path():
    for filename in REALITY_NOTES:
        warnings = validate_template(Template.from_dict(_load(filename)))
        assert [w.message for w in warnings if w.severity == "error"] == [], filename


# ── Tool-neutral bodies ──────────────────────────────────────────────────────


def test_reality_bodies_never_name_the_host_tool():
    for filename in REALITY_NOTES:
        assert "espansr" not in _load(filename)["content"].lower(), filename


def test_reality_max_boundary_points_at_any_next_prompt():
    content = _load("reality.json")["content"]
    assert "- tell the user which other prompt or command to run next." in content
    assert "which espansr command" not in content
