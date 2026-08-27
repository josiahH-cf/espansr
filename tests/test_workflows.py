"""Workflow-manifest acceptance checks (ARCH-03, ARCH-04, ARCH-11, BEH-03/04/15/16).

Workflow topology lives only in manifest files under ``templates/_meta/workflows``.
Manifests describe optional relationships between capability IDs. They never own
user state, never require a current step, and never execute anything.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLED_WORKFLOWS_DIR = ROOT / "templates" / "_meta" / "workflows"
TEMPLATES_DIR = ROOT / "templates"


def _manifest_data(name: str) -> dict:
    return {
        "workflow_schema": 1,
        "id": name,
        "name": name.replace("-", " ").title(),
        "description": "test workflow",
        "entry_points": ["a"],
        "nodes": [{"capability": "a"}, {"capability": "b"}],
        "edges": [{"source": "a", "target": "b", "label": "go"}],
    }


# ── ARCH-04: non-linear graph model ──────────────────────────────────────────


def test_manifest_supports_branches_merges_and_cycles():
    """Cycles, branches, and merges validate cleanly (no acyclicity rule)."""
    from espansr.core.workflows import validate_manifest_data

    data = _manifest_data("cyclic")
    data["nodes"] = [{"capability": n} for n in ("a", "b", "c")]
    data["entry_points"] = ["a", "b", "c"]
    data["edges"] = [
        {"source": "a", "target": "b", "label": "forward"},
        {"source": "b", "target": "a", "label": "revisit"},
        {"source": "a", "target": "c", "label": "branch"},
        {"source": "b", "target": "c", "label": "merge"},
        {"source": "c", "target": "c", "label": "self"},
    ]
    assert validate_manifest_data(data) == []


def test_manifest_supports_multiple_entry_points():
    from espansr.core.workflows import WorkflowManifest, validate_manifest_data

    data = _manifest_data("multi-entry")
    data["entry_points"] = ["a", "b"]
    assert validate_manifest_data(data) == []
    manifest = WorkflowManifest.from_dict(data)
    assert manifest.entry_points == ["a", "b"]


def test_manifest_rejects_structural_errors():
    """Each structural defect produces a validation error naming the problem."""
    from espansr.core.workflows import validate_manifest_data

    missing_entry = _manifest_data("bad-entry")
    missing_entry["entry_points"] = ["ghost"]
    assert any("ghost" in e for e in validate_manifest_data(missing_entry))

    dangling_edge = _manifest_data("bad-edge")
    dangling_edge["edges"] = [{"source": "a", "target": "ghost", "label": "x"}]
    assert any("ghost" in e for e in validate_manifest_data(dangling_edge))

    dup_nodes = _manifest_data("dup-nodes")
    dup_nodes["nodes"] = [{"capability": "a"}, {"capability": "a"}]
    assert any("duplicate" in e.lower() for e in validate_manifest_data(dup_nodes))

    bad_schema = _manifest_data("bad-schema")
    bad_schema["workflow_schema"] = 99
    assert any("schema" in e.lower() for e in validate_manifest_data(bad_schema))

    no_id = _manifest_data("no-id")
    no_id["id"] = ""
    assert validate_manifest_data(no_id)


def test_manifest_rejects_state_and_execution_claims():
    """A manifest may not own current-step state or claim to execute actions."""
    from espansr.core.workflows import validate_manifest_data

    stateful = _manifest_data("stateful")
    stateful["current_node"] = "a"
    assert any("current" in e.lower() for e in validate_manifest_data(stateful))

    executing = _manifest_data("executing")
    executing["edges"][0]["command"] = "rm -rf /"
    assert any("execut" in e.lower() for e in validate_manifest_data(executing))

    scripted = _manifest_data("scripted")
    scripted["exec"] = "os.system('x')"
    assert any("execut" in e.lower() for e in validate_manifest_data(scripted))


def test_catalog_rejects_duplicate_workflow_ids(tmp_path):
    from espansr.core.workflows import load_workflow_catalog

    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "one.json").write_text(json.dumps(_manifest_data("same-id")), encoding="utf-8")
    (wf_dir / "two.json").write_text(json.dumps(_manifest_data("same-id")), encoding="utf-8")

    catalog = load_workflow_catalog([wf_dir])
    assert len(catalog.workflows) == 1
    assert any("same-id" in e for e in catalog.errors)


def test_catalog_reports_dangling_capability_references(tmp_path):
    from espansr.core.workflows import load_workflow_catalog, validate_catalog

    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "wf.json").write_text(json.dumps(_manifest_data("dangling")), encoding="utf-8")
    catalog = load_workflow_catalog([wf_dir])
    errors = validate_catalog(catalog, known_capability_ids={"a"})
    assert any("b" in e for e in errors)
    assert validate_catalog(catalog, known_capability_ids={"a", "b"}) == []


def test_invalid_manifest_is_excluded_but_reported(tmp_path):
    from espansr.core.workflows import load_workflow_catalog

    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "broken.json").write_text("{not json", encoding="utf-8")
    good = _manifest_data("good")
    (wf_dir / "good.json").write_text(json.dumps(good), encoding="utf-8")

    catalog = load_workflow_catalog([wf_dir])
    assert [w.id for w in catalog.workflows] == ["good"]
    assert any("broken.json" in e for e in catalog.errors)


# ── ARCH-03: single authoritative topology source ────────────────────────────


def test_bundled_templates_do_not_duplicate_workflow_topology():
    """Bundled prompt notes keep next_triggers empty; edges live in manifests."""
    for path in TEMPLATES_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert (
            data.get("next_triggers", []) == []
        ), f"{path.name} duplicates workflow topology in next_triggers"


def test_graph_queries_derive_neighbors_from_manifests(tmp_path):
    """Outgoing/incoming neighbors come from manifests at runtime."""
    from espansr.core.workflows import load_workflow_catalog

    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "wf.json").write_text(json.dumps(_manifest_data("neighbors")), encoding="utf-8")
    catalog = load_workflow_catalog([wf_dir])

    outgoing = catalog.outgoing("a")
    assert [(wf.id, edge.target, edge.label) for wf, edge in outgoing] == [("neighbors", "b", "go")]
    incoming = catalog.incoming("b")
    assert [(wf.id, edge.source) for wf, edge in incoming] == [("neighbors", "a")]
    assert [wf.id for wf in catalog.workflows_for("a")] == ["neighbors"]
    assert catalog.workflows_for("ghost") == []


# ── ARCH-11: seed workflows ──────────────────────────────────────────────────


def _load_bundled_workflow(workflow_id: str) -> dict:
    assert BUNDLED_WORKFLOWS_DIR.is_dir(), "bundled workflow manifest dir missing"
    for path in BUNDLED_WORKFLOWS_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("id") == workflow_id:
            return data
    raise AssertionError(f"bundled workflow {workflow_id} not found")


def _edge_set(data: dict) -> set:
    return {(e["source"], e["target"]) for e in data["edges"]}


def test_wf_research_manifest_matches_contract():
    data = _load_bundled_workflow("evidence-research-cycle")
    nodes = {n["capability"] for n in data["nodes"]}
    assert nodes == {
        "research-report",
        "gap-review",
        "visual-workflow",
        "html-help-doc",
        "context-reset",
    }
    assert set(data["entry_points"]) == nodes

    edges = _edge_set(data)
    required = {
        ("research-report", "gap-review"),
        ("research-report", "visual-workflow"),
        ("research-report", "html-help-doc"),
        ("gap-review", "research-report"),
        ("gap-review", "visual-workflow"),
        ("gap-review", "html-help-doc"),
    }
    required |= {("context-reset", n) for n in nodes - {"context-reset"}}
    assert required <= edges

    # Every edge carries a human-readable label.
    assert all(e.get("label") for e in data["edges"])


def test_wf_feature_manifest_matches_contract():
    data = _load_bundled_workflow("feature-delivery-cycle")
    nodes = {n["capability"] for n in data["nodes"]}
    assert nodes == {
        "goal-refinement",
        "research-report",
        "gap-review",
        "human-litmus",
        "feature-handoff",
        "verification",
        "feedback-apply",
        "context-reset",
    }
    assert set(data["entry_points"]) == nodes

    edges = _edge_set(data)
    required = {
        ("goal-refinement", "research-report"),
        ("goal-refinement", "gap-review"),
        ("goal-refinement", "feature-handoff"),
        ("research-report", "gap-review"),
        ("research-report", "feature-handoff"),
        ("gap-review", "research-report"),
        ("gap-review", "human-litmus"),
        ("gap-review", "feature-handoff"),
        ("human-litmus", "feature-handoff"),
        ("feature-handoff", "verification"),
        ("verification", "feedback-apply"),
        ("feedback-apply", "verification"),
    }
    required |= {("context-reset", n) for n in nodes - {"context-reset"}}
    assert required <= edges
    assert all(e.get("label") for e in data["edges"])


def test_seed_workflows_validate_against_bundled_capabilities():
    """Seed manifests load, validate, and reference only real capability IDs."""
    from espansr.core.capabilities import effective_capability_id
    from espansr.core.templates import TemplateManager
    from espansr.core.workflows import load_workflow_catalog, validate_catalog

    catalog = load_workflow_catalog([BUNDLED_WORKFLOWS_DIR])
    assert catalog.errors == []
    assert {w.id for w in catalog.workflows} >= {
        "evidence-research-cycle",
        "feature-delivery-cycle",
    }

    manager = TemplateManager(templates_dir=TEMPLATES_DIR)
    known = {effective_capability_id(t) for t in manager.list_all()}
    assert validate_catalog(catalog, known_capability_ids=known) == []


def test_seed_workflow_cycles_validate_successfully():
    """BEH-04: gap-review → research-report revisit cycles are valid."""
    data = _load_bundled_workflow("evidence-research-cycle")
    edges = _edge_set(data)
    assert ("research-report", "gap-review") in edges
    assert ("gap-review", "research-report") in edges


def test_manifests_contain_no_project_state_or_secrets():
    """BEH-15: bundled manifests carry no current-step or completion state."""
    for path in BUNDLED_WORKFLOWS_DIR.glob("*.json"):
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        for forbidden in ("current_node", "current_step", "completed", "state"):
            assert forbidden not in data, f"{path.name} contains {forbidden}"
        for forbidden in ("exec", "command", "shell", "script"):
            assert forbidden not in data, f"{path.name} contains {forbidden}"


def test_workflow_manifests_do_not_reach_espanso_yaml(tmp_path):
    """ARCH-10 support: the _meta dir never becomes a template or a match."""
    from espansr.core.templates import TemplateManager

    templates_dir = tmp_path / "templates"
    wf_dir = templates_dir / "_meta" / "workflows"
    wf_dir.mkdir(parents=True)
    (wf_dir / "wf.json").write_text(json.dumps(_manifest_data("hidden")), encoding="utf-8")
    (templates_dir / "real.json").write_text(
        json.dumps({"name": "Real", "content": "x", "trigger": ":real"}), encoding="utf-8"
    )
    manager = TemplateManager(templates_dir=templates_dir)
    names = [t.name for t in manager.list_all()]
    assert names == ["Real"]
