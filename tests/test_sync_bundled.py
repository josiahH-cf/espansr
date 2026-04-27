"""Tests for bundled-template drift checking and reconciliation."""

import json
from pathlib import Path
from unittest.mock import patch

import yaml


def _make_args(**kwargs):
    """Create a simple argparse-like namespace object."""
    import argparse

    defaults = {
        "apply": False,
        "check": False,
        "dry_run": False,
        "force": False,
        "verbose": False,
    }
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _write_json(path: Path, data: dict) -> None:
    """Write JSON with stable formatting for tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def test_bundled_report_ignores_formatting_differences(tmp_path):
    """Bundled drift is semantic, not based on raw file formatting."""
    from espansr.core.templates import build_bundled_template_report

    bundled_dir = tmp_path / "bundled"
    local_dir = tmp_path / "local"
    bundled_dir.mkdir()
    local_dir.mkdir()

    bundled = bundled_dir / "example.json"
    bundled.write_text(
        '{"name":"Example","content":"Hello","description":"desc","trigger":":ex"}',
        encoding="utf-8",
    )
    (local_dir / "example.json").write_text(
        json.dumps(
            {
                "trigger": ":ex",
                "description": "desc",
                "content": "Hello",
                "name": "Example",
            },
            indent=4,
        ),
        encoding="utf-8",
    )

    report = build_bundled_template_report(templates_dir=local_dir, bundled_dir=bundled_dir)

    assert report.errors == []
    assert len(report.entries) == 1
    assert report.entries[0].status == "up_to_date"
    assert report.has_drift() is False


def test_sync_bundled_check_ignores_local_only_templates(tmp_path, capsys):
    """Local-only templates are reported but do not count as bundled drift."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    data = {"name": "Shared", "content": "same", "trigger": ":shared"}
    _write_json(bundled_dir / "shared.json", data)
    _write_json(templates_dir / "shared.json", data)
    _write_json(
        templates_dir / "local_only.json",
        {"name": "Local Only", "content": "mine", "trigger": ":mine"},
    )

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args())

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "local_only.json" in output
    assert "already in sync" in output.lower()


def test_sync_bundled_apply_copies_and_updates_with_backup(tmp_path):
    """Apply mode copies missing bundled files and backs up changed local files."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    shared_bundled = {
        "name": "Shared Help",
        "content": "bundled copy",
        "trigger": ":shared",
    }
    missing_bundled = {
        "name": "New Starter",
        "content": "new bundled file",
        "trigger": ":new",
    }
    _write_json(bundled_dir / "shared_help.json", shared_bundled)
    _write_json(bundled_dir / "new_starter.json", missing_bundled)

    _write_json(
        templates_dir / "shared_help.json",
        {"name": "Shared Help", "content": "local edit", "trigger": ":shared"},
    )

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True))

    assert exit_code == 0
    assert (
        json.loads((templates_dir / "shared_help.json").read_text(encoding="utf-8"))
        == shared_bundled
    )
    assert (
        json.loads((templates_dir / "new_starter.json").read_text(encoding="utf-8"))
        == missing_bundled
    )

    version_path = templates_dir / "_versions" / "shared_help" / "v1.json"
    assert version_path.exists()
    version_data = json.loads(version_path.read_text(encoding="utf-8"))
    assert version_data["template_data"]["content"] == "local edit"


def test_sync_bundled_apply_skips_invalid_local_json(tmp_path, capsys):
    """Apply mode refuses to overwrite invalid local bundled files automatically."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    _write_json(
        bundled_dir / "broken.json",
        {"name": "Broken", "content": "bundled", "trigger": ":broken"},
    )
    (templates_dir / "broken.json").write_text("{not-valid-json", encoding="utf-8")

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "skipped invalid" in output.lower()
    assert (templates_dir / "broken.json").read_text(encoding="utf-8") == "{not-valid-json"


def test_sync_bundled_force_overwrites_invalid_local_json_with_backup(tmp_path):
    """Force mode backs up invalid local JSON before replacing it from bundled."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    bundled_data = {"name": "Broken", "content": "bundled", "trigger": ":broken"}
    _write_json(bundled_dir / "broken.json", bundled_data)
    (templates_dir / "broken.json").write_text("{not-valid-json", encoding="utf-8")

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, force=True))

    assert exit_code == 0
    assert (
        json.loads((templates_dir / "broken.json").read_text(encoding="utf-8"))
        == bundled_data
    )

    backups = list(
        (templates_dir / "_versions" / "broken").glob(
            "invalid-backup-before-bundled-sync-*.json"
        )
    )
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{not-valid-json"


def test_sync_bundled_force_requires_apply(tmp_path, capsys):
    """Force mode is only valid when apply mode is enabled."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(force=True))

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "requires --apply" in output


def test_sync_to_espanso_can_apply_bundled_updates_before_writing(tmp_path):
    """Normal sync can copy/update bundled templates before generating Espanso YAML."""
    from espansr.core.templates import TemplateManager
    from espansr.integrations.espanso import sync_to_espanso

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    match_dir = tmp_path / "espanso" / "match"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)
    match_dir.mkdir(parents=True)

    verify_bundled = {
        "name": "Verify and Falsify",
        "content": "Review and fix issues as you find them.",
        "trigger": ":verify",
    }
    meta_bundled = {
        "name": "Meta-Prompt Generator",
        "content": "Draft a context-safe meta-prompt.",
        "trigger": ":meta",
    }
    _write_json(bundled_dir / "verify.json", verify_bundled)
    _write_json(bundled_dir / "meta.json", meta_bundled)
    _write_json(
        templates_dir / "verify.json",
        {
            "name": "Verify and Falsify",
            "content": "Review only.",
            "trigger": ":verify",
        },
    )

    manager = TemplateManager(templates_dir=templates_dir)
    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.get_template_manager", return_value=manager),
        patch("espansr.integrations.espanso.validate_all", return_value=[]),
        patch("espansr.integrations.espanso.clean_stale_espanso_files"),
    ):
        result = sync_to_espanso(
            update_bundled=True,
            templates_dir=templates_dir,
            bundled_dir=bundled_dir,
        )

    assert result is True
    assert json.loads((templates_dir / "verify.json").read_text(encoding="utf-8")) == verify_bundled
    assert json.loads((templates_dir / "meta.json").read_text(encoding="utf-8")) == meta_bundled
    assert (templates_dir / "_versions" / "verify_and_falsify" / "v1.json").exists()

    output = yaml.safe_load((match_dir / "espansr.yml").read_text(encoding="utf-8"))
    matches = {entry["trigger"]: entry["replace"] for entry in output["matches"]}
    assert matches[":meta"] == "Draft a context-safe meta-prompt."
    assert matches[":verify"] == "Review and fix issues as you find them."


def test_sync_bundled_help_lists_flags(capsys):
    """sync-bundled exposes the expected check/apply CLI flags."""
    import sys

    from espansr.__main__ import main

    try:
        sys.argv = ["espansr", "sync-bundled", "--help"]
        main()
    except SystemExit:
        pass

    output = capsys.readouterr().out
    assert "--check" in output
    assert "--apply" in output
    assert "--dry-run" in output
    assert "--force" in output
    assert "--verbose" in output