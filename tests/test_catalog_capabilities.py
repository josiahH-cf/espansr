"""Catalog and publication-isolation acceptance checks (ARCH-08, ARCH-10, BEH-01).

The command catalog exposes capability metadata and workflow membership for
discovery, while generated Espanso YAML stays limited to trigger, replacement,
and variables — no capability-graph metadata may leak into matches.
"""

import json
from pathlib import Path
from unittest.mock import patch

import yaml

from espansr.core.command_catalog import build_command_catalog
from espansr.core.config import Config
from espansr.core.templates import Template, TemplateManager

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"


def _bundled_entries():
    manager = TemplateManager(templates_dir=TEMPLATES_DIR)
    return build_command_catalog(template_manager=manager, config=Config())


# ── ARCH-08: discovery integration ───────────────────────────────────────────


def test_catalog_exposes_capability_metadata():
    entries = {e.trigger: e for e in _bundled_entries()}
    gaps = entries[":gaps"]
    assert gaps.capability_id == "gap-review"
    assert gaps.intent_tags
    assert "evidence-report" in gaps.accepts
    assert "gap-review" in gaps.produces
    assert gaps.use_when
    assert gaps.avoid_when


def test_catalog_exposes_workflow_membership_and_neighbors():
    entries = {e.trigger: e for e in _bundled_entries()}
    research = entries[":research"]
    assert "evidence-research-cycle" in research.workflows
    # Derived neighbors map capability edges to trigger + label pairs.
    targets = {trigger for trigger, _label in research.workflow_next}
    assert ":gaps" in targets
    assert ":visual" in targets
    assert ":html-help-doc" in targets
    labels = {label for _trigger, label in research.workflow_next}
    assert any("Challenge" in label for label in labels)


def test_derived_neighbors_are_not_written_back_to_templates():
    """Runtime derivation never mutates template next_triggers on disk."""
    _bundled_entries()
    for path in TEMPLATES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("next_triggers", []) == [], path.name


def test_system_entries_remain_available():
    entries = {e.trigger: e for e in _bundled_entries()}
    assert entries[":coms"].source == "system"
    assert entries[":sync"].source == "system"
    assert entries[":aopen"].source == "system"


def test_catalog_stays_fresh_per_call(tmp_path):
    """Fresh reads still reflect current files after capability enrichment."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    manager = TemplateManager(templates_dir=templates_dir)
    manager.save(Template(name="First", content="x", trigger=":first"))
    first = {e.trigger for e in build_command_catalog(manager, Config())}
    manager.save(Template(name="Second", content="y", trigger=":second"))
    second = {e.trigger for e in build_command_catalog(manager, Config())}
    assert ":first" in first and ":second" not in first
    assert ":second" in second


def test_litmus_is_directly_invocable_from_catalog():
    """BEH-01/BEH-14: :litmus appears as an ordinary catalog entry."""
    entries = {e.trigger: e for e in _bundled_entries()}
    assert ":litmus" in entries
    assert entries[":litmus"].capability_id == "human-litmus"


# ── ARCH-10: publication isolation ───────────────────────────────────────────


def test_capability_metadata_does_not_leak_into_espanso_yaml(tmp_path):
    from espansr.integrations.espanso import sync_to_espanso

    match_dir = tmp_path / "match"
    match_dir.mkdir()
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "cap.json").write_text(
        json.dumps(
            {
                "name": "Cap",
                "content": "expanded text",
                "trigger": ":cap",
                "capability_id": "cap-demo",
                "intent_tags": ["demo"],
                "accepts": ["rough-intent"],
                "produces": ["evidence-report"],
                "use_when": "use",
                "avoid_when": "avoid",
                "output_contract": {"schema": 1, "required_sections": ["A"]},
            }
        ),
        encoding="utf-8",
    )
    manager = TemplateManager(templates_dir=templates_dir)
    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.get_template_manager", return_value=manager),
        patch("espansr.integrations.espanso.validate_all", return_value=[]),
        patch("espansr.integrations.espanso.is_windows", return_value=False),
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
    ):
        assert sync_to_espanso() is True

    generated = yaml.safe_load((match_dir / "espansr.yml").read_text(encoding="utf-8"))
    assert len(generated["matches"]) == 1
    match = generated["matches"][0]
    assert set(match.keys()) == {"trigger", "replace"}
    assert match["trigger"] == ":cap"
    assert match["replace"] == "expanded text"
    raw = (match_dir / "espansr.yml").read_text(encoding="utf-8")
    for token in (
        "capability_id",
        "intent_tags",
        "accepts",
        "produces",
        "use_when",
        "avoid_when",
        "output_contract",
        "workflow",
    ):
        assert token not in raw, token
