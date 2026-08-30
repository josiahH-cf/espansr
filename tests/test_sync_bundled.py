"""Tests for bundled-template drift checking and reconciliation."""

import json
import re
from pathlib import Path
from unittest.mock import patch

import yaml

INLINE_CONTEXT_FOOTER = "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK.\n\n"


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


def test_sync_bundled_apply_migrates_renamed_starter_with_backup(tmp_path, capsys):
    """AC-6: old starter files are backed up before a renamed starter replaces them."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    bundled_template = {
        "name": "Sanitize Context",
        "content": "new bundled prompt",
        "trigger": ":sanitize",
        "replaces": [":hide-ai"],
    }
    old_local = {
        "name": "Hide AI Metadata",
        "content": "local edited prompt",
        "trigger": ":hide-ai",
    }
    _write_json(bundled_dir / "sanitize.json", bundled_template)
    _write_json(templates_dir / "hide_ai.json", old_local)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "migrated" in output.lower()
    actual_template = json.loads((templates_dir / "sanitize.json").read_text(encoding="utf-8"))
    assert actual_template == bundled_template
    assert not (templates_dir / "hide_ai.json").exists()

    version_path = templates_dir / "_versions" / "hide_ai_metadata" / "v1.json"
    assert version_path.exists()
    version_data = json.loads(version_path.read_text(encoding="utf-8"))
    assert version_data["template_data"] == old_local


def test_sync_bundled_apply_retires_old_starter_when_new_exists(tmp_path, capsys):
    """AC-6: old renamed starters are backed up and removed even after migration."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    bundled_template = {
        "name": "Sanitize Context",
        "content": "new bundled prompt",
        "trigger": ":sanitize",
        "replaces": [":hide-ai"],
    }
    old_local = {
        "name": "Hide AI Metadata",
        "content": "old bundled prompt still present",
        "trigger": ":hide-ai",
    }
    _write_json(bundled_dir / "sanitize.json", bundled_template)
    _write_json(templates_dir / "sanitize.json", bundled_template)
    _write_json(templates_dir / "hide_ai.json", old_local)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "retired" in output.lower()
    actual_template = json.loads((templates_dir / "sanitize.json").read_text(encoding="utf-8"))
    assert actual_template == bundled_template
    assert not (templates_dir / "hide_ai.json").exists()

    version_path = templates_dir / "_versions" / "hide_ai_metadata" / "v1.json"
    assert version_path.exists()
    version_data = json.loads(version_path.read_text(encoding="utf-8"))
    assert version_data["template_data"] == old_local


def test_sync_bundled_apply_retires_deleted_explanation_starters(tmp_path, capsys):
    """Deleted explanation starters retire into the surviving explain prompt."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    bundled_template = {
        "name": "Explain Context",
        "content": "new explain prompt",
        "trigger": ":explain",
    }
    old_templates = {
        "plain.json": {
            "name": "Plain-English Explanation",
            "content": "old plain prompt",
            "trigger": ":plain",
        },
        "dumb.json": {
            "name": "Explain Like I Am Five",
            "content": "older plain prompt",
            "trigger": ":dumb",
        },
    }
    _write_json(bundled_dir / "explain_context_comprehensively.json", bundled_template)
    _write_json(templates_dir / "explain_context_comprehensively.json", bundled_template)
    for filename, data in old_templates.items():
        _write_json(templates_dir / filename, data)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "retired" in output.lower()
    assert (
        json.loads(
            (templates_dir / "explain_context_comprehensively.json").read_text(encoding="utf-8")
        )
        == bundled_template
    )
    for filename in old_templates:
        assert not (templates_dir / filename).exists()

    assert (templates_dir / "_versions" / "plainenglish_explanation" / "v1.json").exists()
    assert (templates_dir / "_versions" / "explain_like_i_am_five" / "v1.json").exists()


def test_sync_bundled_apply_retires_deleted_gap_review_starters(tmp_path, capsys):
    """Deleted gap and principles starters retire into the surviving gaps prompt."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    bundled_template = {
        "name": "Gap Review",
        "content": "new gaps prompt",
        "trigger": ":gaps",
    }
    old_templates = {
        "explain_gaps_comprehensively_pt_2.json": {
            "name": "Explain Gaps Comprehensively (pt. 2)",
            "content": "old gap prompt",
            "trigger": ":gaps-2",
        },
        "principles.json": {
            "name": "First-Principles Analysis",
            "content": "old principles prompt",
            "trigger": ":principles",
        },
        "first_principles_analysis.json": {
            "name": "First Principles Analysis",
            "content": "older principles prompt",
            "trigger": ":fp",
        },
    }
    _write_json(bundled_dir / "gaps.json", bundled_template)
    _write_json(templates_dir / "gaps.json", bundled_template)
    for filename, data in old_templates.items():
        _write_json(templates_dir / filename, data)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "retired" in output.lower()
    assert json.loads((templates_dir / "gaps.json").read_text(encoding="utf-8")) == bundled_template
    for filename in old_templates:
        assert not (templates_dir / filename).exists()

    assert (templates_dir / "_versions" / "explain_gaps_comprehensively_pt_2" / "v1.json").exists()
    assert (templates_dir / "_versions" / "firstprinciples_analysis" / "v1.json").exists()
    assert (templates_dir / "_versions" / "first_principles_analysis" / "v1.json").exists()


def test_sync_bundled_apply_migrates_reality_and_telegram_starters(tmp_path, capsys):
    """Old reality and pocket-note files migrate to their independent replacements."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    reality_template = {
        "name": "Reality Summary",
        "content": "new reality prompt",
        "trigger": ":reality",
    }
    telegram_template = {
        "name": "Telegram Directive Runner",
        "content": "new telegram prompt",
        "trigger": ":telegram",
        "replaces": [":pocket-note"],
    }
    old_templates = {
        "reality_audit.json": {
            "name": "Reality Audit",
            "content": "old reality prompt",
            "trigger": ":reality",
        },
        "pocket_note.json": {
            "name": "Pocket Note Runner",
            "content": "old pocket note prompt",
            "trigger": ":pocket-note",
        },
    }
    _write_json(bundled_dir / "reality.json", reality_template)
    _write_json(bundled_dir / "telegram.json", telegram_template)
    for filename, data in old_templates.items():
        _write_json(templates_dir / filename, data)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "migrated" in output.lower()
    assert json.loads((templates_dir / "reality.json").read_text(encoding="utf-8")) == (
        reality_template
    )
    assert json.loads((templates_dir / "telegram.json").read_text(encoding="utf-8")) == (
        telegram_template
    )
    for filename in old_templates:
        assert not (templates_dir / filename).exists()

    assert (templates_dir / "_versions" / "reality_audit" / "v1.json").exists()
    assert (templates_dir / "_versions" / "pocket_note_runner" / "v1.json").exists()


def test_sync_bundled_apply_migrates_project_init_starter(tmp_path, capsys):
    """The renamed project-init starter migrates with a backup of the old file."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    bundled_templates = {
        "project_init_llm.json": {
            "name": "Project Init LLM",
            "content": "project init prompt",
            "trigger": ":project-init-llm",
            "replaces": [":project-init"],
        },
    }
    old_templates = {
        "project_init.json": {
            "name": "Project Init",
            "content": "old project prompt",
            "trigger": ":project-init",
        },
    }
    for filename, data in bundled_templates.items():
        _write_json(bundled_dir / filename, data)
    for filename, data in old_templates.items():
        _write_json(templates_dir / filename, data)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "migrated" in output.lower()
    for filename, data in bundled_templates.items():
        actual_template = json.loads((templates_dir / filename).read_text(encoding="utf-8"))
        assert actual_template == data
    for filename in old_templates:
        assert not (templates_dir / filename).exists()

    assert (templates_dir / "_versions" / "project_init" / "v1.json").exists()


