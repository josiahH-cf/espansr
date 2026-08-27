"""Regression tests for defects found during adversarial review.

Each test pins a fix: packet round-trips survive Markdown headings and
YAML-ambiguous scalars, packet IDs can never steer writes outside the packets
directory, non-UTF-8 files fail cleanly instead of crashing, saved packet IDs
outrank same-named working-directory files, the packet dialog preserves
sections it does not display, and check-output resolves bundled templates by
name.
"""

import argparse
from unittest.mock import patch

import pytest

from espansr.core.packets import (
    Packet,
    PacketError,
    load_packet,
    parse_packet,
    render_packet,
    save_packet,
)

# ── Round-trip robustness ────────────────────────────────────────────────────


def test_section_bodies_with_markdown_headings_survive_roundtrip():
    packet = Packet(
        title="Heading safety",
        artifact_type="evidence-report",
        sections={
            "Objective": "Ship the feature.\n\n# Decisions\nsplit-off content stays here",
            "Decisions": "Use approach B.",
        },
        notes="A note with\n# Notes\ninside it.",
    )
    parsed = parse_packet(render_packet(packet))
    assert parsed.sections["Objective"] == (
        "Ship the feature.\n\n# Decisions\nsplit-off content stays here"
    )
    assert parsed.sections["Decisions"] == "Use approach B."
    assert parsed.notes == "A note with\n# Notes\ninside it."
    # A second render/parse cycle is also stable.
    again = parse_packet(render_packet(parsed))
    assert again.sections == parsed.sections
    assert again.notes == parsed.notes


def test_yaml_ambiguous_scalars_survive_roundtrip():
    packet = Packet(
        title="No",
        artifact_type="evidence-report",
        created_from="007",
        requested_outcome="yes",
        sections={"Objective": "x"},
    )
    parsed = parse_packet(render_packet(packet))
    assert parsed.title == "No"
    assert parsed.created_from == "007"
    assert parsed.requested_outcome == "yes"


def test_structured_unknown_front_matter_survives_roundtrip():
    text = render_packet(Packet(title="Extras", artifact_type="gap-review"))
    text = text.replace("espansr_packet: 1", "espansr_packet: 1\nrelated: [gaps, verify]")
    parsed = parse_packet(text)
    assert parsed.extra["related"] == ["gaps", "verify"]
    reparsed = parse_packet(render_packet(parsed))
    assert reparsed.extra["related"] == ["gaps", "verify"]


def test_duplicate_section_headings_never_lose_content():
    text = (
        "---\nespansr_packet: 1\nartifact_type: evidence-report\n---\n\n"
        "# Objective\n\nfirst part\n\n# Objective\n\nsecond part\n"
    )
    parsed = parse_packet(text)
    assert "first part" in parsed.sections["Objective"]
    assert "second part" in parsed.sections["Objective"]


# ── Packet-ID safety ─────────────────────────────────────────────────────────


def test_crafted_packet_id_cannot_escape_packets_dir(tmp_path):
    packets_dir = tmp_path / "packets"
    outside_target = tmp_path / "templates" / "evil.md"
    packet = Packet(
        title="Traversal attempt",
        artifact_type="evidence-report",
        packet_id="../templates/evil",
    )
    path = save_packet(packet, packets_dir=packets_dir)
    assert path.parent == packets_dir
    assert not outside_target.exists()
    assert packet.packet_id == "traversal_attempt"


def test_reopened_packet_with_crafted_id_saves_inside_packets_dir(tmp_path):
    packets_dir = tmp_path / "packets"
    packets_dir.mkdir(parents=True)
    crafted = render_packet(Packet(title="Crafted", artifact_type="gap-review"))
    crafted = crafted.replace("espansr_packet: 1", 'espansr_packet: 1\nid: "../escape"')
    crafted_path = packets_dir / "crafted.md"
    crafted_path.write_text(crafted, encoding="utf-8")

    reopened = load_packet(crafted_path)
    saved = save_packet(reopened, packets_dir=packets_dir)
    assert saved.parent == packets_dir
    assert not (tmp_path / "escape.md").exists()


# ── Clean failures on unreadable files ───────────────────────────────────────


def test_load_packet_raises_packet_error_on_non_utf8(tmp_path):
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe garbage")
    with pytest.raises(PacketError):
        load_packet(bad)


def test_cli_check_output_handles_non_utf8_file(tmp_path, capsys):
    from pathlib import Path

    from espansr.__main__ import cmd_check_output

    root = Path(__file__).resolve().parents[1]
    bad = tmp_path / "bad.txt"
    bad.write_bytes(b"\xff\xfe garbage")
    args = argparse.Namespace(template=":feature", path=str(bad), json=False)
    with patch("espansr.__main__.get_templates_dir", return_value=root / "templates"):
        rc = cmd_check_output(args)
    assert rc == 3
    assert "cannot read" in capsys.readouterr().out.lower()


def test_cli_packet_validate_handles_non_utf8_file(tmp_path, capsys):
    from espansr.__main__ import cmd_packet

    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe garbage")
    rc = cmd_packet(argparse.Namespace(packet_action="validate", target=str(bad)))
    assert rc == 1
    assert "cannot read" in capsys.readouterr().out.lower()


# ── Resolution order and lookup ──────────────────────────────────────────────


def test_cli_packet_show_prefers_saved_packet_over_cwd_file(tmp_path, monkeypatch, capsys):
    from espansr.__main__ import cmd_packet

    packets_dir = tmp_path / "packets"
    save_packet(
        Packet(title="Notes", artifact_type="gap-review", sections={"Objective": "the packet"}),
        packets_dir=packets_dir,
    )
    workdir = tmp_path / "cwd"
    workdir.mkdir()
    (workdir / "notes").write_text("an unrelated working-directory file", encoding="utf-8")
    monkeypatch.chdir(workdir)

    with patch("espansr.__main__.get_packets_dir", return_value=packets_dir):
        rc = cmd_packet(argparse.Namespace(packet_action="show", target="notes"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "the packet" in out
    assert "unrelated working-directory file" not in out


def test_cli_check_output_resolves_bundled_template_by_name(tmp_path, capsys):
    from espansr.__main__ import cmd_check_output

    empty_live = tmp_path / "live"
    empty_live.mkdir()
    out_file = tmp_path / "out.txt"
    out_file.write_text("unstructured", encoding="utf-8")
    args = argparse.Namespace(template="Feature", path=str(out_file), json=False)
    with patch("espansr.__main__.get_templates_dir", return_value=empty_live):
        rc = cmd_check_output(args)
    # Resolved by bundled template *name* and failed the contract (not rc 3).
    assert rc == 1


# ── Dialog preservation of undisplayed sections ──────────────────────────────


def test_packet_dialog_preserves_unknown_sections_on_resave(tmp_path):
    pytest.importorskip("PyQt6")
    from espansr.ui.packet_dialog import PacketDialog

    packets_dir = tmp_path / "packets"
    packets_dir.mkdir(parents=True)
    original = render_packet(
        Packet(title="With extras", artifact_type="gap-review", sections={"Objective": "o"})
    )
    original += "# Risks\n\nhand-added risk section\n"
    path = packets_dir / "with_extras.md"
    path.write_text(original, encoding="utf-8")

    dialog = PacketDialog(packets_dir=packets_dir)
    assert dialog.load_packet_file(path)
    dialog._save()

    resaved = load_packet(path)
    assert resaved.sections.get("Risks") == "hand-added risk section"
    assert resaved.sections.get("Objective") == "o"
