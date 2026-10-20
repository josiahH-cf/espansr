"""Catalog publication is a versioned read contract, never an execution engine."""

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from espansr.core.capability_catalog import (
    PUBLICATION_PATH,
    build_catalog,
    canonical_bytes,
    freeze_definition,
    inspect_catalog,
    publish_catalog,
    read_publication,
    render_frozen,
    restore_frozen,
    select_entries,
    sync_workflow_projection,
)
from espansr.core.command_catalog import build_command_catalog
from espansr.core.config import Config
from espansr.core.templates import Template, TemplateManager

ROOT = Path(__file__).resolve().parents[1]
REVISION = "1" * 40


def write(root, name="sample.json", **updates):
    data = {
        "name": "Sample",
        "trigger": ":sample",
        "content": "Consider {{goal}}.",
        "variables": [{"name": "goal", "default": "private local default"}],
        "description": "Turn a goal into a useful plan.",
        "use_when": "Plan an outcome",
        "accepts": ["rough-intent"],
        "produces": ["goal-contract"],
    }
    data.update(updates)
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def projection(tmp_path):
    source, installed = tmp_path / "source", tmp_path / "installed"
    write(source)
    shutil.copytree(source, installed)
    return source, installed


def test_complete_bundled_population_and_truthful_execution():
    catalog = build_catalog(ROOT / "templates")
    assert catalog["validation"] == "passed"
    assert len(catalog["entries"]) == len(list((ROOT / "templates").glob("*.json"))) + len(
        list((ROOT / "templates/_meta/workflows").glob("*.json"))
    )
    templates = [e for e in catalog["entries"] if e["kind"] == "template"]
    assert all(e["execution"]["classification"] == "prompt-only" for e in templates)
    assert any(
        e["capability_metadata"] == "missing" and e["capability_id"] is None for e in templates
    )
    assert all(e["source_byte_sha256"] and e["source_semantic_sha256"] for e in catalog["entries"])


def test_determinism_semantic_parity_and_exact_bytes(projection):
    source, installed = projection
    raw = (installed / "sample.json").read_text(encoding="utf-8")
    (installed / "sample.json").write_text(json.dumps(json.loads(raw), indent=4), encoding="utf-8")
    first = publish_catalog(source, installed, revision=REVISION)
    before = (installed / PUBLICATION_PATH).read_bytes()
    assert publish_catalog(source, installed, revision=REVISION) == first
    assert (installed / PUBLICATION_PATH).read_bytes() == before
    entry = first["entries"][0]
    assert entry["installed"]["status"] == "equal"
    assert not entry["installed"]["byte_equal"]
    assert entry["installed"]["semantic_sha256"] == entry["source_semantic_sha256"]
    assert entry["installed"]["byte_sha256"] != entry["source_byte_sha256"]
    assert read_publication(installed) == first
    assert inspect_catalog(source, installed, revision=REVISION)["status"] == "current"


@pytest.mark.parametrize(
    "failure", ["invalid-source", "partial-install", "drift", "invalid-installed"]
)
def test_failed_update_retains_last_complete_catalog(projection, failure):
    source, installed = projection
    first = publish_catalog(source, installed, revision=REVISION)
    before = (installed / PUBLICATION_PATH).read_bytes()
    if failure == "invalid-source":
        (source / "new.json").write_text("{broken", encoding="utf-8")
    elif failure == "partial-install":
        write(source, "new.json", trigger=":new", capability_id="new")
    elif failure == "drift":
        write(installed, content="A local edit")
    else:
        (installed / "sample.json").write_text("[", encoding="utf-8")
    with pytest.raises(ValueError, match="last complete"):
        publish_catalog(source, installed, revision="2" * 40)
    assert (installed / PUBLICATION_PATH).read_bytes() == before
    assert read_publication(installed) == first
    state = inspect_catalog(source, installed, revision="2" * 40)
    assert state["status"] == "drift"
    assert state["published"] == first


def test_compatible_new_definition_discovered_without_touching_old_selection(projection):
    source, installed = projection
    old = publish_catalog(source, installed)
    frozen = freeze_definition(
        old,
        "template:sample",
        installed,
        values={"goal": r"A \ path {{literal}}"},
        context_binding={"attempt_id": "attempt:1", "source_versions": ["v1"]},
    )
    write(source, content="A new instruction for {{goal}}")
    write(source, "new.json", trigger=":new", capability_id="new")
    shutil.copy2(source / "sample.json", installed / "sample.json")
    shutil.copy2(source / "new.json", installed / "new.json")
    new = publish_catalog(source, installed)
    assert {e["id"] for e in new["entries"]} == {"template:sample", "template:new"}
    # Simulated restart is actual JSON persistence/reload, no current file reads.
    restarted = json.loads(json.dumps(frozen))
    assert render_frozen(restarted) == r"Consider A \ path {{literal}}."
    assert restarted["descriptor"] == old["entries"][0]
    assert restarted["context_binding"] == frozen["context_binding"]
    assert restarted["digest"] == old["entries"][0]["installed"]["byte_sha256"]