def test_sync_bundled_blocks_renamed_trigger_collision(tmp_path, capsys):
    """AC-6: renamed starter migration stops before overwriting a custom trigger."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    _write_json(
        bundled_dir / "sanitize.json",
        {
            "name": "Sanitize Context",
            "content": "new bundled prompt",
            "trigger": ":sanitize",
            "replaces": [":hide-ai"],
        },
    )
    _write_json(
        templates_dir / "hide_ai.json",
        {"name": "Hide AI Metadata", "content": "old bundled prompt", "trigger": ":hide-ai"},
    )
    _write_json(
        templates_dir / "custom_sanitize.json",
        {"name": "Custom Sanitize", "content": "mine", "trigger": ":sanitize"},
    )

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True))

    output = capsys.readouterr().out
    assert exit_code == 2
    assert "trigger collision" in output.lower()
    assert not (templates_dir / "sanitize.json").exists()
    assert (templates_dir / "hide_ai.json").exists()


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
    assert json.loads((templates_dir / "broken.json").read_text(encoding="utf-8")) == bundled_data

    backups = list(
        (templates_dir / "_versions" / "broken").glob("invalid-backup-before-bundled-sync-*.json")
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


def test_sync_to_espanso_blocks_renamed_trigger_collision_before_writing(tmp_path):
    """AC-6: sync stops before writing Espanso YAML when starter migration collides."""
    from espansr.core.templates import TemplateManager
    from espansr.integrations.espanso import sync_to_espanso

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    match_dir = tmp_path / "espanso" / "match"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)
    match_dir.mkdir(parents=True)

    _write_json(
        bundled_dir / "sanitize.json",
        {
            "name": "Sanitize Context",
            "content": "new bundled prompt",
            "trigger": ":sanitize",
            "replaces": [":hide-ai"],
        },
    )
    _write_json(
        templates_dir / "hide_ai.json",
        {"name": "Hide AI Metadata", "content": "old bundled prompt", "trigger": ":hide-ai"},
    )
    _write_json(
        templates_dir / "custom_sanitize.json",
        {"name": "Custom Sanitize", "content": "mine", "trigger": ":sanitize"},
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

    assert result is False
    assert not (match_dir / "espansr.yml").exists()
    assert not (templates_dir / "sanitize.json").exists()
    assert (templates_dir / "hide_ai.json").exists()


def test_sync_to_espanso_invalid_bundled_hint_uses_starters_command(tmp_path, capsys):
    """Runtime bundled-sync failure guidance points to the primary starters lane."""
    from espansr.core.templates import TemplateManager
    from espansr.integrations.espanso import sync_to_espanso

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    match_dir = tmp_path / "espanso" / "match"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)
    match_dir.mkdir(parents=True)

    _write_json(
        bundled_dir / "broken.json",
        {"name": "Broken", "content": "bundled", "trigger": ":broken"},
    )
    (templates_dir / "broken.json").write_text("{not-valid-json", encoding="utf-8")

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

    output = capsys.readouterr().out
    assert result is False
    assert "espansr starters --apply --force" in output
    assert "sync-bundled --apply --force" not in output


def test_starters_help_lists_flags(capsys):
    """starters exposes the expected check/apply CLI flags."""
    import sys

    from espansr.__main__ import main

    try:
        sys.argv = ["espansr", "starters", "--help"]
        main()
    except SystemExit:
        pass

    output = capsys.readouterr().out
    assert "--check" in output
    assert "--apply" in output
    assert "--dry-run" in output
    assert "--force" in output
    assert "--verbose" in output


def test_bundled_meta_template_has_inline_optional_input_block():
    """The :meta starter prompt ends with an inline optional input area."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "meta.json").read_text(encoding="utf-8"))

    variables = {variable["name"]: variable for variable in data.get("variables", [])}
    assert data["trigger"] == ":meta"
    assert "{{context}}" not in data["content"]
    assert "context" not in variables
    assert "USER CONTEXT, GOAL, OR NOTES BELOW. IGNORE IF BLANK." in data["content"]
    assert data["content"].endswith(INLINE_CONTEXT_FOOTER)


