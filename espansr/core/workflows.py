"""Workflow manifests: the single authoritative home for process topology.

A workflow is an optional directed graph describing useful relationships among
capabilities. Manifests are plain JSON files under ``_meta/workflows`` — the
bundled set ships beside the bundled templates, and users may add their own
under the live template store's ``_meta/workflows`` (which stays local-only:
``_meta/`` is gitignored by remote template sync).

Graph semantics: multiple entry points, branches, merges, and cycles are all
valid; acyclicity is never required. A manifest never owns user state — it may
not declare a current step, completion state, or any executable action — and
no node ever loses direct invocability by appearing in a workflow.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from espansr.core.config import get_templates_dir
from espansr.core.templates import get_bundled_templates_dir

WORKFLOW_SCHEMA_VERSION = 1
WORKFLOWS_SUBDIR = Path("_meta") / "workflows"

# Keys that would turn a declarative manifest into state or an action claim.
_STATE_KEYS = {"current_node", "current_step", "completed", "state"}
_EXECUTION_KEYS = {"exec", "command", "shell", "script", "run"}


@dataclass(frozen=True)
class WorkflowNode:
    """One capability's membership in a workflow."""

    capability: str
    role: str = ""


@dataclass(frozen=True)
class WorkflowEdge:
    """A directed, labeled relationship between two capabilities."""

    source: str
    target: str
    label: str = ""
    artifact: str = ""  # Optional artifact-compatibility hint


@dataclass
class WorkflowManifest:
    """A validated workflow manifest."""

    id: str
    name: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    nodes: List[WorkflowNode] = field(default_factory=list)
    edges: List[WorkflowEdge] = field(default_factory=list)
    notes: str = ""
    schema_version: int = WORKFLOW_SCHEMA_VERSION

    def node_ids(self) -> List[str]:
        return [node.capability for node in self.nodes]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowManifest":
        nodes = [
            WorkflowNode(
                capability=str(n.get("capability", "")),
                role=str(n.get("role", "") or ""),
            )
            for n in data.get("nodes", [])
            if isinstance(n, dict)
        ]
        edges = [
            WorkflowEdge(
                source=str(e.get("source", "")),
                target=str(e.get("target", "")),
                label=str(e.get("label", "") or ""),
                artifact=str(e.get("artifact", "") or ""),
            )
            for e in data.get("edges", [])
            if isinstance(e, dict)
        ]
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            description=str(data.get("description", "") or ""),
            tags=[str(t) for t in data.get("tags", []) if t],
            entry_points=[str(p) for p in data.get("entry_points", []) if p],
            nodes=nodes,
            edges=edges,
            notes=str(data.get("notes", "") or ""),
            schema_version=data.get("workflow_schema", WORKFLOW_SCHEMA_VERSION),
        )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "workflow_schema": self.schema_version,
            "id": self.id,
            "name": self.name,
        }
        if self.description:
            d["description"] = self.description
        if self.tags:
            d["tags"] = self.tags
        d["entry_points"] = self.entry_points
        d["nodes"] = [
            {"capability": n.capability, **({"role": n.role} if n.role else {})} for n in self.nodes
        ]
        d["edges"] = [
            {
                "source": e.source,
                "target": e.target,
                **({"label": e.label} if e.label else {}),
                **({"artifact": e.artifact} if e.artifact else {}),
            }
            for e in self.edges
        ]
        if self.notes:
            d["notes"] = self.notes
        return d


def _find_forbidden_keys(value: Any, forbidden: set) -> List[str]:
    """Recursively collect forbidden keys anywhere in a JSON structure."""
    found: List[str] = []
    if isinstance(value, dict):
        for key, sub in value.items():
            if key in forbidden:
                found.append(key)
            found.extend(_find_forbidden_keys(sub, forbidden))
    elif isinstance(value, list):
        for item in value:
            found.extend(_find_forbidden_keys(item, forbidden))
    return found


