"""Versioned definition publication; discovery is never an execution claim.

Only canonical definitions supply public metadata. Installed files supply hashes
and parity, never private values. Frozen selections belong to the existing job
serializer, not this publication. No executor, queue or operation state lives here.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from espansr.core.atomic import atomic_copy, atomic_write_bytes
from espansr.core.templates import Template
from espansr.core.workflows import WORKFLOWS_SUBDIR, validate_manifest_data

INTERFACE = "espansr-capability-catalog-v1"
ADAPTER_INTERFACE = "espansr-adapter-v1"
SCHEMA_VERSION = 1
PUBLICATION_PATH = Path("_meta/capabilities.json")
_VARIABLE = re.compile(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")
_REVISION = re.compile(r"[0-9a-f]{40,64}\Z")
_ROUTE_KINDS = {"instruction-skill", "native-tool", "browser-interaction", "other"}
_SECRET = re.compile(
    r"(?:[a-z][a-z0-9+.-]*://[^\s/:@]+:[^\s/@]+@|"
    r"\b(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9]{20,})|"
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)",
    re.IGNORECASE,
)


def canonical_bytes(value: Any) -> bytes:
    """Canonical JSON: formatting is ignored, values (including prose) are exact."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _definition_path(root: Path, relative: str | Path) -> Path:
    root, relative = Path(root), Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("invalid definition path")
    target = root / relative
    if any(
        p.is_symlink() for p in [root, target, *target.parents] if p == root or root in p.parents
    ):
        raise ValueError("linked definition path")
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError("definition outside selected root")
    return target


def source_revision(root: Path) -> str | None:
    """Report a Git revision only for a clean canonical definition set."""
    try:

        def git(*args):
            return subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            ).stdout.strip()

        if git("status", "--porcelain", "--", "."):
            return None
        revision = git("rev-parse", "HEAD")
        return revision if _REVISION.fullmatch(revision) else None
    except (OSError, subprocess.SubprocessError):
        return None


def _read(path: Path) -> tuple[bytes, dict]:
    if path.is_symlink():
        raise ValueError("linked definition")
    raw = path.read_bytes()

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(data, dict):
        raise ValueError("definition must be an object")
    canonical_bytes(data)  # Reject non-finite JSON numbers, too.
    return raw, data


def _public_errors(value: Any) -> list[str]:
    """Reject credential-shaped source material without echoing its values.

    This is a guard, not a claim that arbitrary prose can be classified as
    public. Canonical definitions still follow the repository's public review
    rules. Unknown keys and variable defaults never enter discovery metadata.
    """
    errors = []
    if _SECRET.search(json.dumps(value, ensure_ascii=False)):
        errors.append("credential-shaped source material")
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower() in {"password", "token", "api_key", "cookie", "account_details"}:
                errors.append("private source field")
            errors.extend(_public_errors(item))
    elif isinstance(value, list):
        for item in value:
            errors.extend(_public_errors(item))
    return sorted(set(errors))


def _template_errors(data: dict) -> list[str]:
    errors = []
    for key in ("name", "content", "trigger"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"missing usable {key}")
    for key in ("capability_id", "description", "use_when", "avoid_when", "category", "stage"):
        if key in data and not isinstance(data[key], str):
            errors.append(f"invalid {key}")
    for key in ("accepts", "produces", "intent_tags", "variables"):
        if key in data and not isinstance(data[key], list):
            errors.append(f"invalid {key}")
    for key in ("accepts", "produces", "intent_tags"):
        if isinstance(data.get(key), list) and any(not isinstance(x, str) for x in data[key]):
            errors.append(f"invalid {key} item")
    variables = data.get("variables", [])
    if isinstance(variables, list):
        names = []
        for var in variables:
            if not isinstance(var, dict) or not isinstance(var.get("name"), str):
                errors.append("invalid variable")
            else:
                names.append(var["name"])
        if len(names) != len(set(names)):
            errors.append("duplicate variable")
    if "output_contract" in data and not isinstance(data["output_contract"], dict):
        errors.append("invalid output_contract")
    if "execution" in data:
        route = data["execution"]
        if not isinstance(route, dict) or set(route) - {"kind", "id", "hosts", "clients"}:
            errors.append("invalid execution declaration")
        elif route.get("kind") not in _ROUTE_KINDS or not isinstance(route.get("id"), str):
            errors.append("invalid execution route")
        elif not route["id"].strip():
            errors.append("empty execution route")
        else:
            for key in ("hosts", "clients"):
                if not isinstance(route.get(key, []), list) or any(
                    not isinstance(x, str) or not x for x in route.get(key, [])
                ):
                    errors.append(f"invalid execution {key}")
    return errors