def test_bundled_q_and_a_template_contract():
    """The :q&a starter opens a source-agnostic, evidence-bound Q&A session."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "q_and_a.json").read_text(encoding="utf-8"))
    content = data["content"]

    assert data["trigger"] == ":q&a"
    assert data["category"] == "analysis"
    assert data["stage"] == "interactive-qa"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []
    assert "output exactly this sentence and nothing else" in content
    assert "Okay, what do you want to know about?" in content
    assert "Be agnostic to project type, technology, file format, and concept." in content
    assert "Do not require the user to preselect sources" in content
    assert "connected vault" not in content.lower()
    assert "## Refresh" not in content
    assert not content.endswith(INLINE_CONTEXT_FOOTER)


def test_all_bundled_templates_end_with_trailing_newline():
    """Every bundled template ends with a trailing newline so the cursor lands on
    a fresh line ready for input, not jammed against the last character."""
    repo_root = Path(__file__).resolve().parents[1]
    templates_dir = repo_root / "templates"
    offenders = [
        path.name
        for path in sorted(templates_dir.glob("*.json"))
        if not json.loads(path.read_text(encoding="utf-8")).get("content", "").endswith("\n")
    ]
    assert offenders == [], f"templates missing a trailing newline: {offenders}"


def test_bundled_context_prompts_use_inline_footer_instead_of_variables():
    """Context-bearing starter prompts use inline notes instead of popup variables."""
    repo_root = Path(__file__).resolve().parents[1]
    templates_dir = repo_root / "templates"
    expected = {
        "goal_clarifier.json": (),
        "meta.json": ("context",),
        "context.json": (),
        "template_builder.json": (),
        "project_init_llm.json": (),
    }

    for filename, removed_variable_names in expected.items():
        data = json.loads((templates_dir / filename).read_text(encoding="utf-8"))
        content = data["content"]
        variables = {variable["name"]: variable for variable in data.get("variables", [])}

        assert content.endswith(INLINE_CONTEXT_FOOTER), filename
        assert "USER CONTEXT, PROJECT IDEA" not in content
        for variable_name in removed_variable_names:
            assert f"{{{{{variable_name}}}}}" not in content
            assert variable_name not in variables


def test_bundled_prompt_taxonomy_and_renamed_triggers():
    """AC-2: bundled prompts expose the redesigned trigger taxonomy and metadata."""
    repo_root = Path(__file__).resolve().parents[1]
    templates_dir = repo_root / "templates"
    expected = {
        "project_init_llm.json": (
            ":project-init-llm",
            "workflow",
            "project-init-llm",
            [],
            [":project-init"],
        ),
        "feature.json": (
            ":feature",
            "workflow",
            "feature-delivery",
            [],
            [],
        ),
        "unblock.json": (
            ":unblock",
            "workflow",
            "unblocking",
            [],
            [],
        ),
        "visual_workflow.json": (
            ":visual",
            "explanation",
            "visual-workflow",
            [],
            [],
        ),
        "gaps.json": (
            ":gaps",
            "analysis",
            "gap-review",
            [],
            [":critique", ":gaps-2", ":principles", ":fp"],
        ),
        "reality.json": (":reality", "analysis", "reality-summary", [], []),
        "explain_context_comprehensively.json": (
            ":explain",
            "explanation",
            "one-page-explanation",
            [],
            [":plain", ":dumb", ":simplify", ":explain-1", ":distill", ":summarize"],
        ),
        "context.json": (":context", "prompting", "context-reset", [], []),
        "goal_clarifier.json": (":goal", "workflow", "goal-refinement", [], []),
        "template_builder.json": (
            ":template-builder",
            "prompting",
            "template-authoring",
            [],
            [],
        ),
        "troubleshoot.json": (":troubleshoot", "workflow", "troubleshooting", [], []),
        "sanitize.json": (":sanitize", "safety", "scrub", [], [":hide-ai"]),
        "docs_qa.json": (":docs-qa", "maintenance", "docs-review", [], [":qa"]),
        "telegram.json": (
            ":telegram",
            "workflow",
            "source-directive",
            [],
            [":pocket-note"],
        ),
        "git_yolo_sh.json": (":git-yolo-sh", "workflow", "git-yolo", [], []),
        "git_rebase_sh.json": (":git-rebase-sh", "workflow", "git-rebase", [], []),
        "git_branch_sh.json": (":git-branch-sh", "workflow", "git-branch", [], []),
        "git_yolo_ps.json": (":git-yolo-ps", "workflow", "git-yolo", [], []),
        "git_rebase_ps.json": (":git-rebase-ps", "workflow", "git-rebase", [], []),
        "git_branch_ps.json": (":git-branch-ps", "workflow", "git-branch", [], []),
        "work_merge.json": (
            ":work-merge",
            "workflow",
            "git-merge-sanitize",
            [],
            [":work-merge-safe"],
        ),
    }
    retired_files = {
        "dumb.json",
        "explain_gaps_comprehensively_pt_2.json",
        "first_principles_analysis.json",
        "plain.json",
        "principles.json",
        "reality_audit.json",
        "project_init.json",
        "feature_init.json",
        "feature_new.json",
        "feature_next.json",
        "project_scaffold.json",
        "scaffold_feature_process.json",
        "feature_scope.json",
        "feature_continue.json",
        "hide_ai.json",
        "qa_docs.json",
        "pocket.json",
        "pocket_note.json",
        "feat.json",
        "feat_plan.json",
        "feat_runner.json",
        "feedback_loop.json",
        "merge.json",
        "rebase.json",
        "save.json",
        "pocket_system.json",
        "agent_scaffold.json",
        "work_merge_safe.json",
        "distill.json",
        "summarize.json",
    }

    existing_files = {path.name for path in templates_dir.glob("*.json")}
    assert retired_files.isdisjoint(existing_files)

    for path in templates_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["description"]
        assert data["category"]
        assert data["stage"]
        assert data.get("next_triggers", []) == []

    for filename, (trigger, category, stage, next_triggers, replaces) in expected.items():
        data = json.loads((templates_dir / filename).read_text(encoding="utf-8"))

        assert data["trigger"] == trigger
        assert data["description"]
        assert data["category"] == category
        assert data["stage"] == stage
        assert data["next_triggers"] == next_triggers
        assert data["replaces"] == replaces


def test_bundled_quick_help_uses_current_triggers():
    """AC-3: :espansr quick help lists current prompts without stale triggers."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "espansr_help.json").read_text(encoding="utf-8"))
    content = data["content"]

    for trigger in [
        ":explain",
        ":visual",
        ":gaps",
        ":reality",
        ":telegram",
        ":troubleshoot",
        ":verify",
        ":sanitize",
        ":context",
        ":template-builder",
        ":goal",
        ":project-init-llm",
        ":feature",
        ":unblock",
        ":docs-qa",
        ":work-merge",
        ":git-yolo-sh",
        ":git-rebase-sh",
        ":git-branch-sh",
        ":git-yolo-ps",
        ":git-rebase-ps",
        ":git-branch-ps",
        ":coms",
        ":espansr",
    ]:
        assert trigger in content

    for removed_alias in ["Legacy aliases", "sync-down", "sync-bundled"]:
        assert removed_alias not in content

    help_lines = content.splitlines()
    for stale_trigger in [
        ":simplify",
        ":critique",
        ":fp",
        ":hide-ai",
        ":qa",
        ":project-init",
        ":feature-init",
        ":feature-new",
        ":feature-next",
        ":project-scaffold",
        ":scaffold-feature-process",
        ":feature-scope",
        ":continue",
        ":plain",
        ":principles",
        ":pocket-note",
        ":feat-plan",
        ":feat-runner",
        ":feat",
        ":feedback-loop",
        ":save",
        ":merge",
        ":rebase",
        ":pocket-system",
        ":agent-scaffold",
        ":work-merge-safe",
    ]:
        assert not any(line.strip().startswith(f"{stale_trigger} ") for line in help_lines)


