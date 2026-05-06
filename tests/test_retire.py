"""Tests for first-class template retirement."""

import argparse
import contextlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from espansr.core.templates import TemplateManager


def _args(target: str, dry_run: bool = False) -> argparse.Namespace:
    return argparse.Namespace(target=target, dry_run=dry_run)


@contextlib.contextmanager
def _patched_publish_dependencies(templates_dir: Path, match_dir: Path):
    manager = TemplateManager(templates_dir=templates_dir)
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            patch("espansr.integrations.espanso.get_match_dir", return_value=match_dir)
        )
        stack.enter_context(
            patch("espansr.integrations.espanso.get_template_manager", return_value=manager)
        )
        stack.enter_context(patch("espansr.integrations.espanso.validate_all", return_value=[]))
        stack.enter_context(patch("espansr.integrations.espanso.clean_stale_espanso_files"))
        stack.enter_context(patch("espansr.integrations.espanso.is_windows", return_value=False))
        stack.enter_context(patch("espansr.integrations.espanso.is_wsl2", return_value=False))
        yield


@pytest.mark.parametrize("target", [":target", "Target Template", "target_template.json"])
def test_retire_resolves_exact_trigger_name_or_filename(tmp_path, target):
    """retire accepts the supported exact target forms."""
    from espansr.__main__ import cmd_retire

    templates_dir = tmp_path / "templates"
    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)
    manager = TemplateManager(templates_dir=templates_dir)
    manager.create(name="Target Template", content="remove me", trigger=":target")

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        _patched_publish_dependencies(templates_dir, match_dir),
    ):
        code = cmd_retire(_args(target))

    assert code == 0
    assert not (templates_dir / "target_template.json").exists()
    assert (templates_dir / "_versions" / "target_template" / "v1.json").exists()


def test_retire_dry_run_does_not_delete_or_publish(tmp_path, capsys):
    """--dry-run previews the delete and publish steps without mutating files."""
    from espansr.__main__ import cmd_retire

    templates_dir = tmp_path / "templates"
    manager = TemplateManager(templates_dir=templates_dir)
    manager.create(name="Keep Dry", content="body", trigger=":dry")

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.integrations.espanso.sync_to_espanso") as mock_publish,
    ):
        code = cmd_retire(_args(":dry", dry_run=True))

    output = capsys.readouterr().out.lower()
    assert code == 0
    assert "would back up and delete" in output
    assert "would publish templates to espanso" in output
    assert (templates_dir / "keep_dry.json").exists()
    mock_publish.assert_not_called()


def test_retire_deletes_template_backs_up_and_regenerates_espanso_yaml(tmp_path):
    """Retiring one template removes its trigger from the managed Espanso output."""
    from espansr.__main__ import cmd_retire

    templates_dir = tmp_path / "templates"
    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)
    manager = TemplateManager(templates_dir=templates_dir)
    manager.create(name="Keep", content="stay", trigger=":keep")
    manager.create(name="Old", content="remove", trigger=":old")
    unmanaged = match_dir / "user-owned.yml"
    unmanaged.write_text("matches: []", encoding="utf-8")

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        _patched_publish_dependencies(templates_dir, match_dir),
    ):
        code = cmd_retire(_args(":old"))

    assert code == 0
    assert not (templates_dir / "old.json").exists()
    version_path = templates_dir / "_versions" / "old" / "v1.json"
    assert version_path.exists()
    version_data = json.loads(version_path.read_text(encoding="utf-8"))
    assert version_data["template_data"]["trigger"] == ":old"

    output = yaml.safe_load((match_dir / "espansr.yml").read_text(encoding="utf-8"))
    triggers = {entry["trigger"] for entry in output["matches"]}
    assert triggers == {":keep"}
    assert unmanaged.exists()


def test_retire_last_template_removes_stale_managed_espanso_yaml(tmp_path):
    """Retiring the last triggered template removes the stale managed YAML file."""
    from espansr.__main__ import cmd_retire

    templates_dir = tmp_path / "templates"
    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)
    manager = TemplateManager(templates_dir=templates_dir)
    manager.create(name="Solo", content="remove", trigger=":solo")
    output_file = match_dir / "espansr.yml"
    output_file.write_text(
        yaml.safe_dump({"matches": [{"trigger": ":solo", "replace": "remove"}]}),
        encoding="utf-8",
    )

    with (
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        _patched_publish_dependencies(templates_dir, match_dir),
    ):
        code = cmd_retire(_args(":solo"))

    assert code == 0
    assert not output_file.exists()


def test_retire_ambiguous_filename_requires_specific_path(tmp_path):
    """A filename used in multiple folders is not retired ambiguously."""
    from espansr.__main__ import cmd_retire

    templates_dir = tmp_path / "templates"
    (templates_dir / "a").mkdir(parents=True)
    (templates_dir / "b").mkdir(parents=True)
    for folder, trigger in (("a", ":a"), ("b", ":b")):
        (templates_dir / folder / "shared.json").write_text(
            json.dumps({"name": f"Shared {folder}", "content": folder, "trigger": trigger}),
            encoding="utf-8",
        )

    with patch("espansr.__main__.get_templates_dir", return_value=templates_dir):
        code = cmd_retire(_args("shared.json"))

    assert code == 2
    assert (templates_dir / "a" / "shared.json").exists()
    assert (templates_dir / "b" / "shared.json").exists()
