"""Handoff packets: explicit, user-controlled context transport.

A packet carries selected context — objective, evidence, decisions,
assumptions, unknowns, and the requested next outcome — into a fresh model
window or another capability. Packets are Markdown with a small YAML front
matter block, so they stay human-readable and safe to paste anywhere.

Rules the implementation guarantees:

- Rendering a preview never touches disk; only an explicit save persists.
- Saved packets live in a config-owned ``packets/`` directory, a sibling of
  the git-synced template store — never auto-synced, never auto-tracked.
- A packet has no authoritative current-step field; newer user direction and
  current project evidence always outrank packet content.
- Round-trips preserve every supported field, and unknown future front-matter
  keys are carried through untouched (forward compatibility).
- Loading or parsing a packet never mutates templates or workflows.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from espansr.core.config import get_config_dir

PACKET_SCHEMA_VERSION = 1
PACKET_SECTIONS = (
    "Objective",
    "Confirmed facts and evidence",
    "Decisions",
    "Assumptions",
    "Material unknowns",
    "Evidence references",
    "Candidate capabilities",
)
_NOTES_SECTION = "Notes"

# Front matter keys with dedicated Packet fields, in render order.
_KNOWN_FRONT_MATTER = (
    "espansr_packet",
    "id",
    "title",
    "artifact_type",
    "workflow",
    "created_from",
    "requested_outcome",
    "candidates",
    "created",
    "updated",
)

_SECRET_KEY_PATTERN = re.compile(
    r"(secret|token|password|api_?key|credential|private_?key)", re.IGNORECASE
)
_STATE_KEYS = {"current_step", "current_node", "current_capability"}

_BARE_SCALAR = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.,;/()'\-]*$")


class PacketError(ValueError):
    """Raised when packet text cannot be parsed as a packet."""


@dataclass
class Packet:
    """One handoff packet."""

    title: str = ""
    artifact_type: str = ""
    workflow: str = ""
    created_from: str = ""
    requested_outcome: str = ""
    candidates: List[str] = field(default_factory=list)
    sections: Dict[str, str] = field(default_factory=dict)
    notes: str = ""
    packet_id: str = ""
    created: str = ""
    updated: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


def _yaml_scalar(value: Any) -> str:
    """Render one front-matter value as a round-trip-safe YAML scalar.

    A string is written bare only when parsing it back yields the identical
    string (so ``No``, ``yes``, ``null``, ``007`` and friends get quoted
    instead of being coerced by YAML 1.1 resolution). Everything else —
    booleans, numbers, lists, dicts — is written as JSON, which YAML parses
    back into the same structure.
    """
    if isinstance(value, str):
        if _BARE_SCALAR.match(value):
            try:
                if yaml.safe_load(value) == value:
                    return value
            except yaml.YAMLError:
                pass
        return json.dumps(value, ensure_ascii=False)
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return json.dumps(str(value), ensure_ascii=False)


# Body lines that would read as a section heading (or as an escaped one) are
# escaped with a single leading backslash on render and unescaped on parse,
# so pasted Markdown headings survive the round trip instead of splitting
# sections apart.
_HEADING_LINE = re.compile(r"^#\s+\S")
_ESCAPED_HEADING_LINE = re.compile(r"^(\\+)(#)")


def _escape_section_body(body: str) -> str:
    lines = []
    for line in body.splitlines():
        if _HEADING_LINE.match(line) or _ESCAPED_HEADING_LINE.match(line):
            line = "\\" + line
        lines.append(line)
    return "\n".join(lines)


def _unescape_body_line(line: str) -> str:
    if _ESCAPED_HEADING_LINE.match(line):
        return line[1:]
    return line


def render_packet(packet: Packet) -> str:
    """Render *packet* as Markdown with front matter. Never persists anything."""
    lines: List[str] = ["---", f"espansr_packet: {PACKET_SCHEMA_VERSION}"]
    if packet.packet_id:
        lines.append(f"id: {_yaml_scalar(packet.packet_id)}")
    if packet.title:
        lines.append(f"title: {_yaml_scalar(packet.title)}")
    if packet.artifact_type:
        lines.append(f"artifact_type: {_yaml_scalar(packet.artifact_type)}")
    if packet.workflow:
        lines.append(f"workflow: {_yaml_scalar(packet.workflow)}")
    if packet.created_from:
        lines.append(f"created_from: {_yaml_scalar(packet.created_from)}")
    if packet.requested_outcome:
        lines.append(f"requested_outcome: {_yaml_scalar(packet.requested_outcome)}")
    if packet.candidates:
        rendered = ", ".join(_yaml_scalar(c) for c in packet.candidates)
        lines.append(f"candidates: [{rendered}]")
    if packet.created:
        lines.append(f"created: {_yaml_scalar(packet.created)}")
    if packet.updated:
        lines.append(f"updated: {_yaml_scalar(packet.updated)}")
    for key in sorted(packet.extra):
        lines.append(f"{key}: {_yaml_scalar(packet.extra[key])}")
    lines.append("---")
    lines.append("")

    ordered = [s for s in PACKET_SECTIONS if s in packet.sections]
    ordered += [s for s in packet.sections if s not in PACKET_SECTIONS]
    for section in ordered:
        lines.append(f"# {section}")
        lines.append("")
        body = _escape_section_body((packet.sections.get(section) or "").rstrip())
        lines.append(body if body else "(none)")
        lines.append("")
    if packet.notes:
        lines.append(f"# {_NOTES_SECTION}")
        lines.append("")
        lines.append(_escape_section_body(packet.notes.rstrip()))
        lines.append("")
    return "\n".join(lines)


def _split_front_matter(text: str) -> tuple:
    if not text.startswith("---"):
        raise PacketError("packet is missing its front matter block")
    end = text.find("\n---", 3)
    if end == -1:
        raise PacketError("packet front matter block is not closed")
    front = text[4:end]
    body_start = text.find("\n", end + 1)
    body = text[body_start + 1 :] if body_start != -1 else ""
    return front, body


def _parse_sections(body: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    current: Optional[str] = None
    buffer: List[str] = []

    def _commit() -> None:
        if current is None:
            return
        value = "\n".join(buffer).strip()
        if current in sections and sections[current]:
            # A repeated heading never silently overwrites earlier content.
            sections[current] = sections[current] + "\n\n" + value if value else sections[current]
        else:
            sections[current] = value

    for line in body.splitlines():
        heading = re.match(r"^#\s+(.+?)\s*$", line)
        if heading:
            _commit()
            current = heading.group(1)
            buffer = []
        elif current is not None:
            buffer.append(_unescape_body_line(line))
    _commit()
    for name, value in list(sections.items()):
        if value == "(none)":
            sections[name] = ""
    return sections


def parse_packet(text: str) -> Packet:
    """Parse packet text. Raises :class:`PacketError` when it is not a packet."""
    front_text, body = _split_front_matter(text)
    try:
        front = yaml.safe_load(front_text)
    except yaml.YAMLError as exc:
        raise PacketError(f"invalid packet front matter: {exc}") from exc
    if not isinstance(front, dict):
        raise PacketError("packet front matter must be a mapping")

    sections = _parse_sections(body)
    notes = sections.pop(_NOTES_SECTION, "")
    candidates_raw = front.get("candidates", [])
    if isinstance(candidates_raw, str):
        candidates = [candidates_raw]
    elif isinstance(candidates_raw, list):
        candidates = [str(c) for c in candidates_raw if c]
    else:
        candidates = []

    extra = {k: v for k, v in front.items() if k not in _KNOWN_FRONT_MATTER}
    return Packet(
        title=str(front.get("title", "") or ""),
        artifact_type=str(front.get("artifact_type", "") or ""),
        workflow=str(front.get("workflow", "") or ""),
        created_from=str(front.get("created_from", "") or ""),
        requested_outcome=str(front.get("requested_outcome", "") or ""),
        candidates=candidates,
        sections=sections,
        notes=notes,
        packet_id=str(front.get("id", "") or ""),
        created=str(front.get("created", "") or ""),
        updated=str(front.get("updated", "") or ""),
        extra=extra,
    )


def validate_packet_text(text: str) -> List[str]:
    """Return every validation error for *text* (empty list = valid packet)."""
    errors: List[str] = []
    try:
        front_text, _body = _split_front_matter(text)
    except PacketError as exc:
        return [str(exc)]
    try:
        front = yaml.safe_load(front_text)
    except yaml.YAMLError as exc:
        return [f"invalid packet front matter: {exc}"]
    if not isinstance(front, dict):
        return ["packet front matter must be a mapping"]

    version = front.get("espansr_packet")
    if version is None:
        errors.append("missing espansr_packet schema declaration")
    elif not isinstance(version, int) or version < 1:
        errors.append(f"invalid espansr_packet schema declaration: {version!r}")
    elif version > PACKET_SCHEMA_VERSION:
        errors.append(
            f"unsupported packet schema version {version} "
            f"(this espansr supports up to {PACKET_SCHEMA_VERSION})"
        )

    if not str(front.get("artifact_type", "") or "").strip():
        errors.append("missing artifact_type declaration")

    for key in front:
        if _SECRET_KEY_PATTERN.search(str(key)):
            errors.append(f"packets may not carry secret fields ('{key}')")
        if str(key) in _STATE_KEYS:
            errors.append(f"packets may not carry authoritative current-step state ('{key}')")

    return errors


# ── Persistence (explicit, user-controlled) ──────────────────────────────────


def get_packets_dir() -> Path:
    """The local packet directory: a config-dir sibling of the template store."""
    return get_config_dir() / "packets"


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9_]", "", (title or "packet").lower().replace(" ", "_"))
    return slug or "packet"


_SAFE_PACKET_ID = re.compile(r"^[a-z0-9_]+$")


def save_packet(
    packet: Packet,
    packets_dir: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Path:
    """Explicitly persist *packet*. Assigns an ID and timestamps on first save."""
    directory = packets_dir if packets_dir is not None else get_packets_dir()
    directory.mkdir(parents=True, exist_ok=True)

    # A packet ID names a file inside the packets directory and nothing else.
    # An ID that arrived from parsed front matter (or anywhere) with characters
    # outside the safe slug alphabet is discarded and re-derived, so a crafted
    # id like "../templates/evil" can never steer the write outside.
    if packet.packet_id and not _SAFE_PACKET_ID.match(packet.packet_id):
        packet.packet_id = ""

    if not packet.packet_id:
        base = _slug(packet.title)
        candidate = base
        counter = 2
        while (directory / f"{candidate}.md").exists():
            candidate = f"{base}_{counter}"
            counter += 1
        packet.packet_id = candidate

    timestamp = (now or datetime.now()).isoformat(timespec="seconds")
    if not packet.created:
        packet.created = timestamp
    packet.updated = timestamp

    path = directory / f"{packet.packet_id}.md"
    path.write_text(render_packet(packet), encoding="utf-8")
    return path


def load_packet(path: Path) -> Packet:
    """Load one saved packet. Raises :class:`PacketError` on invalid content."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PacketError(f"cannot read packet {path}: {exc}") from exc
    return parse_packet(text)


def list_packets(packets_dir: Optional[Path] = None) -> List[Path]:
    """List saved packet files, sorted by filename for stable output."""
    directory = packets_dir if packets_dir is not None else get_packets_dir()
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.md"))


def delete_packet(path: Path) -> bool:
    """Explicitly delete one packet file. Never touches anything else."""
    path = Path(path)
    if not path.exists():
        return False
    try:
        path.unlink()
        return True
    except OSError:
        return False