def test_sync_bundled_apply_migrates_work_merge_safe_to_work_merge(tmp_path, capsys):
    """The renamed work-merge starter migrates the old :work-merge-safe copy with a backup."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    bundled_template = {
        "name": "Work Merge",
        "content": "new work merge prompt",
        "trigger": ":work-merge",
        "replaces": [":work-merge-safe"],
    }
    old_local = {
        "name": "Work-Safe Merge",
        "content": "old work-merge-safe prompt",
        "trigger": ":work-merge-safe",
    }
    _write_json(bundled_dir / "work_merge.json", bundled_template)
    _write_json(templates_dir / "work_merge_safe.json", old_local)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "migrated" in output.lower()
    migrated = json.loads((templates_dir / "work_merge.json").read_text(encoding="utf-8"))
    assert migrated == bundled_template
    assert not (templates_dir / "work_merge_safe.json").exists()
    assert (templates_dir / "_versions" / "worksafe_merge" / "v1.json").exists()


def test_bundled_project_init_template_contract():
    """The project-init prompt keeps its AGENTS.md-centered instruction contract."""
    repo_root = Path(__file__).resolve().parents[1]
    templates_dir = repo_root / "templates"

    expected = {
        "project_init_llm.json": (
            ":project-init-llm",
            [":project-init"],
            [
                "AGENTS.md as the canonical instruction surface",
                "CLAUDE.md as a pointer to AGENTS.md",
                "Do not create a separate Copilot instruction file unless",
            ],
        ),
    }

    all_replacements: list[str] = []
    for filename, (trigger, replaces, phrases) in expected.items():
        data = json.loads((templates_dir / filename).read_text(encoding="utf-8"))
        content = data["content"]

        assert data["trigger"] == trigger
        assert data["category"] == "workflow"
        assert data["replaces"] == replaces
        assert content.endswith(INLINE_CONTEXT_FOOTER)
        for phrase in phrases:
            assert phrase in content
        all_replacements.extend(replaces)

    assert len(all_replacements) == len(set(all_replacements))


def test_bundled_feature_template_contract():
    """The :feature prompt defaults to one three-outcome implementation meta-prompt."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "feature.json").read_text(encoding="utf-8"))
    content = data["content"]

    assert data["name"] == "Feature"
    assert data["trigger"] == ":feature"
    assert data["category"] == "workflow"
    assert data["stage"] == "feature-delivery"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []
    assert content.endswith(INLINE_CONTEXT_FOOTER)

    # Default delivery is one implementation meta-prompt; a project-native flow is an
    # explicit appended-context override, and process existence alone is not an override.
    for phrase in [
        "feature-handoff architect",
        "Do not implement the requested feature.",
        "Core Feature Outcome",
        "FEATURE SPECIFICATION DECISIONS",
        "accept all recommendations",
        "Adversarial Specification Review",
        "implementation meta-prompt",
        "one implementation meta-prompt",
        "explicit appended-context override",
        "is not an override",
        "Override: Project-Native Flow",
        "REALITY SUMMARY",
    ]:
        assert phrase in content, phrase

    # All three verification outcomes are mandatory and adaptively packaged, not three
    # forced documents, and the architecture/behavior checks must be fail-first.
    for phrase in [
        "Three Verification Outcomes",
        "Architecture Outcome",
        "Behavior Outcome",
        "Human Litmus Outcome",
        "three processes the feature must satisfy",
        "single combined specification",
        "fails against the starting state",
        "If this was built correctly:",
        "Model verdict:",
        "Human verdict:",
    ]:
        assert phrase in content, phrase

    # Preservation gate, external completion predicate, honest budget, mechanical
    # extraction, scope traceability, and a consolidated package are all required.
    for phrase in [
        "Preservation Gate",
        "Acceptance and Preservation Matrix",
        "ALL_GATES_GREEN",
        "BUDGET_EXHAUSTED",
        "BLOCKED",
        "Do not invent a numeric",
        "Mechanical Deliverable Extraction",
        "derived mechanically",
        "Scope Traceability",
        "Consolidated Delivery Package",
    ]:
        assert phrase in content, phrase

    # Gold-standard harness hardening: deterministic-over-judge, evidence-cited
    # checks, recorded fail-first baseline, surfaced human kickoff inputs, an
    # auditable single transcript, and the runnable-check invariant under any packaging.
    for phrase in [
        "KICKOFF INPUTS",
        "deterministic checks over model judgment",
        "cite the evidence",
        "failing baseline",
        "separate from implementation code",
        "re-runnable verification",
        "one linear transcript",
        "read-only",
    ]:
        assert phrase in content, phrase

    # Delivery is a single pre-write approval round: recommendations plus a "what
    # would be" reality summary, then the final artifact is written after the reply.
    for phrase in [
        "Pre-Write and Single Approval Round",
        "consolidated approval round",
        "DECISIONS AND RECOMMENDATIONS",
        "triggers the final write",
    ]:
        assert phrase in content, phrase

    # Standalone: one self-contained prompt with no companion command.
    assert (
        "This is one standalone prompt. Do not require, invoke, reference, or direct the user "
        "to another prompt or command."
    ) in content

    # No dependency on the retired loop artifacts, triggers, or sibling prompts.
    for forbidden in [
        "features/STATE.json",
        "features/README.md",
        ":feat-plan",
        ":feat-runner",
        ":agent-scaffold",
        ":feedback-loop",
        ":meta",
        ":reality",
        ":cb-transcript-feature",
    ]:
        assert forbidden not in content, forbidden