def _projection(path: Path | None, source_raw: bytes, source_data: dict) -> dict:
    if path is None:
        return {"status": "unobserved", "byte_sha256": None, "semantic_sha256": None}
    try:
        raw, data = _read(path)
        same = digest(data) == digest(source_data)
        return {
            "status": "equal" if same else "drift",
            "byte_sha256": _sha(raw),
            "semantic_sha256": digest(data),
            "byte_equal": raw == source_raw,
        }
    except (OSError, ValueError, UnicodeError):
        return {"status": "unavailable", "byte_sha256": None, "semantic_sha256": None}


def build_catalog(
    source_root: Path,
    installed_root: Path | None = None,
    *,
    revision: str | None = None,
) -> dict:
    """Pure deterministic descriptor over canonical definitions and a projection.

    Execution declarations identify routes; observations are deliberately not
    bundled. A consumer resolves availability against its actual host/client
    tool inventory, keyed by exact definition digest, using ``select_entries``.
    """
    source_root = Path(source_root)
    installed_root = Path(installed_root) if installed_root is not None else None
    if revision is not None and not _REVISION.fullmatch(revision):
        raise ValueError("source revision must be a full Git object identity")
    entries = []
    paths = [(p, "template") for p in sorted(source_root.glob("*.json"))]
    paths += [(p, "workflow") for p in sorted((source_root / WORKFLOWS_SUBDIR).glob("*.json"))]
    for path, kind in paths:
        relative = path.relative_to(source_root).as_posix()
        entry = {
            "id": f"{kind}:{path.stem}",
            "kind": kind,
            "path": relative,
            "source_revision": revision,
            "schema_version": SCHEMA_VERSION,
        }
        try:
            _definition_path(source_root, relative)
            raw, data = _read(path)
            errors = _public_errors(data)
            errors += _template_errors(data) if kind == "template" else validate_manifest_data(data)
            entry.update({"source_byte_sha256": _sha(raw), "source_semantic_sha256": digest(data)})
            if errors:
                raise ValueError("; ".join(errors))
            if kind == "template":
                template = Template.from_dict(data, path)
                entry.update(
                    {
                        "template_id": path.stem,
                        "capability_id": template.capability_id or None,
                        "capability_metadata": "explicit" if template.capability_id else "missing",
                        "metadata_gaps": [
                            key
                            for key in (
                                "capability_id",
                                "description",
                                "use_when",
                                "accepts",
                                "produces",
                                "output_contract",
                            )
                            if not data.get(key)
                        ],
                        "name": template.name,
                        "trigger": template.trigger,
                        "category": template.category,
                        "stage": template.stage,
                        "description": template.description,
                        "use_when": template.use_when,
                        "avoid_when": template.avoid_when,
                        "intent_tags": template.intent_tags,
                        "accepts": template.accepts,
                        "produces": template.produces,
                        "output_contract": template.output_contract,
                        "variables": sorted(set(_VARIABLE.findall(template.content))),
                        "variable_contract": [
                            {"name": v.name, "type": v.type, "has_default": bool(v.default)}
                            for v in template.variables
                        ],
                        "execution": {
                            "classification": (
                                "declared-unobserved" if data.get("execution") else "prompt-only"
                            ),
                            "route": data.get("execution"),
                            "availability": "unknown",
                        },
                    }
                )
            else:
                entry.update(
                    {
                        "id": f"workflow:{data['id']}",
                        "workflow_id": data["id"],
                        "name": data["name"],
                        "description": data.get("description", ""),
                        "use_when": "",
                        "accepts": [],
                        "produces": [],
                        "variables": [],
                        "output_contract": {},
                        "entry_points": data["entry_points"],
                        "nodes": data["nodes"],
                        "edges": data.get("edges", []),
                        "execution": {
                            "classification": "declarative-workflow",
                            "route": None,
                            "availability": "not-executable",
                        },
                    }
                )
            entry["installed"] = _projection(
                _definition_path(installed_root, relative) if installed_root is not None else None,
                raw,
                data,
            )
            entry["errors"] = []
            entry["usable"] = True
        except (OSError, ValueError, UnicodeError, TypeError, KeyError, AttributeError):
            # Never echo raw parse errors: they may quote private source text.
            entry.update(
                {
                    "usable": False,
                    "errors": ["invalid or unavailable definition"],
                    "execution": {
                        "classification": "unusable",
                        "route": None,
                        "availability": "unavailable",
                    },
                    "installed": {"status": "unobserved"},
                }
            )
        entries.append(entry)
    # Stable IDs, declared capabilities and triggers must have one owner.
    for key in ("id", "capability_id", "trigger", "workflow_id"):
        owners: dict[str, list] = {}
        for entry in entries:
            if entry.get(key):
                owners.setdefault(entry[key], []).append(entry)
        for group in owners.values():
            if len(group) > 1:
                for entry in group:
                    entry["usable"] = False
                    entry["errors"].append(f"duplicate {key}")
                    entry["execution"]["classification"] = "unusable"
                    entry["execution"]["availability"] = "unavailable"
    known = {
        e.get("capability_id") or e.get("template_id")
        for e in entries
        if e["usable"] and e["kind"] == "template"
    }
    for entry in entries:
        if entry["kind"] == "workflow" and entry["usable"]:
            if any(n["capability"] not in known for n in entry["nodes"]):
                entry["usable"] = False
                entry["errors"].append("workflow references unavailable capability")
                entry["execution"]["classification"] = "unusable"
                entry["execution"]["availability"] = "unavailable"
    valid = bool(entries) and any(e["kind"] == "template" for e in entries)
    valid = valid and all(e["usable"] for e in entries)
    qualified = (
        valid
        and installed_root is not None
        and all(e["installed"]["status"] == "equal" for e in entries)
    )
    catalog = {
        "interface": INTERFACE,
        "schema_version": SCHEMA_VERSION,
        "compatible_adapters": [ADAPTER_INTERFACE],
        "source_revision": revision,
        "definitions_sha256": digest(
            [{"path": e["path"], "digest": e.get("source_semantic_sha256")} for e in entries]
        ),
        "validation": "passed" if valid else "failed",
        "publication": "qualified" if qualified else "unqualified",
        "coverage": {
            "templates": sum(e["kind"] == "template" for e in entries),
            "workflows": sum(e["kind"] == "workflow" for e in entries),
            "unmanaged_installed_templates": (
                len(
                    {p.name for p in installed_root.glob("*.json")}
                    - {p.name for p in source_root.glob("*.json")}
                )
                if installed_root is not None
                else None
            ),
        },
        "entries": entries,
    }
    return {**catalog, "catalog_sha256": digest(catalog)}


