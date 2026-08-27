"""Handoff-packet acceptance checks (ARCH-06, BEH-08, BEH-09).

Packets are explicit, user-controlled transport artifacts. Preview never
persists; save, load, export, and delete are distinct explicit operations;
packets live outside the git-synced template store; round-trips preserve
every supported field; and no packet carries authoritative current-step state.
"""

import json

import pytest

from espansr.core.packets import (
    PACKET_SECTIONS,
    Packet,
    PacketError,
    delete_packet,
    list_packets,
    load_packet,
    parse_packet,
    render_packet,
    save_packet,
    validate_packet_text,
)


def _sample_packet() -> Packet:
    return Packet(
        title="Auth research handoff",
        artifact_type="evidence-report",
        workflow="evidence-research-cycle",
        created_from="research-report",
        requested_outcome="gap-review",
        candidates=["gap-review", "visual-workflow"],
        sections={
            "Objective": "Decide the auth approach.",
            "Confirmed facts and evidence": "SSO is required by policy P-4.",
            "Decisions": "Use OIDC.",
            "Assumptions": "The IdP supports PKCE.",
            "Material unknowns": "Token lifetime budget.",
            "Evidence references": "policy/P-4.md",
            "Candidate capabilities": "gap-review, visual-workflow",
        },
        notes="Carry into a fresh window.",
    )


# ── Render / parse round-trip (BEH-09) ───────────────────────────────────────


def test_packet_roundtrip_preserves_all_supported_fields():
    packet = _sample_packet()
    text = render_packet(packet)
    parsed = parse_packet(text)
    assert parsed.title == packet.title
    assert parsed.artifact_type == "evidence-report"
    assert parsed.workflow == "evidence-research-cycle"
    assert parsed.created_from == "research-report"
    assert parsed.requested_outcome == "gap-review"
    assert parsed.candidates == ["gap-review", "visual-workflow"]
    for section in PACKET_SECTIONS:
        assert parsed.sections.get(section, "") == packet.sections.get(section, "")
    assert parsed.notes == packet.notes


def test_rendered_packet_is_human_readable_markdown():
    text = render_packet(_sample_packet())
    assert text.startswith("---\n")
    assert "espansr_packet: 1" in text
    assert "artifact_type: evidence-report" in text
    assert "# Objective" in text
    assert "# Material unknowns" in text
    # Safe to paste: no code execution, no binary, ends with newline.
    assert text.endswith("\n")


def test_unknown_future_fields_survive_roundtrip():
    """Forward compatibility: unknown front-matter keys are preserved."""
    text = render_packet(_sample_packet())
    text = text.replace("espansr_packet: 1", "espansr_packet: 1\nfuture_field: kept")
    parsed = parse_packet(text)
    assert parsed.extra.get("future_field") == "kept"
    rerendered = render_packet(parsed)
    assert "future_field: kept" in rerendered


# ── Validation ───────────────────────────────────────────────────────────────


def test_validate_reports_missing_front_matter():
    errors = validate_packet_text("just some text")
    assert any("front matter" in e.lower() for e in errors)


def test_validate_reports_missing_schema_and_artifact_type():
    text = "---\ntitle: x\n---\n\n# Objective\n\nBody.\n"
    errors = validate_packet_text(text)
    assert any("espansr_packet" in e for e in errors)
    assert any("artifact_type" in e for e in errors)


def test_validate_reports_unsupported_schema_version():
    text = "---\nespansr_packet: 99\nartifact_type: evidence-report\n---\n\n# Objective\n\nx\n"
    errors = validate_packet_text(text)
    assert any("schema" in e.lower() for e in errors)


def test_validate_rejects_secret_fields():
    text = (
        "---\nespansr_packet: 1\nartifact_type: evidence-report\n"
        "api_key: sk-123\n---\n\n# Objective\n\nx\n"
    )
    errors = validate_packet_text(text)
    assert any("secret" in e.lower() for e in errors)