def test_bundled_unblock_template_contract():
    """The :unblock prompt is a standalone bulk-input blocker-resolution workflow."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "unblock.json").read_text(encoding="utf-8"))
    content = data["content"]

    assert data["name"] == "Unblock"
    assert data["trigger"] == ":unblock"
    assert data["category"] == "workflow"
    assert data["stage"] == "unblocking"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []
    assert content.endswith(INLINE_CONTEXT_FOOTER)

    # Works from blank context and inspects/resolves before escalating.
    assert "Additional notes after the final marker are optional" in content
    assert "Inspect before asking" in content
    assert "Resolve Everything the Agent Can" in content

    # Consolidated bulk packet with stable IDs and flexible reply formats.
    for phrase in [
        "B01",
        "UNBLOCK PACKET",
        "ALREADY CLEARED",
        "DECISIONS AND INFORMATION NEEDED",
        "ACTIONS FOR YOU",
        "EXTERNAL OR WAITING ITEMS",
        "REPLY FORMAT",
        "accept all recommendations",
        "stream-of-consciousness",
        "A1 done",
        "reduced delta packet",
        "Prevent Repeated Blocking",
        "UNBLOCKED",
        "PARTIALLY UNBLOCKED",
    ]:
        assert phrase in content, phrase

    # accept-all is decision-scoped, not blanket authorization.
    assert (
        "`accept all recommendations` applies only to the explicitly recommended decision options"
        in content
    )
    # Proof required before a blocker is cleared, plus safety handling.
    assert "Do not claim a blocker is cleared until" in content
    assert "Never request that the user paste passwords" in content
    assert "untrusted data" in content
    assert "```<detected-language>" in content

    # Standalone: no feature-loop, router, state file, or platform coupling.
    for forbidden in ["features/", ":feature", ":feat-plan", "GitHub"]:
        assert forbidden not in content, forbidden


def test_bundled_explain_template_contract():
    """The unified :explain prompt is a standalone faithful one-page explainer."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads(
        (repo_root / "templates" / "explain_context_comprehensively.json").read_text(
            encoding="utf-8"
        )
    )
    content = data["content"]

    assert data["name"] == "Explain"
    assert data["trigger"] == ":explain"
    assert data["category"] == "explanation"
    assert data["stage"] == "one-page-explanation"
    assert data["next_triggers"] == []
    assert data["replaces"] == [
        ":plain",
        ":dumb",
        ":simplify",
        ":explain-1",
        ":distill",
        ":summarize",
    ]
    assert data.get("variables", []) == []
    assert content.endswith(INLINE_CONTEXT_FOOTER)

    for phrase in [
        "If the marker is blank, explain the most recent coherent subject already in view",
        "focus, audience, emphasis, voice, or visual preference",
        "Follow the newest explicit focus",
        "inspect the actual material first when accessible",
        "Do not summarize from a filename, title, snippet, memory, or another summary",
        "Use lawful access only",
        "Do not use pirated or shadow-library copies",
        "Never claim to have read, watched, or retrieved material that was not actually accessed",
        "strongest lawful substitute",
        "explain the result conditionally",
        "preserve their separate claims, terms, and positions",
        "Attribute source-specific claims",
        "Never invent claims, quotations, examples",
        "Do not fact-check, critique, grade, debate",
        "Do not modify files, execute the material, or change external state",
        "Write exactly three short, cohesive paragraphs with no headings",
        "Follow the paragraphs with three to seven bullets",
        "add at most one compact inline visual after the bullets",
        "Never invent nodes, relationships, categories, or numbers",
        "no more than 700 words",
        "### Additional context needed",
        "Use no more than three bullets",
        "ask one brief clarification question",
    ]:
        assert phrase in content, phrase

    # Standalone and read-only: does not route to or depend on retired or sibling prompts.
    for other in (":distill", ":summarize", ":reality", ":visual", ":research"):
        assert other not in content, other


def test_bundled_goal_template_contract():
    """The reworked :goal prompt is a standalone context-grounded goal-refinement workflow."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "goal_clarifier.json").read_text(encoding="utf-8"))
    content = data["content"]

    assert data["name"] == "Goal Refiner"
    assert data["trigger"] == ":goal"
    assert data["category"] == "workflow"
    assert data["stage"] == "goal-refinement"
    assert data["next_triggers"] == []
    assert data["replaces"] == []
    assert data.get("variables", []) == []
    assert content.endswith(INLINE_CONTEXT_FOOTER)

    for phrase in [
        "If the marker is blank, infer the active goal from the most recent coherent context",
        "Objectively Restate the Goal",
        "What the user said or supplied",
        "The current state or contextual starting point",
        "The desired real-world end state",
        "Resolve obvious speech-to-text mistakes",
        "Separate the requested outcome from proposed methods",
        "Assign stable gap IDs such as G01, G02, and G03",
        "strategic rationale or parent objective",
        "Missing scope boundary or explicit non-goals",
        "define observable and reviewable evidence instead of inventing a numeric target",
        "GOAL REFINEMENT",
        "DECISIONS NEEDED TO FINALIZE",
        "Misinterpretation risk:",
        "accept all recommendations",
        "stream-of-consciousness",
        "reduced delta packet",
        "Adversarial Misinterpretation Check",
        "REFINED GOAL",
        "GOAL CONTRACT",
        "Interpretation guardrails:",
        "REMAINING NONBLOCKING UNKNOWNS",
        "Do not include implementation tasks, milestones",
    ]:
        assert phrase in content, phrase

    # Decision-scoped accept-all, not blanket authorization.
    assert (
        "`accept all recommendations` adopts only the explicitly recommended decision options"
        in content
    )
    # Project-agnostic, read-only, no companion prompt or persistent state.
    for forbidden in ["GitHub", "features/STATE.json", ":feature", ":unblock"]:
        assert forbidden not in content, forbidden


def test_bundled_sanitize_template_contract():
    """The sanitize prompt preserves its broader sanitization and planning contract."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "sanitize.json").read_text(encoding="utf-8"))

    content = data["content"]

    assert data["trigger"] == ":sanitize"
    assert data["category"] == "safety"
    assert data["stage"] == "scrub"
    assert data["next_triggers"] == []
    assert data["replaces"] == [":hide-ai"]
    assert "comprehensive" in data["description"].lower()
    assert "recommendation" in data["description"].lower()

    assert "analyze the project comprehensively" in content.lower()
    assert "development artifacts" in content.lower()
    assert "source code" in content.lower()
    assert "comments" in content.lower()
    assert "docstrings" in content.lower()
    assert "internal-control and governance files" in content.lower()
    assert "AGENTS.md" in content
    assert "CLAUDE.md" in content
    assert ".github/" in content
    assert ".claude/" in content
    assert ".codex/" in content
    assert "governance/" in content
    assert "workflow/" in content
    assert "specs/" in content
    assert "tasks/" in content
    assert "decisions/" in content
    assert "recommend `.gitignore` first" in content
    assert "already tracked or already shared" in content
    assert "Recommended Sanitization Plan" in content
    assert "Hyper-safe" in content
    assert "Minimum-safe" in content
    assert "when the risk is non-trivial" in content.lower()


def test_bundled_revise_template_contract():
    """The revise prompt stays a strict, output-only message cleanup assistant."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "revise.json").read_text(encoding="utf-8"))

    content = data["content"]

    assert data["trigger"] == ":revise"
    assert data["category"] == "communication"
    assert data["stage"] == "message-revision"
    assert data["next_triggers"] == []
    assert "clarity" in data["description"].lower()
    assert "preserving meaning" in data["description"].lower()

    assert (
        "You are `revise`, a minimal assistant for cleaning up user-provided messaging." in content
    )
    assert (
        "If the user includes a style, direction, audience, tone, or wording preference "
        "there, follow it." in content
    )
    assert (
        "If no direction is provided, default to a clean edit for clarity and concision." in content
    )
    assert "Avoid em dashes." in content
    assert "Avoid trailing spaces." in content
    assert "Avoid contrast framing like `it's this, not this`." in content
    assert "Do not add new facts, claims, requests, examples, or context." in content
    assert "Do not explain edits." in content
    assert "Do not ask follow-up questions." in content
    assert "Return only the revised text." in content
    assert "No text provided to revise." in content
    assert content.endswith(INLINE_CONTEXT_FOOTER)


def test_bundled_quick_help_describes_broader_sanitize_role():
    """Quick help should describe sanitize as broader than AI-marker cleanup."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "espansr_help.json").read_text(encoding="utf-8"))

    assert (
        ":sanitize         — assess sensitive/internal traces and recommend sanitization"
        in data["content"]
    )