def test_freeze_refuses_changed_definition_missing_values_and_corruption(projection):
    source, installed = projection
    catalog = publish_catalog(source, installed)
    with pytest.raises(ValueError, match="required variable"):
        freeze_definition(catalog, "template:sample", source, values={}, context_binding={})
    frozen = freeze_definition(
        catalog, "template:sample", source, values={"goal": "Ship"}, context_binding={}
    )
    frozen["values"]["goal"] = "Different"
    with pytest.raises(ValueError, match="integrity"):
        render_frozen(frozen)
    write(source, content="different")
    with pytest.raises(ValueError, match="changed since"):
        freeze_definition(
            catalog, "template:sample", source, values={"goal": "Ship"}, context_binding={}
        )


def test_private_values_and_installed_only_fields_never_enter_publication(projection):
    source, installed = projection
    # Unknown installed metadata causes explicit drift; it is never exported.
    write(installed, private_notes="private operation contents")
    current = build_catalog(source, installed)
    assert "private operation contents" not in json.dumps(current)
    shutil.copy2(source / "sample.json", installed / "sample.json")
    write(installed, "personal.json", content="private operation contents")
    catalog = publish_catalog(source, installed)
    frozen = freeze_definition(
        catalog,
        "template:sample",
        source,
        values={"goal": "private operation contents"},
        context_binding={},
    )
    assert "private operation contents" in render_frozen(frozen)
    assert "private" not in (installed / PUBLICATION_PATH).read_text(encoding="utf-8")
    assert catalog["coverage"]["unmanaged_installed_templates"] == 1
    assert "personal" not in json.dumps(catalog)


@pytest.mark.parametrize(
    "value", ["https://name:credential@host/path", "ghp_" + "x" * 30, "-----BEGIN PRIVATE KEY-----"]
)
def test_credential_source_is_rejected_without_echo(projection, value):
    source, installed = projection
    before = publish_catalog(source, installed)
    write(source, description=value)
    catalog = build_catalog(source, installed)
    assert catalog["validation"] == "failed"
    assert value not in json.dumps(catalog)
    with pytest.raises(ValueError):
        publish_catalog(source, installed)
    assert read_publication(installed) == before


def test_route_requires_declared_and_exact_observed_host_client_evidence(projection):
    source, installed = projection
    route = {
        "kind": "instruction-skill",
        "id": "sample-skill",
        "hosts": ["windows"],
        "clients": ["codex"],
    }
    write(source, execution=route, capability_id="sample-cap")
    assert (
        Template.from_dict(json.loads((source / "sample.json").read_text())).to_dict()["execution"]
        == route
    )
    catalog = build_catalog(source, installed)
    entry = select_entries(catalog, capability="sample-cap")[0]
    assert entry["execution"]["classification"] == "declared-unobserved"
    assert not select_entries(catalog, host="wsl", client="codex")
    # Explicit choices survive relevance filters, still showing unavailable.
    chosen = select_entries(catalog, host="wsl", intent="unrelated", selected="template:sample")
    assert chosen[0]["execution"]["availability"] == "unavailable"
    observation = {
        "definition_sha256": entry["source_semantic_sha256"],
        "route": route,
        "host": "windows",
        "client": "codex",
        "available": True,
    }
    rows = select_entries(catalog, host="windows", client="codex", observations=(observation,))
    assert rows[0]["execution"]["classification"] == "supported-execution"
    observation["definition_sha256"] = "old"
    assert (
        select_entries(catalog, host="windows", client="codex", observations=(observation,))[0][
            "execution"
        ]["classification"]
        == "declared-unobserved"
    )
    assert catalog["entries"][0]["execution"]["availability"] == "unknown"


def test_relevance_filters_use_declared_metadata_and_keep_same_descriptor(projection):
    source, installed = projection
    catalog = build_catalog(source, installed)
    assert select_entries(catalog, inputs=set()) == []
    assert select_entries(catalog, intent="outcome", inputs={"rough-intent"}) == catalog["entries"]
    assert (
        select_entries(catalog, capability="sample") == []
    )  # Missing explicit metadata stays missing.
    write(source, accepts=["rough-intent", "evidence-report"])
    alternatives = build_catalog(source, installed)
    assert select_entries(alternatives, inputs={"rough-intent"}) == alternatives["entries"]
    assert select_entries(alternatives, inputs={"unrelated-kind"}) == []


def test_duplicate_and_broken_workflow_are_local_unusable_entries(projection):
    source, installed = projection
    write(source, "duplicate.json")
    workflows = source / "_meta/workflows"
    workflows.mkdir(parents=True)
    (workflows / "broken.json").write_text(
        json.dumps(
            {
                "workflow_schema": 1,
                "id": "broken",
                "name": "Broken",
                "nodes": [{"capability": "absent"}],
                "entry_points": ["absent"],
                "edges": [],
            }
        )
    )
    catalog = build_catalog(source, installed)
    assert catalog["validation"] == "failed"
    assert all(not e["usable"] for e in catalog["entries"])