def publish_catalog(
    source_root: Path, installed_root: Path, *, revision: str | None = None
) -> dict:
    """Existing install/publish owner calls this after projection writes.

    One atomic envelope contains descriptor and receipt. Invalid or partial
    installs do not replace it. Idempotent replay produces identical bytes.
    This does not install definitions, restart Espanso or claim trigger use.
    """
    catalog = build_catalog(source_root, installed_root, revision=revision)
    if catalog["publication"] != "qualified":
        raise ValueError("catalog unqualified; last complete publication retained")
    atomic_write_bytes(
        _definition_path(installed_root, PUBLICATION_PATH), canonical_bytes(catalog) + b"\n"
    )
    return catalog


def sync_workflow_projection(source_root: Path, installed_root: Path) -> None:
    """Bundled sync owner projects topology, retaining exact overwritten bytes."""
    snapshots = []
    for path in sorted((Path(source_root) / WORKFLOWS_SUBDIR).glob("*.json")):
        raw, data = _read(_definition_path(source_root, path.relative_to(source_root)))
        if validate_manifest_data(data) or _public_errors(data):
            raise ValueError("invalid bundled workflow; publication retained")
        snapshots.append((path.name, raw))
    for name, raw in snapshots:
        target = _definition_path(installed_root, WORKFLOWS_SUBDIR / name)
        if target.is_symlink():
            raise ValueError("linked installed workflow; publication retained")
        if target.exists():
            previous = target.read_bytes()
            if previous == raw:
                continue
            backup = _definition_path(
                installed_root, Path("_versions/wf") / f"{_sha(previous)[:24]}.json"
            )
            if backup.exists():
                if backup.read_bytes() != previous:
                    raise ValueError("workflow backup identity conflict; original retained")
            else:
                atomic_copy(target, backup)
        atomic_write_bytes(target, raw)


def read_publication(installed_root: Path) -> dict:
    """Read an integrity-checked complete publication; never reinterpret schema."""
    _, data = _read(_definition_path(installed_root, PUBLICATION_PATH))
    recorded = data.pop("catalog_sha256", None)
    if (
        data.get("interface") != INTERFACE
        or data.get("schema_version") != SCHEMA_VERSION
        or data.get("compatible_adapters") != [ADAPTER_INTERFACE]
        or data.get("publication") != "qualified"
        or data.get("validation") != "passed"
        or digest(data) != recorded
    ):
        raise ValueError("incompatible or corrupt publication")
    return {**data, "catalog_sha256": recorded}


def inspect_catalog(
    source_root: Path, installed_root: Path, *, revision: str | None = None
) -> dict:
    """Last qualified publication and current drift are separate observations."""
    current = build_catalog(source_root, installed_root, revision=revision)
    try:
        published = read_publication(installed_root)
    except (OSError, ValueError, UnicodeError):
        published = None
    return {
        "current": current,
        "published": published,
        "status": "current" if published == current else "drift" if published else "unavailable",
    }