def test_bundled_quick_help_lists_revise_prompt():
    """Quick help should list revise as a standalone writing utility prompt."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "espansr_help.json").read_text(encoding="utf-8"))

    assert (
        ":revise   — clean up messaging while preserving meaning and direction" in data["content"]
    )


def test_bundled_troubleshoot_template_contract():
    """The troubleshoot prompt enforces ordered repair and affected-area review."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "troubleshoot.json").read_text(encoding="utf-8"))

    content = data["content"]

    assert data["trigger"] == ":troubleshoot"
    assert data["category"] == "workflow"
    assert data["stage"] == "troubleshooting"
    assert data["next_triggers"] == []
    assert data["replaces"] == []

    required_phrases = [
        "Context quality first",
        "Bounded research before planning",
        "Concrete plan",
        "Test-first when practical",
        "Execute the minimal fix",
        "Focused verification",
        "Affected-area review",
        "Completion gate",
        "poisoned, stale, contradictory, or irrelevant context",
        "newest explicit user direction and reliable local evidence",
        "owning abstraction",
        "directly affected docs, configs, help text, workflow text, or prompt guidance",
        "cheapest failing test",
        "Finish only when both gates pass",
    ]

    for phrase in required_phrases:
        assert phrase in content

    assert content.index("Context quality first") < content.index(
        "Bounded research before planning"
    )
    assert content.index("Bounded research before planning") < content.index("Concrete plan")
    assert content.index("Concrete plan") < content.index("Execute the minimal fix")
    assert content.index("Execute the minimal fix") < content.index("Focused verification")
    assert content.index("Focused verification") < content.index("Affected-area review")
    assert content.index("Affected-area review") < content.index("Completion gate")
    assert content.endswith(INLINE_CONTEXT_FOOTER)


def test_bundled_quick_help_lists_troubleshoot_prompt():
    """Quick help should list troubleshoot as an ordered debugging workflow prompt."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "espansr_help.json").read_text(encoding="utf-8"))

    assert (
        ":troubleshoot — debug with context checks, research, planning, fixing, and verification"
        in data["content"]
    )


def test_bundled_gaps_template_contract_preserves_review_modes():
    """The gaps prompt preserves gap and first-principles review without owning reality."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "gaps.json").read_text(encoding="utf-8"))

    content = data["content"]

    assert data["trigger"] == ":gaps"
    assert data["replaces"] == [":critique", ":gaps-2", ":principles", ":fp"]
    assert "Mode selection" in content
    assert content.count("Mode selection") == 1
    assert "first-principles pass" in content
    assert "reality pass" not in content


def test_bundled_reality_template_contract():
    """Reality is a comprehensive standalone end-state account, not a diagnostic review mode."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "reality.json").read_text(encoding="utf-8"))
    content = data["content"]

    assert data["name"] == "Reality Summary"
    assert data["trigger"] == ":reality"
    assert data["category"] == "analysis"
    assert data["stage"] == "reality-summary"
    assert data["next_triggers"] == []
    assert data["replaces"] == []

    # Grounding: evidence is classified rather than flattened into one voice.
    for phrase in (
        "**Verified reality:**",
        "**Proposed reality:**",
        "**Supported inference:**",
        "**Unknown or unresolved:**",
        "Do not silently repair, optimize, reinterpret, or complete it",
    ):
        assert phrase in content, phrase

    # Boundaries: reports reality, never performs or grades the underlying work.
    for phrase in (
        "Report reality; do not perform the underlying work.",
        "conduct gap analysis or a first-principles critique",
        "recommend improvements, alternate approaches, or next steps",
        "tell the user which espansr command to run next",
    ):
        assert phrase in content, phrase

    # Output contract: comprehensive, headed, and closed by a definition of done.
    for phrase in (
        "# Reality Summary",
        "**If you only read one thing:**",
        "Be comprehensive rather than artificially short",
        "## ✅ Definition of Done",
    ):
        assert phrase in content, phrase

    # The superseded fixed-length contract is gone.
    for phrase in (
        "Return exactly two short plain-English paragraphs",
        "followed by zero to ten bullets",
        "Every bullet must be one complete sentence",
    ):
        assert phrase not in content, phrase

    assert content.endswith(INLINE_CONTEXT_FOOTER)


def test_bundled_project_systems_template_contract():
    """:project-systems is a file-backed runner for the Master Systems Process."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads(
        (repo_root / "templates" / "project_systems.json").read_text(encoding="utf-8")
    )
    content = data["content"]

    assert data["name"] == "Master Systems Process Runner"
    assert data["trigger"] == ":project-systems"
    assert data["category"] == "workflow"
    assert data["stage"] == "master-systems-process"
    assert data["next_triggers"] == []
    assert data["replaces"] == []

    # One entry point: the tracker owns the active step and the standing command.
    for phrase in (
        "# Master Systems Process — Runner Prompt",
        "The files are the memory; do not rely on prior chat.",
        "[[Master Systems Process — Project Tracker]]",
        "Continue the first incomplete tracker step until the next real human decision",
        "Do not recreate the plan or restart completed work.",
    ):
        assert phrase in content, phrase

    # Unknowns are triaged rather than pushed through unfounded criteria.
    for phrase in (
        "**Discoverable:**",
        "**Testable:**",
        "**Human-owned:**",
        "**Deferred:**",
        "Do not push an unknown through criteria that have not themselves been established.",
        "Ask questions only after agent-owned discovery is complete.",
    ):
        assert phrase in content, phrase

    # Writeback: every surface the runner may touch is named with its own rule.
    for phrase in (
        "**Tracker:**",
        "**Clarification file:**",
        "**Master document:**",
        "**SVG files:**",
        "**System Project:**",
        "make sure the project can resume from the tracker alone",
    ):
        assert phrase in content, phrase

    # Standalone runner: no inline-context footer, and it ends on the report rule.
    assert not content.endswith(INLINE_CONTEXT_FOOTER)
    assert content.rstrip().endswith(
        "report what changed and the next action without a long recap."
    )


