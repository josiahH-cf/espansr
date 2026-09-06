"""CLI handler paths in ``espansr.__main__`` that had no direct coverage.

Every test runs against the per-test config directory the conftest fixtures
provide and stubs only the collaborators that would otherwise reach a real
git remote, Espanso, or the installer.
"""

import argparse
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

from espansr.core.config import get_templates_dir
from espansr.core.packets import Packet, get_packets_dir, save_packet
from espansr.core.remote import RemoteConflictError, RemoteError
from espansr.core.workflows import WorkflowCatalog


def _ns(**kwargs) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def _write_template(directory: Path, filename: str, data: dict) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / filename
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ── remote / push / pull ─────────────────────────────────────────────────────


def test_cmd_remote_set_status_remove_roundtrip(tmp_path, capsys):
    """set, status, remove drive a real RemoteManager over the isolated store."""
    from espansr.__main__ import cmd_remote

    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    store = get_templates_dir()

    assert cmd_remote(_ns(remote_action="set", url=str(bare))) == 0
    assert f"[ok]   Remote set to {bare}" in capsys.readouterr().out
    assert (store / ".git").is_dir()

    assert cmd_remote(_ns(remote_action="status")) == 0
    status_out = capsys.readouterr().out
    assert f"Remote URL:  {bare}" in status_out
    assert "Modified:    (clean)" in status_out

    _write_template(store, "draft.json", {"name": "Draft", "content": "d"})
    assert cmd_remote(_ns(remote_action="status")) == 0
    assert "Modified:    draft.json" in capsys.readouterr().out

    assert cmd_remote(_ns(remote_action="remove")) == 0
    assert "[ok]   Remote removed. Local templates preserved." in capsys.readouterr().out
    assert not (store / ".git").exists()
    assert (store / "draft.json").exists()

    assert cmd_remote(_ns(remote_action="status")) == 0
    assert "No remote configured. Run: espansr remote set <git-url>" in capsys.readouterr().out


def test_cmd_remote_without_action_prints_usage_rc1(capsys):
    from espansr.__main__ import cmd_remote

    assert cmd_remote(_ns(remote_action=None)) == 1
    assert capsys.readouterr().out.strip() == "Usage: espansr remote {set,status,remove}"


def test_cmd_push_maps_remote_error_to_rc1(capsys):
    from espansr.__main__ import cmd_push

    with patch("espansr.core.remote.RemoteManager") as manager_cls:
        manager_cls.return_value.push.side_effect = RemoteError(
            "Push rejected: remote has changes. Run 'espansr pull' first."
        )
        assert cmd_push(_ns(template=None, message=None)) == 1

    out = capsys.readouterr().out
    assert "[FAIL] Push rejected: remote has changes. Run 'espansr pull' first." in out
    assert "Pushed templates to remote." not in out
    manager_cls.return_value.push.assert_called_once_with(message=None)


def test_pull_conflict_maps_to_rc1(capsys):
    from espansr.__main__ import cmd_pull

    with (
        patch("espansr.core.remote.RemoteManager") as manager_cls,
        patch("espansr.integrations.espanso.sync_to_espanso") as sync,
    ):
        manager_cls.return_value.pull_with_result.side_effect = RemoteConflictError(
            "Merge conflicts detected in: greeting.json"
        )
        assert cmd_pull(_ns(template=None)) == 1

    assert "[FAIL] Conflict: Merge conflicts detected in: greeting.json" in capsys.readouterr().out
    sync.assert_not_called()


# ── list ─────────────────────────────────────────────────────────────────────


def test_cmd_list_prints_triggers_and_skips_untriggered(capsys):
    from espansr.__main__ import cmd_list

    store = get_templates_dir()
    _write_template(store, "alpha.json", {"name": "Alpha", "content": "a", "trigger": ":alpha"})
    _write_template(store, "notes.json", {"name": "Untriggered Notes", "content": "n"})

    assert cmd_list(None) == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert lines[0].split() == ["TRIGGER", "TEMPLATE", "NAME"]
    assert any(line.split() == [":alpha", "Alpha"] for line in lines)
    assert "Untriggered Notes" not in out


# ── retire ───────────────────────────────────────────────────────────────────


def test_retire_unknown_target_returns_1(capsys):
    from espansr.__main__ import cmd_retire

    assert cmd_retire(_ns(target=":nope", dry_run=False)) == 1
    assert "[FAIL] No template found for retire target: :nope" in capsys.readouterr().out


def test_retire_empty_target_returns_2(capsys):
    from espansr.__main__ import cmd_retire

    assert cmd_retire(_ns(target="   ", dry_run=False)) == 2
    out = capsys.readouterr().out
    assert "[FAIL] retire requires a trigger, filename, path, or template name" in out