def select_entries(
    catalog: dict,
    *,
    capability: str | None = None,
    host: str | None = None,
    client: str | None = None,
    inputs: set[str] | None = None,
    intent: str | None = None,
    observations: tuple[dict, ...] = (),
    selected: str | None = None,
) -> list[dict]:
    """Same descriptors for Dot/Console/skills, no ranking or planner.

    Observations are caller-owned runtime evidence, never publication facts.
    A user-selected usable entry bypasses relevance filters, not availability.
    """
    rows = []
    for original in catalog["entries"]:
        entry = copy.deepcopy(original)
        if not entry["usable"]:
            continue
        chosen = selected == entry["id"]
        route = entry["execution"]["route"]
        if not chosen:
            if capability and entry.get("capability_id") != capability:
                continue
            # accepts lists compatible artifact kinds, not a requirement to
            # supply every listed alternative at once (same as popup filters).
            accepts = set(entry.get("accepts", []))
            if inputs is not None and accepts and not accepts.intersection(inputs):
                continue
            if (
                intent
                and intent.casefold()
                not in " ".join(
                    [
                        entry.get("name", ""),
                        entry.get("description", ""),
                        entry.get("use_when", ""),
                        *entry.get("intent_tags", []),
                    ]
                ).casefold()
            ):
                continue
            if route and any(
                value and route.get(key) and value not in route[key]
                for key, value in (("hosts", host), ("clients", client))
            ):
                continue
        if route:
            compatible = not any(
                value and route.get(key) and value not in route[key]
                for key, value in (("hosts", host), ("clients", client))
            )
            observed = (
                compatible
                and host is not None
                and client is not None
                and any(
                    o.get("definition_sha256") == entry["source_semantic_sha256"]
                    and o.get("route") == route
                    and o.get("host") == host
                    and o.get("client") == client
                    and o.get("available") is True
                    for o in observations
                )
            )
            entry["execution"]["availability"] = "available" if observed else "unavailable"
            if observed:
                entry["execution"]["classification"] = "supported-execution"
        rows.append(entry)
    return rows


def freeze_definition(
    catalog: dict,
    entry_id: str,
    definition_root: Path,
    *,
    values: dict[str, str],
    context_binding: dict,
) -> dict:
    """Private job payload: exact definition bytes, variables and caller binding.

    The caller persists this with its existing contextual profile/job; never
    write it into the public catalog. Changes to a later catalog cannot alter
    restart/replay. No external effect happens during selection or rendering.
    """
    entry = next(e for e in catalog["entries"] if e["id"] == entry_id)
    if not entry["usable"]:
        raise ValueError("selection is not a usable definition")
    raw, data = _read(_definition_path(definition_root, entry["path"]))
    expected = entry["installed"].get("byte_sha256")
    if (
        _sha(raw) not in {entry["source_byte_sha256"], expected}
        or digest(data) != entry["source_semantic_sha256"]
    ):
        raise ValueError("definition changed since selection")
    if set(values) != set(entry["variables"]) or any(
        not isinstance(v, str) for v in values.values()
    ):
        raise ValueError("provide exactly the required variable values")
    frozen = {
        "interface": ADAPTER_INTERFACE,
        "catalog_interface": INTERFACE,
        "descriptor": copy.deepcopy(entry),
        "catalog_sha256": catalog["catalog_sha256"],
        "definition_bytes": base64.b64encode(raw).decode("ascii"),
        "digest": _sha(raw),
        "values": copy.deepcopy(values),
        "context_binding": copy.deepcopy(context_binding),
    }
    return {**frozen, "frozen_sha256": digest(frozen)}


def restore_frozen(frozen: dict) -> dict:
    """Restore exact prompt or workflow data without reading current files."""
    payload = {k: v for k, v in frozen.items() if k != "frozen_sha256"}
    raw = base64.b64decode(payload["definition_bytes"], validate=True)
    if (
        payload["interface"] != ADAPTER_INTERFACE
        or digest(payload) != frozen["frozen_sha256"]
        or _sha(raw) != payload["digest"]
    ):
        raise ValueError("frozen selection integrity mismatch")
    definition = json.loads(raw.decode("utf-8"))
    if digest(definition) != payload["descriptor"]["source_semantic_sha256"]:
        raise ValueError("frozen definition lineage mismatch")
    return definition


def render_frozen(frozen: dict) -> str:
    """Replay a persisted private prompt without reading current files."""
    definition = restore_frozen(frozen)
    if frozen["descriptor"]["kind"] != "template":
        raise ValueError("declarative workflow is not a prompt")
    return _VARIABLE.sub(lambda match: frozen["values"][match.group(1)], definition["content"])