def test_bundled_telegram_template_contract():
    """Telegram resolves a generic source and runs its directive without fixed file assumptions."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "telegram.json").read_text(encoding="utf-8"))
    content = data["content"]

    assert data["trigger"] == ":telegram"
    assert data["category"] == "workflow"
    assert data["stage"] == "source-directive"
    assert data["next_triggers"] == []
    assert data["replaces"] == [":pocket-note"]
    assert "attachment, local path, URL, filename, directory, file-type hint" in content
    assert "unique or strongly supported" in content
    assert "ask one focused follow-up question" in content
    assert "Do not assume a fixed filename, directory, repository" in content
    assert "contextualized.md" not in content
    assert "Pocket" not in content
    assert content.endswith("SOURCE, LOCATION, FILE TYPE, OR NOTES BELOW. IGNORE IF BLANK.\n\n")


def test_bundled_prompts_are_independent_except_for_help():
    """Bundled prompts do not suggest another prompt; only the help lists triggers."""
    repo_root = Path(__file__).resolve().parents[1]
    templates_dir = repo_root / "templates"
    templates = {}
    for path in templates_dir.glob("*.json"):
        templates[path.name] = json.loads(path.read_text(encoding="utf-8"))

    triggers = {data["trigger"] for data in templates.values() if data.get("trigger")}
    allowed_cross_prompt_files = {"espansr_help.json"}

    for filename, data in templates.items():
        assert data.get("next_triggers", []) == [], filename
        if filename in allowed_cross_prompt_files:
            continue

        own_trigger = data.get("trigger")
        content = data.get("content", "")
        for trigger in triggers - {own_trigger}:
            assert not re.search(
                re.escape(trigger) + r"(?![a-z0-9-])", content
            ), f"{filename} directs users to {trigger}"


def test_bundled_git_helper_templates_are_executable_commands():
    """Git helper prompts contain self-invoking command snippets, not prose only."""
    repo_root = Path(__file__).resolve().parents[1]
    templates_dir = repo_root / "templates"
    expected = {
        "git_yolo_sh.json": (
            ":git-yolo-sh",
            "git_yolo_push()",
            "git push --force-with-lease",
            "git_yolo_push",
        ),
        "git_rebase_sh.json": (
            ":git-rebase-sh",
            "git_rebase_main_safe()",
            "git stash push -u",
            "git_rebase_main_safe",
        ),
        "git_branch_sh.json": (
            ":git-branch-sh",
            "git_new_branch()",
            'git switch -c "$branch_name"',
            "git_new_branch",
        ),
        "git_yolo_ps.json": (
            ":git-yolo-ps",
            "function Invoke-GitYoloMain",
            "Invoke-GitChecked push --force-with-lease",
            "Invoke-GitYoloMain",
        ),
        "git_rebase_ps.json": (
            ":git-rebase-ps",
            "function Invoke-GitRebaseMainSafe",
            "Invoke-GitChecked stash push -u",
            "Invoke-GitRebaseMainSafe",
        ),
        "git_branch_ps.json": (
            ":git-branch-ps",
            "function Invoke-GitNewBranch",
            "Invoke-GitChecked switch -c $branchName",
            "Invoke-GitNewBranch",
        ),
    }

    for filename, (trigger, definition, required_command, invocation) in expected.items():
        data = json.loads((templates_dir / filename).read_text(encoding="utf-8"))
        content = data["content"]

        assert data["trigger"] == trigger
        assert data["category"] == "workflow"
        assert data["next_triggers"] == []
        assert definition in content
        assert required_command in content
        assert content.rstrip().endswith(invocation)
        assert "git reset --hard" not in content
        assert "gh " not in content
        assert "Run this from a non-main branch." not in content
        assert "Local changes are on main" in content
        assert "merge --ff-only" in content

        if "yolo" in filename:
            assert "--force-with-lease" in content
            assert "not force-pushing main" in content
        else:
            assert "--force" not in content

        if "branch" in filename:
            variables = {variable["name"]: variable for variable in data.get("variables", [])}

            assert variables["branch_name"]["label"] == "Branch Name"
            assert variables["branch_name"]["type"] == "form"
            assert variables["branch_name"]["multiline"] is False
            assert content.count("{{branch_name}}") == 1
            assert "git check-ref-format --branch" in content
            assert "git show-ref --verify --quiet" in content
            assert "Branch name must be a single line." in content
            assert "git switch -c {{branch_name}}" not in content
            assert "Invoke-GitChecked switch -c {{branch_name}}" not in content
            assert 'branch_name="{{branch_name}}"' not in content
            assert "$branchName = '{{branch_name}}'" not in content
            assert "eval " not in content
            assert "Invoke-Expression" not in content
            assert "stash push -u" in content
            assert "Rebase stopped. Resolve conflicts" in content

            if filename.endswith("_sh.json"):
                assert "<<'ESPANSR_BRANCH_NAME:" in content
            else:
                assert "$rawBranchName = @'" in content


def test_bundled_git_branch_helpers_use_popup_form_variable(tmp_path):
    """Git branch helpers use Espanso form variables for branch-name input."""
    from espansr.core.templates import TemplateManager
    from espansr.integrations.espanso import sync_to_espanso

    repo_root = Path(__file__).resolve().parents[1]
    bundled_templates_dir = repo_root / "templates"
    templates_dir = tmp_path / "templates"
    match_dir = tmp_path / "espanso" / "match"
    templates_dir.mkdir()
    match_dir.mkdir(parents=True)

    for filename in ["git_branch_sh.json", "git_branch_ps.json"]:
        (templates_dir / filename).write_text(
            (bundled_templates_dir / filename).read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    manager = TemplateManager(templates_dir=templates_dir)
    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir),
        patch("espansr.integrations.espanso.get_template_manager", return_value=manager),
        patch("espansr.integrations.espanso.validate_all", return_value=[]),
        patch("espansr.integrations.espanso.clean_stale_espanso_files"),
        patch("espansr.integrations.espanso.restart_espanso", return_value=True),
    ):
        result = sync_to_espanso()

    assert result is True
    data = yaml.safe_load((match_dir / "espansr.yml").read_text(encoding="utf-8"))
    matches = {entry["trigger"]: entry for entry in data["matches"]}

    for trigger in [":git-branch-sh", ":git-branch-ps"]:
        entry = matches[trigger]

        assert "{{branch_name.value}}" in entry["replace"]
        assert "{{branch_name}}" not in entry["replace"]
        assert entry["vars"] == [
            {
                "name": "branch_name",
                "type": "form",
                "params": {"layout": "Branch Name: [[value]]"},
            }
        ]


# ── Retirement of removed bundled prompts ────────────────────────────────────

_REMOVED_BUNDLED_FILES = (
    "feat.json",
    "feat_plan.json",
    "feat_runner.json",
    "feedback_loop.json",
    "agent_scaffold.json",
    "merge.json",
    "rebase.json",
    "save.json",
    "pocket_system.json",
    "distill.json",
    "summarize.json",
)


def test_removed_bundled_prompt_files_are_absent():
    """The pruned bundled prompt files no longer ship in the bundled set."""
    templates_dir = Path(__file__).resolve().parents[1] / "templates"
    for filename in _REMOVED_BUNDLED_FILES:
        assert not (templates_dir / filename).exists(), filename


def test_sync_bundled_apply_retires_removed_bundled_prompts(tmp_path, capsys):
    """Previously installed copies of removed prompts are backed up and retired."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    # A surviving bundled prompt keeps the store otherwise in sync.
    verify_template = {"name": "Verify", "content": "verify prompt", "trigger": ":verify"}
    _write_json(bundled_dir / "verify.json", verify_template)
    _write_json(templates_dir / "verify.json", verify_template)
    # Seeded copies of removed prompts, including a historical rename alias.
    _write_json(
        templates_dir / "merge.json",
        {"name": "Merge and Push", "content": "old merge prompt", "trigger": ":merge"},
    )
    _write_json(
        templates_dir / "save.json",
        {"name": "Save Project State", "content": "old save prompt", "trigger": ":save"},
    )
    _write_json(
        templates_dir / "pocket.json",
        {"name": "Pocket", "content": "old pocket prompt", "trigger": ":pocket"},
    )
    _write_json(
        templates_dir / "agent_scaffold.json",
        {"name": "Agent Scaffold", "content": "old scaffold prompt", "trigger": ":agent-scaffold"},
    )
    _write_json(
        templates_dir / "feature_init.json",
        {"name": "Feature Init", "content": "old feature-init prompt", "trigger": ":feature-init"},
    )

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "retired" in output.lower()
    assert not (templates_dir / "merge.json").exists()
    assert not (templates_dir / "save.json").exists()
    assert not (templates_dir / "pocket.json").exists()
    assert not (templates_dir / "agent_scaffold.json").exists()
    assert not (templates_dir / "feature_init.json").exists()

    assert (templates_dir / "_versions" / "merge_and_push" / "v1.json").exists()
    assert (templates_dir / "_versions" / "save_project_state" / "v1.json").exists()
    assert (templates_dir / "_versions" / "pocket" / "v1.json").exists()
    assert (templates_dir / "_versions" / "agent_scaffold" / "v1.json").exists()
    assert (templates_dir / "_versions" / "feature_init" / "v1.json").exists()


