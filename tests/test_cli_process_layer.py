"""CLI acceptance checks for the process layer (workflows, packets).

``espansr workflows`` lists, shows, and validates workflow manifests.
``espansr packet`` lists, shows, validates, and deletes handoff packets.
Both are read-only except for the explicit packet delete action, and neither
executes prompts, shells, models, installs, syncs, or network actions.
"""

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
BUNDLED_WORKFLOWS_DIR = ROOT / "templates" / "_meta" / "workflows"


def _packet_text(title="CLI packet"):
    from espansr.core.packets import Packet, render_packet

    return render_packet(
        Packet(
            title=title,
            artifact_type="evidence-report",
            requested_outcome="gap-review",
            sections={"Objective": "test objective"},
        )
    )


# ── espansr workflows ────────────────────────────────────────────────────────


def test_cli_workflows_list_shows_seed_workflows(capsys):
    from espansr.__main__ import cmd_workflows

    with patch(
        "espansr.core.workflows.get_default_workflow_dirs",
        return_value=[BUNDLED_WORKFLOWS_DIR],
    ):
        rc = cmd_workflows(argparse.Namespace(workflows_action="list"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "evidence-research-cycle" in out
    assert "feature-delivery-cycle" in out


def test_cli_workflows_show_renders_entry_points_and_edges(capsys):
    from espansr.__main__ import cmd_workflows

    with patch(
        "espansr.core.workflows.get_default_workflow_dirs",
        return_value=[BUNDLED_WORKFLOWS_DIR],
    ):
        rc = cmd_workflows(
            argparse.Namespace(workflows_action="show", workflow_id="evidence-research-cycle")
        )
    assert rc == 0
    out = capsys.readouterr().out
    assert "research-report" in out
    assert "gap-review" in out
    assert "Challenge the findings independently." in out
    assert "Entry points" in out


def test_cli_workflows_validate_passes_on_seed_manifests(capsys):
    from espansr.__main__ import cmd_workflows

    with patch(
        "espansr.core.workflows.get_default_workflow_dirs",
        return_value=[BUNDLED_WORKFLOWS_DIR],
    ):
        rc = cmd_workflows(argparse.Namespace(workflows_action="validate"))
    assert rc == 0
    assert "valid" in capsys.readouterr().out.lower()


def test_cli_workflows_validate_fails_on_broken_manifest(tmp_path, capsys):
    from espansr.__main__ import cmd_workflows

    wf_dir = tmp_path / "workflows"
    wf_dir.mkdir()
    (wf_dir / "bad.json").write_text(
        json.dumps(
            {
                "workflow_schema": 1,
                "id": "broken",
                "name": "Broken",
                "entry_points": ["ghost"],
                "nodes": [{"capability": "a"}],
                "edges": [],
            }
        ),
        encoding="utf-8",
    )
    with patch("espansr.core.workflows.get_default_workflow_dirs", return_value=[wf_dir]):
        rc = cmd_workflows(argparse.Namespace(workflows_action="validate"))
    assert rc == 1
    assert "ghost" in capsys.readouterr().out


# ── espansr packet ───────────────────────────────────────────────────────────


@pytest.fixture
def packets_dir(tmp_path):
    d = tmp_path / "packets"
    d.mkdir()
    return d


def test_cli_packet_validate_passes_on_valid_packet(tmp_path, capsys):
    from espansr.__main__ import cmd_packet

    path = tmp_path / "packet.md"
    path.write_text(_packet_text(), encoding="utf-8")
    rc = cmd_packet(argparse.Namespace(packet_action="validate", target=str(path)))
    assert rc == 0
    assert "valid" in capsys.readouterr().out.lower()


def test_cli_packet_validate_fails_with_clear_errors(tmp_path, capsys):
    from espansr.__main__ import cmd_packet

    path = tmp_path / "bad.md"
    path.write_text("no front matter at all", encoding="utf-8")
    rc = cmd_packet(argparse.Namespace(packet_action="validate", target=str(path)))
    assert rc == 1
    assert "front matter" in capsys.readouterr().out.lower()


def test_cli_packet_list_and_show_roundtrip(packets_dir, capsys):
    from espansr.__main__ import cmd_packet
    from espansr.core.packets import Packet, save_packet

    save_packet(
        Packet(
            title="Saved packet",
            artifact_type="evidence-report",
            sections={"Objective": "listed"},
        ),
        packets_dir=packets_dir,
    )
    with patch("espansr.__main__.get_packets_dir", return_value=packets_dir):
        rc = cmd_packet(argparse.Namespace(packet_action="list"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "saved" in out.lower() and "evidence-report" in out

    with patch("espansr.__main__.get_packets_dir", return_value=packets_dir):
        rc = cmd_packet(argparse.Namespace(packet_action="show", target="saved_packet"))
    assert rc == 0
    out = capsys.readouterr().out
    assert "listed" in out


def test_cli_packet_delete_removes_only_target(packets_dir, capsys):
    from espansr.__main__ import cmd_packet
    from espansr.core.packets import Packet, save_packet

    keep = save_packet(Packet(title="Keep me", artifact_type="gap-review"), packets_dir=packets_dir)
    save_packet(Packet(title="Drop me", artifact_type="gap-review"), packets_dir=packets_dir)

    with patch("espansr.__main__.get_packets_dir", return_value=packets_dir):
        rc = cmd_packet(argparse.Namespace(packet_action="delete", target="drop_me"))
    assert rc == 0
    assert keep.exists()
    assert [p.stem for p in packets_dir.glob("*.md")] == ["keep_me"]


def test_cli_packet_delete_refuses_paths_outside_packets_dir(packets_dir, tmp_path, capsys):
    """Delete only targets saved packets — never an arbitrary file path."""
    from espansr.__main__ import cmd_packet

    outside = tmp_path / "precious.md"
    outside.write_text("not a packet, must survive", encoding="utf-8")
    with patch("espansr.__main__.get_packets_dir", return_value=packets_dir):
        rc = cmd_packet(argparse.Namespace(packet_action="delete", target=str(outside)))
    assert rc == 1
    assert outside.exists()
    assert "refusing" in capsys.readouterr().out.lower()


def test_cli_packet_show_unknown_returns_error(packets_dir, capsys):
    from espansr.__main__ import cmd_packet

    with patch("espansr.__main__.get_packets_dir", return_value=packets_dir):
        rc = cmd_packet(argparse.Namespace(packet_action="show", target="ghost"))
    assert rc == 1
    assert "not found" in capsys.readouterr().out.lower()


# ── Registration ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("command", ["workflows", "packet", "check-output"])
def test_new_subcommands_registered_with_help(command):
    from espansr.__main__ import main

    with patch("sys.argv", ["espansr", command, "--help"]):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 0


def test_new_subcommands_appear_in_completions():
    from espansr.__main__ import _build_parser
    from espansr.core.completions import build_bash_completion

    script = build_bash_completion(_build_parser())
    for command in ("workflows", "packet", "check-output"):
        assert command in script