def test_retire_publish_failure_returns_1(capsys):
    from espansr.__main__ import cmd_retire

    store = get_templates_dir()
    path = _write_template(store, "old.json", {"name": "Old", "content": "o", "trigger": ":old"})

    with patch("espansr.integrations.espanso.sync_to_espanso", return_value=False) as sync:
        assert cmd_retire(_ns(target=":old", dry_run=False)) == 1

    out = capsys.readouterr().out
    assert "[ok]   Retired Old [:old] at old.json (matched by trigger)" in out
    assert (
        "[FAIL] Template retired, but Espanso output refresh failed. Run 'espansr publish'." in out
    )
    sync.assert_called_once_with(update_bundled=False)
    # The template is gone, but its backup snapshot was taken first.
    assert not path.exists()
    assert (store / "_versions" / "old" / "v1.json").exists()


# ── check-output ─────────────────────────────────────────────────────────────


def test_check_output_json_reports_failures_and_rc1(tmp_path, capsys):
    from espansr.__main__ import cmd_check_output

    _write_template(
        get_templates_dir(),
        "audit.json",
        {
            "name": "Audit",
            "content": "audit",
            "trigger": ":audit",
            "output_contract": {
                "required_sections": ["FINDINGS"],
                "required_markers": [{"pattern": "Verdict:", "min_count": 1}],
                "forbidden_markers": [{"pattern": "TODO"}],
            },
        },
    )
    output = tmp_path / "output.md"
    output.write_text("no findings here\nTODO later\n", encoding="utf-8")

    assert cmd_check_output(_ns(template=":audit", path=str(output), json=True)) == 1

    report = json.loads(capsys.readouterr().out)
    assert report["template"] == "Audit"
    assert report["trigger"] == ":audit"
    assert report["passed"] is False
    assert sorted(failure["kind"] for failure in report["failures"]) == [
        "forbidden",
        "marker",
        "section",
    ]
    assert any("FINDINGS" in failure["message"] for failure in report["failures"])


# ── workflows / packet ───────────────────────────────────────────────────────


def test_workflows_show_unknown_id_and_unknown_action(capsys):
    from espansr.__main__ import cmd_workflows

    with patch("espansr.core.workflows.load_workflow_catalog", return_value=WorkflowCatalog()):
        assert cmd_workflows(_ns(workflows_action="show", workflow_id="nope")) == 1
        assert "[FAIL] Workflow not found: nope" in capsys.readouterr().out

        assert cmd_workflows(_ns(workflows_action="bogus")) == 2
        assert "[FAIL] Unknown workflows action: bogus" in capsys.readouterr().out


def test_packet_unknown_action_and_corrupt_packet_warns_in_list(capsys):
    from espansr.__main__ import cmd_packet

    packets_dir = get_packets_dir()
    save_packet(Packet(title="Good one", artifact_type="gap-review"), packets_dir=packets_dir)
    (packets_dir / "broken.md").write_text("not a packet at all\n", encoding="utf-8")

    assert cmd_packet(_ns(packet_action="list")) == 0
    out = capsys.readouterr().out
    assert "[warn] broken.md: packet is missing its front matter block" in out
    assert "good_one  [gap-review]  Good one" in out

    assert cmd_packet(_ns(packet_action="bogus", target="")) == 2
    assert "[FAIL] Unknown packet action: bogus" in capsys.readouterr().out


# ── record-install / import ──────────────────────────────────────────────────


def test_record_install_infer_failure_returns_1(capsys):
    from espansr.__main__ import cmd_record_install
    from espansr.core.install_meta import get_install_meta_path

    with patch("espansr.core.install_meta.infer_repo_dir", return_value=None):
        assert cmd_record_install(_ns(repo_dir=None, installer=None, venv_dir=None)) == 1

    assert "[FAIL] Could not determine the install directory to record." in capsys.readouterr().out
    assert not get_install_meta_path().exists()


def test_import_directory_all_failed_returns_1(tmp_path, capsys):
    from espansr.__main__ import cmd_import

    source = tmp_path / "incoming"
    source.mkdir()
    (source / "broken.json").write_text("{not json", encoding="utf-8")
    (source / "list.json").write_text("[1, 2, 3]", encoding="utf-8")

    assert cmd_import(_ns(path=str(source))) == 1

    out = capsys.readouterr().out
    assert "Imported 0 template(s), 2 failed." in out
    assert "  ! Invalid JSON in broken.json" in out
    assert "  ! list.json: expected a JSON object, got list" in out
    assert list(get_templates_dir().glob("*.json")) == []
