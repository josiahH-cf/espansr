"""Capability-metadata acceptance checks (ARCH-01, ARCH-02, BEH-18).

The capability graph extends templates with additive, backward-compatible
metadata: a stable ``capability_id`` (the contract's stable ID), plain-language
``intent_tags``, ``accepts``/``produces`` artifact types, ``use_when`` /
``avoid_when`` guidance, and an optional ``output_contract``. Existing
user templates without any of this metadata must keep working unchanged.
"""

import json
from pathlib import Path

from espansr.core.templates import Template, TemplateManager, import_template

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "templates"

# Bundled capabilities that must carry stable IDs (workflow node identities).
EXPECTED_BUNDLED_CAPABILITY_IDS = {
    "goal_clarifier.json": "goal-refinement",
    "research_report.json": "research-report",
    "gaps.json": "gap-review",
    "litmus.json": "human-litmus",
    "feature.json": "feature-handoff",
    "verify.json": "verification",
    "feedback.json": "feedback-apply",
    "visual_workflow.json": "visual-workflow",
    "html_help_doc.json": "html-help-doc",
    "context.json": "context-reset",
}


# ── ARCH-02: additive metadata model ─────────────────────────────────────────


def test_template_supports_capability_metadata_fields():
    """The template model accepts the full capability metadata set."""
    template = Template(
        name="Capability",
        content="body",
        trigger=":cap",
        capability_id="capability-demo",
        intent_tags=["do the thing", "demo"],
        accepts=["rough-intent"],
        produces=["evidence-report"],
        use_when="You need the thing done.",
        avoid_when="The thing is already done.",
        output_contract={"schema": 1, "required_sections": ["RESULT"]},
    )
    data = template.to_dict()
    assert data["capability_id"] == "capability-demo"
    assert data["intent_tags"] == ["do the thing", "demo"]
    assert data["accepts"] == ["rough-intent"]
    assert data["produces"] == ["evidence-report"]
    assert data["use_when"] == "You need the thing done."
    assert data["avoid_when"] == "The thing is already done."
    assert data["output_contract"] == {"schema": 1, "required_sections": ["RESULT"]}


def test_capability_metadata_roundtrips_through_save_and_load(tmp_path):
    """Save → load preserves every capability metadata field."""
    manager = TemplateManager(templates_dir=tmp_path)
    template = Template(
        name="Round Trip",
        content="body",
        trigger=":rt",
        capability_id="round-trip",
        intent_tags=["round trip"],
        accepts=["evidence-report"],
        produces=["gap-review"],
        use_when="use",
        avoid_when="avoid",
        output_contract={"schema": 1, "required_markers": [{"pattern": "OK"}]},
    )
    assert manager.save(template)

    loaded = manager.get("Round Trip")
    assert loaded is not None
    assert loaded.capability_id == "round-trip"
    assert loaded.intent_tags == ["round trip"]
    assert loaded.accepts == ["evidence-report"]
    assert loaded.produces == ["gap-review"]
    assert loaded.use_when == "use"
    assert loaded.avoid_when == "avoid"
    assert loaded.output_contract == {"schema": 1, "required_markers": [{"pattern": "OK"}]}


def test_capability_metadata_survives_version_snapshots(tmp_path):
    """create_version() carries the capability metadata in template_data."""
    manager = TemplateManager(templates_dir=tmp_path)
    template = Template(
        name="Versioned",
        content="body",
        trigger=":ver",
        capability_id="versioned-cap",
        intent_tags=["snapshot"],
    )
    assert manager.save(template)
    version = manager.create_version(template, note="check")
    assert version is not None
    assert version.template_data["capability_id"] == "versioned-cap"
    assert version.template_data["intent_tags"] == ["snapshot"]


def test_import_preserves_capability_metadata(tmp_path):
    """import_template keeps every recognized capability metadata field."""
    src = tmp_path / "src" / "cap.json"
    src.parent.mkdir(parents=True)
    src.write_text(
        json.dumps(
            {
                "name": "Imported Cap",
                "content": "body",
                "trigger": ":impcap",
                "capability_id": "imported-cap",
                "intent_tags": ["import"],
                "accepts": ["rough-intent"],
                "produces": ["goal-contract"],
                "use_when": "use",
                "avoid_when": "avoid",
                "output_contract": {"schema": 1},
                "author": "someone",
            }
        ),
        encoding="utf-8",
    )
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    result = import_template(src, manager)
    assert result.template is not None
    saved = json.loads(result.template._path.read_text(encoding="utf-8"))
    assert saved["capability_id"] == "imported-cap"
    assert saved["intent_tags"] == ["import"]
    assert saved["accepts"] == ["rough-intent"]
    assert saved["produces"] == ["goal-contract"]
    assert saved["use_when"] == "use"
    assert saved["avoid_when"] == "avoid"
    assert saved["output_contract"] == {"schema": 1}
    assert "author" not in saved


def test_import_drops_capability_id_owned_by_another_template(tmp_path):
    """Importing a duplicate explicit capability ID conservatively clears it."""
    manager = TemplateManager(templates_dir=tmp_path / "templates")
    existing = Template(name="Owner", content="x", trigger=":own", capability_id="owned-cap")
    assert manager.save(existing)

    src = tmp_path / "src" / "dup.json"
    src.parent.mkdir(parents=True)
    src.write_text(
        json.dumps(
            {
                "name": "Duplicate",
                "content": "y",
                "trigger": ":dup",
                "capability_id": "owned-cap",
            }
        ),
        encoding="utf-8",
    )
    result = import_template(src, manager)
    assert result.template is not None
    saved = json.loads(result.template._path.read_text(encoding="utf-8"))
    assert saved.get("capability_id", "") == ""