def validate_manifest_data(data: Any) -> List[str]:
    """Validate one raw manifest object. Returns every error, not just the first."""
    errors: List[str] = []
    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]

    schema = data.get("workflow_schema")
    if schema != WORKFLOW_SCHEMA_VERSION:
        errors.append(
            f"unsupported workflow schema version {schema!r} "
            f"(expected {WORKFLOW_SCHEMA_VERSION})"
        )

    workflow_id = data.get("id", "")
    if not isinstance(workflow_id, str) or not workflow_id.strip():
        errors.append("missing workflow id")
    if not isinstance(data.get("name", ""), str) or not data.get("name", "").strip():
        errors.append("missing workflow name")

    nodes = data.get("nodes", [])
    if not isinstance(nodes, list) or not nodes:
        errors.append("manifest declares no nodes")
        nodes = []
    node_ids: List[str] = []
    for node in nodes:
        if not isinstance(node, dict) or not str(node.get("capability", "")).strip():
            errors.append("every node needs a capability id")
            continue
        node_ids.append(str(node["capability"]))
    for node_id in {n for n in node_ids if node_ids.count(n) > 1}:
        errors.append(f"duplicate node identity: {node_id}")

    node_set = set(node_ids)
    entry_points = data.get("entry_points", [])
    if not isinstance(entry_points, list) or not entry_points:
        errors.append("manifest declares no entry points")
        entry_points = []
    for entry in entry_points:
        if str(entry) not in node_set:
            errors.append(f"entry point is not a node: {entry}")

    edges = data.get("edges", [])
    if not isinstance(edges, list):
        errors.append("edges must be a list")
        edges = []
    for edge in edges:
        if not isinstance(edge, dict):
            errors.append("every edge must be an object")
            continue
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source not in node_set:
            errors.append(f"edge source is not a node: {source or '(empty)'}")
        if target not in node_set:
            errors.append(f"edge target is not a node: {target or '(empty)'}")
        artifact = edge.get("artifact", "")
        if artifact and not isinstance(artifact, str):
            errors.append(f"invalid artifact hint on edge {source} -> {target}")

    for key in _find_forbidden_keys(data, _STATE_KEYS):
        errors.append(f"manifest may not declare workflow state ('{key}')")
    for key in _find_forbidden_keys(data, _EXECUTION_KEYS):
        errors.append(f"manifest may not claim to execute actions ('{key}')")

    return errors


@dataclass
class WorkflowCatalog:
    """All loaded workflow manifests plus any load/validation errors."""

    workflows: List[WorkflowManifest] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def get(self, workflow_id: str) -> Optional[WorkflowManifest]:
        for workflow in self.workflows:
            if workflow.id == workflow_id:
                return workflow
        return None

    def workflows_for(self, capability_id: str) -> List[WorkflowManifest]:
        """Return every workflow that includes *capability_id* as a node."""
        return [w for w in self.workflows if capability_id in w.node_ids()]

    def outgoing(self, capability_id: str) -> List[Tuple[WorkflowManifest, WorkflowEdge]]:
        """Derived neighbors: edges leaving *capability_id*, with their workflow."""
        return [
            (workflow, edge)
            for workflow in self.workflows
            for edge in workflow.edges
            if edge.source == capability_id
        ]

    def incoming(self, capability_id: str) -> List[Tuple[WorkflowManifest, WorkflowEdge]]:
        """Derived neighbors: edges arriving at *capability_id*."""
        return [
            (workflow, edge)
            for workflow in self.workflows
            for edge in workflow.edges
            if edge.target == capability_id
        ]


def get_bundled_workflows_dir() -> Path:
    """The authoritative location of the bundled workflow manifests."""
    return get_bundled_templates_dir() / WORKFLOWS_SUBDIR


def get_user_workflows_dir() -> Path:
    """Optional user manifests inside the live store (local-only via .gitignore)."""
    return get_templates_dir() / WORKFLOWS_SUBDIR


def get_default_workflow_dirs() -> List[Path]:
    """Manifest search order: bundled topology first, then user additions."""
    return [get_bundled_workflows_dir(), get_user_workflows_dir()]


def load_workflow_catalog(dirs: Optional[Iterable[Path]] = None) -> WorkflowCatalog:
    """Load and validate every manifest from *dirs* (default search order).

    Invalid manifests and duplicate workflow IDs are excluded from the catalog
    and reported in ``errors`` so the rest of the graph keeps working.
    """
    catalog = WorkflowCatalog()
    seen_ids: Dict[str, str] = {}
    for directory in dirs if dirs is not None else get_default_workflow_dirs():
        directory = Path(directory)
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                catalog.errors.append(f"{path.name}: cannot load manifest: {exc}")
                continue
            errors = validate_manifest_data(data)
            if errors:
                catalog.errors.extend(f"{path.name}: {e}" for e in errors)
                continue
            workflow_id = data["id"]
            if workflow_id in seen_ids:
                catalog.errors.append(
                    f"{path.name}: duplicate workflow id {workflow_id} "
                    f"(already loaded from {seen_ids[workflow_id]})"
                )
                continue
            seen_ids[workflow_id] = path.name
            catalog.workflows.append(WorkflowManifest.from_dict(data))
    return catalog


def validate_catalog(
    catalog: WorkflowCatalog,
    known_capability_ids: Optional[set] = None,
) -> List[str]:
    """Cross-check manifests against the known capability IDs.

    A node referencing an unknown capability is a dangling reference. When
    *known_capability_ids* is None the check is skipped (schema-only mode).
    """
    errors: List[str] = []
    if known_capability_ids is None:
        return errors
    for workflow in catalog.workflows:
        for node_id in workflow.node_ids():
            if node_id not in known_capability_ids:
                errors.append(
                    f"workflow {workflow.id}: node references unknown capability " f"'{node_id}'"
                )
    return errors