def test_bundled_workflows_project_and_backup_exact_bytes(tmp_path):
    source, installed = ROOT / "templates", tmp_path / "installed"
    shutil.copytree(source, installed)
    target = installed / "_meta/workflows/session-continuity.json"
    target.write_bytes(b"old private topology bytes")
    sync_workflow_projection(source, installed)
    assert target.read_bytes() == (source / "_meta/workflows/session-continuity.json").read_bytes()
    backups = list((installed / "_versions/wf").iterdir())
    assert len(backups) == 1 and backups[0].read_bytes() == b"old private topology bytes"
    assert publish_catalog(source, installed)["publication"] == "qualified"
    sync_workflow_projection(source, installed)
    assert list((installed / "_versions/wf").iterdir()) == backups
    workflow = next(e for e in build_catalog(source)["entries"] if e["kind"] == "workflow")
    frozen = freeze_definition(
        build_catalog(source),
        workflow["id"],
        source,
        values={},
        context_binding={"attempt_id": "exact:1"},
    )
    restored = restore_frozen(json.loads(json.dumps(frozen)))
    assert restored == json.loads((source / workflow["path"]).read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="not a prompt"):
        render_frozen(frozen)


def test_corrupt_or_future_publication_is_not_accepted(projection):
    source, installed = projection
    catalog = publish_catalog(source, installed)
    catalog["schema_version"] = 2
    (installed / PUBLICATION_PATH).write_bytes(canonical_bytes(catalog))
    with pytest.raises(ValueError, match="incompatible"):
        read_publication(installed)
    assert inspect_catalog(source, installed)["status"] == "unavailable"


@pytest.mark.parametrize(
    "bad",
    [
        {"variables": [None]},
        {"execution": {"kind": "shell", "id": "run-me"}},
        {"output_contract": []},
        {"accepts": "anything"},
        {"content": None},
    ],
)
def test_invalid_metadata_is_local_and_never_crashes_discovery(projection, bad):
    source, installed = projection
    write(source, **bad)
    catalog = build_catalog(source, installed)
    assert catalog["validation"] == "failed"
    assert not catalog["entries"][0]["usable"]


def test_duplicate_json_keys_and_path_escape_are_refused(projection):
    source, installed = projection
    catalog = build_catalog(source, installed)
    catalog["entries"][0]["path"] = "../outside.json"
    with pytest.raises(ValueError, match="invalid definition path"):
        freeze_definition(
            catalog, "template:sample", source, values={"goal": "A"}, context_binding={}
        )
    (source / "sample.json").write_text('{"name":"A","name":"B"}', encoding="utf-8")
    assert build_catalog(source)["validation"] == "failed"


def test_atomic_publication_failure_preserves_previous_receipt(projection):
    source, installed = projection
    first = publish_catalog(source, installed)
    with patch("espansr.core.atomic._replace", side_effect=OSError("fixture")):
        with pytest.raises(OSError):
            publish_catalog(source, installed, revision=REVISION)
    assert read_publication(installed) == first
    assert not list((installed / "_meta").glob("*.tmp"))


def test_popup_uses_same_published_descriptor_and_keeps_local_triggers(tmp_path):
    installed = tmp_path / "installed"
    shutil.copytree(ROOT / "templates", installed)
    published = publish_catalog(ROOT / "templates", installed)
    write(installed, "local.json", trigger=":local")
    entries = build_command_catalog(TemplateManager(installed), Config())
    row = next(e for e in entries if e.trigger == ":gaps")
    descriptor = next(e for e in published["entries"] if e.get("trigger") == ":gaps")
    assert row.capability_descriptor == descriptor
    assert next(e for e in entries if e.trigger == ":local").capability_descriptor == {}


def test_catalog_cli_read_only_and_machine_descriptor(projection, capsys):
    from espansr.__main__ import main

    source, installed = projection
    before = {p.relative_to(installed): p.read_bytes() for p in installed.rglob("*.json")}
    with pytest.raises(SystemExit) as exit_info:
        main(["catalog", "--source", str(source), "--installed", str(installed), "--json"])
    assert exit_info.value.code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "unavailable"
    assert output["choices"][0]["id"] == "template:sample"
    assert {p.relative_to(installed): p.read_bytes() for p in installed.rglob("*.json")} == before


def test_publish_owner_qualifies_after_projection_without_execution(projection, tmp_path):
    from espansr.integrations.espanso import sync_to_espanso

    source, installed = projection
    match = tmp_path / "match"
    match.mkdir()
    manager = TemplateManager(installed)
    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match),
        patch("espansr.integrations.espanso.get_template_manager", return_value=manager),
        patch("espansr.integrations.espanso.validate_all", return_value=[]),
        patch("espansr.integrations.espanso.is_windows", return_value=False),
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
    ):
        assert sync_to_espanso(bundled_dir=source)
    assert read_publication(installed)["publication"] == "qualified"
    assert "Consider" in (match / "espansr.yml").read_text(encoding="utf-8")