def test_malformed_capability_metadata_is_normalized_conservatively(tmp_path):
    """Malformed optional metadata coerces to safe defaults instead of crashing."""
    template = Template.from_dict(
        {
            "name": "Messy",
            "content": "body",
            "trigger": ":messy",
            "capability_id": {"nested": True},
            "intent_tags": "single-tag",
            "accepts": [None, "", "evidence-report", 3],
            "produces": {"not": "a list"},
            "use_when": ["not", "a", "string"],
            "avoid_when": None,
            "output_contract": "not-a-dict",
        }
    )
    assert template.capability_id == ""
    assert template.intent_tags == ["single-tag"]
    assert template.accepts == ["evidence-report", "3"]
    assert template.produces == []
    assert template.use_when == ""
    assert template.avoid_when == ""
    assert template.output_contract == {}


# ── ARCH-01: stable identity ─────────────────────────────────────────────────


def test_effective_capability_id_prefers_explicit_then_file_stem_then_name(tmp_path):
    """The derived-ID policy is deterministic and documented."""
    from espansr.core.capabilities import effective_capability_id

    explicit = Template(name="X", content="c", trigger=":x", capability_id="explicit-id")
    assert effective_capability_id(explicit) == "explicit-id"

    manager = TemplateManager(templates_dir=tmp_path)
    saved = Template(name="My Saved Template", content="c", trigger=":mst")
    assert manager.save(saved)
    loaded = manager.get("My Saved Template")
    assert effective_capability_id(loaded) == "my_saved_template"

    unsaved = Template(name="Never Saved", content="c", trigger=":ns")
    assert effective_capability_id(unsaved) == "never_saved"


def test_trigger_rename_does_not_change_capability_identity(tmp_path):
    """Renaming a trigger keeps the stable capability ID intact."""
    from espansr.core.capabilities import effective_capability_id

    manager = TemplateManager(templates_dir=tmp_path)
    template = Template(
        name="Renamable", content="c", trigger=":before", capability_id="stable-cap"
    )
    assert manager.save(template)

    loaded = manager.get("Renamable")
    loaded.trigger = ":after"
    assert manager.save(loaded)

    reloaded = manager.get("Renamable")
    assert reloaded.trigger == ":after"
    assert effective_capability_id(reloaded) == "stable-cap"


def test_bundled_capability_templates_declare_expected_ids():
    """Every workflow-node capability carries its stable bundled ID."""
    for filename, expected_id in EXPECTED_BUNDLED_CAPABILITY_IDS.items():
        path = TEMPLATES_DIR / filename
        assert path.exists(), f"missing bundled capability template {filename}"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data.get("capability_id") == expected_id, filename


def test_bundled_capability_ids_are_unique():
    """No two bundled templates share an explicit capability ID."""
    seen = {}
    for path in TEMPLATES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        cap_id = data.get("capability_id", "")
        if not cap_id:
            continue
        assert cap_id not in seen, f"{path.name} duplicates {seen.get(cap_id)}"
        seen[cap_id] = path.name


def test_bundled_capability_templates_declare_artifacts_and_guidance():
    """Workflow-node capabilities carry discovery metadata, not just IDs."""
    for filename in EXPECTED_BUNDLED_CAPABILITY_IDS:
        data = json.loads((TEMPLATES_DIR / filename).read_text(encoding="utf-8"))
        assert data.get("intent_tags"), f"{filename} needs intent_tags"
        assert data.get("accepts"), f"{filename} needs accepts"
        assert data.get("produces"), f"{filename} needs produces"
        assert data.get("use_when"), f"{filename} needs use_when"
        assert data.get("avoid_when"), f"{filename} needs avoid_when"


def test_duplicate_explicit_capability_ids_surface_in_validation(tmp_path):
    """validate_all warns when two templates declare the same capability ID."""
    from unittest.mock import patch

    from espansr.integrations.validate import validate_all

    a = Template(name="A", content="c", trigger=":aa", capability_id="dup-cap")
    b = Template(name="B", content="c", trigger=":bb", capability_id="dup-cap")

    class _ManagerStub:
        def list_all(self):
            return [a, b]

        def iter_with_triggers(self):
            return iter([a, b])

    with patch("espansr.integrations.validate.get_template_manager", return_value=_ManagerStub()):
        warnings = validate_all()
    assert any("dup-cap" in w.message for w in warnings)


# ── BEH-18: backward compatibility ───────────────────────────────────────────


def test_minimal_user_template_still_loads_and_roundtrips(tmp_path):
    """A template with only name/content/trigger/variables keeps working."""
    manager = TemplateManager(templates_dir=tmp_path)
    path = tmp_path / "simple.json"
    path.write_text(
        json.dumps(
            {
                "name": "Simple",
                "content": "Hello {{who}}",
                "trigger": ":simple",
                "variables": [{"name": "who", "default": "world"}],
            }
        ),
        encoding="utf-8",
    )
    loaded = manager.load(path)
    assert loaded is not None
    assert loaded.capability_id == ""
    assert loaded.intent_tags == []
    assert loaded.accepts == []
    assert loaded.produces == []
    assert loaded.output_contract == {}
    assert loaded.render({}) == "Hello world"
    assert manager.save(loaded)
    saved = json.loads(path.read_text(encoding="utf-8"))
    # No metadata keys are invented for plain templates.
    for key in (
        "capability_id",
        "intent_tags",
        "accepts",
        "produces",
        "use_when",
        "avoid_when",
        "output_contract",
    ):
        assert key not in saved