def test_sync_bundled_preserves_user_template_reusing_retired_filename(tmp_path):
    """A user template that reuses a retired filename with its own trigger is kept."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    _write_json(
        bundled_dir / "verify.json",
        {"name": "Verify", "content": "verify prompt", "trigger": ":verify"},
    )
    user_merge = {"name": "My Merge", "content": "my own merge helper", "trigger": ":my-merge"}
    _write_json(templates_dir / "merge.json", user_merge)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    assert exit_code == 0
    assert json.loads((templates_dir / "merge.json").read_text(encoding="utf-8")) == user_merge
    assert not (templates_dir / "_versions" / "my_merge").exists()


def test_sync_bundled_retires_distill_and_summarize(tmp_path, capsys):
    """Consolidated :distill and :summarize live copies are backed up and retired."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    explain_bundled = {
        "name": "Explain",
        "content": "unified explain prompt",
        "trigger": ":explain",
    }
    _write_json(bundled_dir / "explain_context_comprehensively.json", explain_bundled)
    _write_json(
        templates_dir / "distill.json",
        {"name": "Context Distiller", "content": "old distill", "trigger": ":distill"},
    )
    _write_json(
        templates_dir / "summarize.json",
        {"name": "Source Summarizer", "content": "old summarize", "trigger": ":summarize"},
    )

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "retired" in output.lower()
    assert not (templates_dir / "distill.json").exists()
    assert not (templates_dir / "summarize.json").exists()
    assert (templates_dir / "explain_context_comprehensively.json").exists()
    explain_triggers = [
        p
        for p in templates_dir.glob("*.json")
        if json.loads(p.read_text(encoding="utf-8")).get("trigger") == ":explain"
    ]
    assert len(explain_triggers) == 1
    assert (templates_dir / "_versions" / "context_distiller" / "v1.json").exists()
    assert (templates_dir / "_versions" / "source_summarizer" / "v1.json").exists()


def test_sync_bundled_preserves_user_distill_and_summarize(tmp_path):
    """User-created distill/summarize files keeping their own triggers are preserved."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    _write_json(
        bundled_dir / "explain_context_comprehensively.json",
        {"name": "Explain", "content": "unified explain prompt", "trigger": ":explain"},
    )
    user_distill = {"name": "My Distiller", "content": "mine", "trigger": ":my-distill"}
    user_summarize = {"name": "My Summary", "content": "mine", "trigger": ":my-summary"}
    _write_json(templates_dir / "distill.json", user_distill)
    _write_json(templates_dir / "summarize.json", user_summarize)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    assert exit_code == 0
    assert json.loads((templates_dir / "distill.json").read_text(encoding="utf-8")) == user_distill
    assert (
        json.loads((templates_dir / "summarize.json").read_text(encoding="utf-8")) == user_summarize
    )


def test_sync_bundled_apply_updates_goal_with_backup(tmp_path):
    """A changed local goal template is backed up before the bundled version replaces it."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    new_goal = {"name": "Goal Refiner", "content": "new goal refiner prompt", "trigger": ":goal"}
    old_goal = {
        "name": "Goal Clarifier",
        "content": "old goal clarifier prompt",
        "trigger": ":goal",
    }
    _write_json(bundled_dir / "goal_clarifier.json", new_goal)
    _write_json(templates_dir / "goal_clarifier.json", old_goal)
    user_only = {"name": "Mine", "content": "keep me", "trigger": ":mine"}
    _write_json(templates_dir / "user_only.json", user_only)

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
    ):
        exit_code = cmd_sync_bundled(_make_args(apply=True, verbose=True))

    assert exit_code == 0
    updated = json.loads((templates_dir / "goal_clarifier.json").read_text(encoding="utf-8"))
    assert updated == new_goal
    preserved = json.loads((templates_dir / "user_only.json").read_text(encoding="utf-8"))
    assert preserved == user_only
    version_path = templates_dir / "_versions" / "goal_clarifier" / "v1.json"
    assert version_path.exists()
    backup = json.loads(version_path.read_text(encoding="utf-8"))
    assert backup["template_data"]["content"] == "old goal clarifier prompt"


def test_publish_path_retires_removed_prompt_and_omits_trigger(tmp_path):
    """The publish path retires a seeded removed prompt and drops it from Espanso YAML."""
    from espansr.core.templates import TemplateManager
    from espansr.integrations.espanso import sync_to_espanso

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    match_dir = tmp_path / "espanso" / "match"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)
    match_dir.mkdir(parents=True)

    _write_json(
        bundled_dir / "verify.json",
        {"name": "Verify", "content": "verify prompt", "trigger": ":verify"},
    )
    _write_json(
        templates_dir / "rebase.json",
        {"name": "Rebase Current Branch", "content": "old rebase prompt", "trigger": ":rebase"},
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
    assert not (templates_dir / "rebase.json").exists()
    assert (templates_dir / "_versions" / "rebase_current_branch" / "v1.json").exists()

    output = yaml.safe_load((match_dir / "espansr.yml").read_text(encoding="utf-8"))
    triggers = {entry["trigger"] for entry in output["matches"]}
    assert ":rebase" not in triggers
    assert ":verify" in triggers