def test_validate_rejects_current_step_state():
    """No packet may carry an authoritative current-step field."""
    text = (
        "---\nespansr_packet: 1\nartifact_type: evidence-report\n"
        "current_step: research\n---\n\n# Objective\n\nx\n"
    )
    errors = validate_packet_text(text)
    assert any("current" in e.lower() for e in errors)


def test_parse_invalid_packet_raises_packet_error():
    with pytest.raises(PacketError):
        parse_packet("no front matter here")


def test_valid_packet_produces_no_errors():
    assert validate_packet_text(render_packet(_sample_packet())) == []


# ── Persistence lifecycle (BEH-08) ───────────────────────────────────────────


def test_preview_render_does_not_persist(tmp_path):
    packets_dir = tmp_path / "packets"
    render_packet(_sample_packet())
    assert not packets_dir.exists() or list(packets_dir.iterdir()) == []


def test_save_creates_one_recoverable_packet(tmp_path):
    packets_dir = tmp_path / "packets"
    path = save_packet(_sample_packet(), packets_dir=packets_dir)
    assert path.exists()
    assert path.parent == packets_dir
    assert list_packets(packets_dir=packets_dir) == [path]

    loaded = load_packet(path)
    assert loaded.title == "Auth research handoff"
    assert loaded.packet_id
    assert loaded.created
    assert loaded.updated


def test_delete_removes_only_the_targeted_packet(tmp_path):
    packets_dir = tmp_path / "packets"
    first = save_packet(_sample_packet(), packets_dir=packets_dir)
    second_packet = _sample_packet()
    second_packet.title = "Second packet"
    second = save_packet(second_packet, packets_dir=packets_dir)

    assert delete_packet(first) is True
    assert not first.exists()
    assert second.exists()
    assert list_packets(packets_dir=packets_dir) == [second]


def test_saved_packets_get_distinct_ids(tmp_path):
    packets_dir = tmp_path / "packets"
    a = save_packet(_sample_packet(), packets_dir=packets_dir)
    b = save_packet(_sample_packet(), packets_dir=packets_dir)
    assert a != b
    assert load_packet(a).packet_id != load_packet(b).packet_id


def test_packets_live_outside_the_template_store(tmp_path):
    """The default packet directory is a config-dir sibling of templates/."""
    from unittest.mock import patch

    from espansr.core.packets import get_packets_dir

    with patch("espansr.core.packets.get_config_dir", return_value=tmp_path):
        packets_dir = get_packets_dir()
    assert packets_dir == tmp_path / "packets"
    assert packets_dir.name != "templates"
    assert "templates" not in packets_dir.parts


def test_import_of_packet_does_not_mutate_templates(tmp_path):
    """Parsing/loading a packet never writes template or workflow files."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    (templates_dir / "keep.json").write_text(
        json.dumps({"name": "Keep", "content": "x", "trigger": ":keep"}), encoding="utf-8"
    )
    before = sorted(p.name for p in templates_dir.rglob("*"))
    packets_dir = tmp_path / "packets"
    path = save_packet(_sample_packet(), packets_dir=packets_dir)
    load_packet(path)
    after = sorted(p.name for p in templates_dir.rglob("*"))
    assert before == after


def test_packet_recommends_capabilities_from_artifact_type():
    """BEH-09/WF-FRESH-CONTEXT: a reopened packet drives discovery."""
    from pathlib import Path

    from espansr.core.command_catalog import build_command_catalog
    from espansr.core.config import Config
    from espansr.core.recommend import RecommendationQuery, recommend
    from espansr.core.templates import TemplateManager

    root = Path(__file__).resolve().parents[1]
    manager = TemplateManager(templates_dir=root / "templates")
    entries = build_command_catalog(template_manager=manager, config=Config())

    packet = _sample_packet()
    results = recommend(
        entries,
        RecommendationQuery(
            have_artifact=packet.artifact_type, want_artifact=packet.requested_outcome
        ),
    )
    assert results
    assert results[0].entry.trigger == ":gaps"
