"""Tests for --dry-run and --verbose CLI flags.

Covers: espansr sync --dry-run, espansr setup --dry-run, espansr setup --verbose,
combined flags, and argparse help registration.
"""

import json
from pathlib import Path
from unittest.mock import patch


def _make_bundled_dir(tmp_path: Path) -> Path:
    """Create a fake bundled templates directory with one template."""
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    (bundled / "espansr_help.json").write_text(
        json.dumps(
            {
                "name": "Espansr Quick Help",
                "description": "Quick reference for espansr CLI commands.",
                "trigger": ":espansr",
                "content": "espansr commands: list, sync, status",
            }
        )
    )
    return bundled


def _make_args(**kwargs):
    """Create a simple argparse-like namespace object."""
    import argparse

    defaults = {"dry_run": False, "verbose": False, "strict": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


# ─── sync --dry-run ──────────────────────────────────────────────────────────


def test_sync_dry_run_no_file_written(tmp_path):
    """sync --dry-run must not write espansr.yml to the match directory."""
    from espansr.integrations.espanso import sync_to_espanso

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)
    output_file = match_dir / "espansr.yml"

    # Provide a template with a trigger so sync has something to write
    class _Stub:
        name = "Test"
        trigger = ":test"
        content = "hello"
        variables = []

    class _ManagerStub:
        def iter_with_triggers(self):
            return iter([_Stub()])

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.get_template_manager",
            return_value=_ManagerStub(),
        ),
        patch("espansr.integrations.espanso.validate_all", return_value=[]),
        patch("espansr.integrations.espanso.clean_stale_espanso_files"),
    ):
        result = sync_to_espanso(dry_run=True)

    assert result is True or (hasattr(result, "success") and result.success)
    assert not output_file.exists(), "dry-run must not create espansr.yml"


def test_sync_dry_run_exit_zero(tmp_path):
    """cmd_sync with --dry-run returns exit code 0."""
    from espansr.__main__ import cmd_sync

    class _Stub:
        name = "Test"
        trigger = ":test"
        content = "hello"
        variables = []

    class _ManagerStub:
        def iter_with_triggers(self):
            return iter([_Stub()])

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.get_template_manager",
            return_value=_ManagerStub(),
        ),
        patch("espansr.integrations.espanso.validate_all", return_value=[]),
        patch("espansr.integrations.espanso.clean_stale_espanso_files"),
    ):
        exit_code = cmd_sync(_make_args(dry_run=True))

    assert exit_code == 0


def test_sync_dry_run_lists_files(tmp_path, capsys):
    """sync --dry-run output mentions the file that would be written."""
    from espansr.integrations.espanso import sync_to_espanso

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    class _Stub:
        name = "Test"
        trigger = ":test"
        content = "hello"
        variables = []

    class _ManagerStub:
        def iter_with_triggers(self):
            return iter([_Stub()])

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.get_template_manager",
            return_value=_ManagerStub(),
        ),
        patch("espansr.integrations.espanso.validate_all", return_value=[]),
        patch("espansr.integrations.espanso.clean_stale_espanso_files"),
    ):
        sync_to_espanso(dry_run=True)

    output = capsys.readouterr().out
    assert "espansr.yml" in output
    assert "dry" in output.lower() or "would" in output.lower()


# ─── setup --dry-run ─────────────────────────────────────────────────────────


def test_setup_dry_run_no_copy(tmp_path):
    """setup --dry-run must not copy templates or generate launcher."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)
    espanso_dir = tmp_path / "espanso"
    espanso_dir.mkdir()

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch(
            "espansr.__main__.get_espanso_config_dir",
            return_value=espanso_dir,
        ),
        patch("espansr.__main__.clean_stale_espanso_files") as mock_clean,
        patch("espansr.__main__.generate_launcher_file") as mock_launcher,
    ):
        result = cmd_setup(_make_args(dry_run=True))

    assert result == 0
    assert not (templates_dir / "espansr_help.json").exists(), "dry-run must not copy templates"
    mock_clean.assert_not_called()
    mock_launcher.assert_not_called()


def test_setup_dry_run_prints_plan(tmp_path, capsys):
    """setup --dry-run output describes what would happen."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        cmd_setup(_make_args(dry_run=True))

    output = capsys.readouterr().out
    # Must mention dry-run and what would be done
    assert "would" in output.lower() or "dry" in output.lower()
    assert "espansr_help.json" in output or "template" in output.lower()


# ─── setup --verbose ─────────────────────────────────────────────────────────


def test_setup_verbose_per_file(tmp_path, capsys):
    """setup --verbose prints one line per template with a reason."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    templates_dir.mkdir(parents=True)
    bundled_dir = _make_bundled_dir(tmp_path)

    # Pre-create one file so we get a "skipped" reason
    (templates_dir / "espansr_help.json").write_text('{"name": "existing"}')

    # Add a second bundled template that doesn't exist yet
    (bundled_dir / "extra.json").write_text(
        json.dumps({"name": "Extra", "trigger": ":extra", "content": "extra"})
    )

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        cmd_setup(_make_args(verbose=True))

    output = capsys.readouterr().out
    # Should mention both files and their disposition
    assert "espansr_help.json" in output
    assert "extra.json" in output
    # Should explain why one was skipped
    assert "skip" in output.lower() or "already exists" in output.lower()


# ─── Combined flags ──────────────────────────────────────────────────────────


def test_setup_dry_run_verbose_combined(tmp_path, capsys):
    """--dry-run and --verbose can be used together on setup."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        result = cmd_setup(_make_args(dry_run=True, verbose=True))

    assert result == 0
    # Must not write any files
    assert not (templates_dir / "espansr_help.json").exists()

    output = capsys.readouterr().out
    # Should show per-file detail and dry-run indication
    assert "espansr_help.json" in output
    assert "would" in output.lower() or "dry" in output.lower()


# ─── Argparse registration ───────────────────────────────────────────────────


def test_flags_in_help(capsys):
    """--dry-run and --verbose appear in sync and setup help text."""
    import sys

    from espansr.__main__ import main

    # Test sync --help
    for subcmd in ("sync", "setup"):
        try:
            sys.argv = ["espansr", subcmd, "--help"]
            main()
        except SystemExit:
            pass

        output = capsys.readouterr().out
        assert "--dry-run" in output, f"--dry-run missing from {subcmd} help"

    # --verbose only on setup
    try:
        sys.argv = ["espansr", "setup", "--help"]
        main()
    except SystemExit:
        pass

    output = capsys.readouterr().out
    assert "--verbose" in output, "--verbose missing from setup help"
