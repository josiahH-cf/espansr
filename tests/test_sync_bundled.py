"""Tests for bundled-template drift checking and reconciliation."""

import json
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


def test_sync_bundled_apply_retires_deleted_analysis_starters(tmp_path, capsys):
    """Deleted analysis starters retire into the surviving explain prompt."""
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
            "trigger": ":simplify",
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
        "reality_audit.json": {
            "name": "Reality Audit",
            "content": "old reality prompt",
            "trigger": ":reality",
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
    assert json.loads(
        (templates_dir / "explain_context_comprehensively.json").read_text(encoding="utf-8")
    ) == bundled_template
    for filename in old_templates:
        assert not (templates_dir / filename).exists()

    assert (templates_dir / "_versions" / "plainenglish_explanation" / "v1.json").exists()
    assert (templates_dir / "_versions" / "explain_like_i_am_five" / "v1.json").exists()
    assert (templates_dir / "_versions" / "firstprinciples_analysis" / "v1.json").exists()
    assert (templates_dir / "_versions" / "first_principles_analysis" / "v1.json").exists()
    assert (templates_dir / "_versions" / "reality_audit" / "v1.json").exists()


def test_sync_bundled_apply_consolidates_feature_switcher_starters(tmp_path, capsys):
    """Old project/feature starter prompts retire into the single feat switcher."""
    from espansr.__main__ import cmd_sync_bundled

    bundled_dir = tmp_path / "bundled"
    templates_dir = tmp_path / "config" / "espansr" / "templates"
    bundled_dir.mkdir(parents=True)
    templates_dir.mkdir(parents=True)

    bundled_template = {
        "name": "Feature Switcher",
        "content": "single switcher prompt",
        "trigger": ":feat",
        "replaces": [":project-init", ":feature-new", ":feature-next"],
    }
    old_templates = {
        "project_init.json": {
            "name": "Project Init",
            "content": "old project prompt",
            "trigger": ":project-init",
        },
        "feature_new.json": {
            "name": "Feature New",
            "content": "old new-feature prompt",
            "trigger": ":feature-new",
        },
        "feature_next.json": {
            "name": "Feature Next",
            "content": "old next-feature prompt",
            "trigger": ":feature-next",
        },
    }
    _write_json(bundled_dir / "feat.json", bundled_template)
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
    assert "retired" in output.lower()
    actual_template = json.loads((templates_dir / "feat.json").read_text(encoding="utf-8"))
    assert actual_template == bundled_template
    for filename in old_templates:
        assert not (templates_dir / filename).exists()

    assert (templates_dir / "_versions" / "project_init" / "v1.json").exists()
    assert (templates_dir / "_versions" / "feature_new" / "v1.json").exists()
    assert (templates_dir / "_versions" / "feature_next" / "v1.json").exists()


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


def test_bundled_context_prompts_use_inline_footer_instead_of_variables():
    """Context-bearing starter prompts use inline notes instead of popup variables."""
    repo_root = Path(__file__).resolve().parents[1]
    templates_dir = repo_root / "templates"
    expected = {
        "goal_clarifier.json": (),
        "meta.json": ("context",),
        "context.json": (),
        "template_builder.json": (),
        "feat.json": (),
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
        "feat.json": (
            ":feat",
            "workflow",
            "feature-switcher",
            [":feat", ":verify", ":save"],
            [
                ":project-init",
                ":feature-init",
                ":feature-new",
                ":feature-next",
                ":project-scaffold",
                ":scaffold-feature-process",
                ":feature-scope",
                ":continue",
            ],
        ),
        "visual_workflow.json": (
            ":visual",
            "explanation",
            "visual-workflow",
            [":verify"],
            [],
        ),
        "gaps.json": (
            ":gaps",
            "analysis",
            "gap-review",
            [":verify"],
            [":critique"],
        ),
        "context.json": (":context", "prompting", "context-reset", [":meta", ":verify"], []),
        "template_builder.json": (
            ":template-builder",
            "prompting",
            "template-authoring",
            [":verify", ":context"],
            [],
        ),
        "sanitize.json": (":sanitize", "safety", "scrub", [":verify"], [":hide-ai"]),
        "docs_qa.json": (":docs-qa", "maintenance", "docs-review", [":save"], [":qa"]),
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
    }

    existing_files = {path.name for path in templates_dir.glob("*.json")}
    assert retired_files.isdisjoint(existing_files)

    for path in templates_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["description"]
        assert data["category"]
        assert data["stage"]
        assert "next_triggers" in data

    for filename, (trigger, category, stage, next_triggers, replaces) in expected.items():
        data = json.loads((templates_dir / filename).read_text(encoding="utf-8"))

        assert data["trigger"] == trigger
        assert data["description"]
        assert data["category"] == category
        assert data["stage"] == stage
        assert data["next_triggers"] == next_triggers
        assert data["replaces"] == replaces


def test_bundled_quick_help_uses_renamed_triggers():
    """AC-3: :espansr quick help lists the new prompt chain without stale triggers."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "espansr_help.json").read_text(encoding="utf-8"))
    content = data["content"]

    for trigger in [
        ":explain",
        ":visual",
        ":gaps",
        ":verify",
        ":sanitize",
        ":context",
        ":template-builder",
        ":goal",
        ":feat",
        ":docs-qa",
        ":save",
    ]:
        assert trigger in content

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
        ":reality",
    ]:
        assert stale_trigger not in content


def test_bundled_feat_switcher_template_contract():
    """The feat switcher owns project setup and feature workflow routes."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "feat.json").read_text(encoding="utf-8"))

    content = data["content"]
    variables = {variable["name"]: variable for variable in data.get("variables", [])}

    assert data["trigger"] == ":feat"
    assert data["category"] == "workflow"
    assert data["stage"] == "feature-switcher"
    assert data["next_triggers"] == [":feat", ":verify", ":save"]
    assert data["replaces"] == [
        ":project-init",
        ":feature-init",
        ":feature-new",
        ":feature-next",
        ":project-scaffold",
        ":scaffold-feature-process",
        ":feature-scope",
        ":continue",
    ]
    assert variables == {}
    assert "Route: Project setup" in content
    assert "Route: Feature loop setup" in content
    assert "Route: New feature" in content
    assert "Route: Feature spec" in content
    assert "Route: Next feature" in content
    assert "Would create in reality" in content
    assert "AGENTS.md" in content
    assert "CLAUDE.md" in content
    assert ".github/copilot-instructions.md" in content
    assert "features/STATE.json" in content


def test_bundled_sanitize_template_contract():
    """The sanitize prompt preserves its broader sanitization and planning contract."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "sanitize.json").read_text(encoding="utf-8"))

    content = data["content"]

    assert data["trigger"] == ":sanitize"
    assert data["category"] == "safety"
    assert data["stage"] == "scrub"
    assert data["next_triggers"] == [":verify"]
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


def test_bundled_quick_help_describes_broader_sanitize_role():
    """Quick help should describe sanitize as broader than AI-marker cleanup."""
    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "templates" / "espansr_help.json").read_text(encoding="utf-8"))

    assert (
        ":sanitize         — assess sensitive/internal traces and recommend sanitization"
        in data["content"]
    )
