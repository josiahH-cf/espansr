"""`espansr setup` reports launcher/popup/sync-trigger generation truthfully and
fails (exit 1) when Espanso is present but publishing or generation failed."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from espansr.__main__ import cmd_setup
from espansr.core.platform import ShimResult


@pytest.fixture(autouse=True)
def _no_real_shim_mutation(monkeypatch):
    monkeypatch.setattr(
        "espansr.core.platform.ensure_command_shim",
        lambda *a, **kw: ShimResult(
            path=Path("/tmp/fake-shim/espansr"),
            target=Path("/tmp/fake-target"),
            status="unchanged",
            message="patched in test",
        ),
    )
    monkeypatch.setattr("espansr.core.platform.is_user_bin_on_path", lambda *a, **kw: True)


def _bundled(tmp_path: Path) -> Path:
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    (bundled / "espansr_help.json").write_text(
        json.dumps({"name": "Help", "trigger": ":espansr", "content": "help"})
    )
    return bundled


def _run(tmp_path, *, espanso_dir, launcher=True, popup=True, sync_file=True, publish=True):
    config_dir = tmp_path / "config" / "espansr"
    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=config_dir / "templates"),
        patch("espansr.__main__._get_bundled_dir", return_value=_bundled(tmp_path)),
        patch("espansr.__main__.get_espanso_config_dir", return_value=espanso_dir),
        patch("espansr.__main__.clean_stale_espanso_files"),
        patch("espansr.__main__.generate_launcher_file", return_value=launcher),
        patch("espansr.__main__.generate_commands_popup_file", return_value=popup),
        patch("espansr.__main__.generate_sync_file", return_value=sync_file),
        patch("espansr.integrations.espanso.sync_to_espanso", return_value=publish),
    ):
        return cmd_setup(None)


def test_setup_reports_generated_items_and_succeeds(tmp_path, capsys):
    espanso_dir = tmp_path / "espanso"
    espanso_dir.mkdir()
    assert _run(tmp_path, espanso_dir=espanso_dir) == 0
    out = capsys.readouterr().out
    assert "Launcher: generated" in out
    assert "Commands popup: generated" in out
    assert "Sync trigger: generated" in out
    assert "failed" not in out


def test_setup_reports_failed_launcher_and_returns_1(tmp_path, capsys):
    espanso_dir = tmp_path / "espanso"
    espanso_dir.mkdir()
    assert _run(tmp_path, espanso_dir=espanso_dir, launcher=False) == 1
    out = capsys.readouterr().out
    assert "Launcher: failed" in out
    assert "Commands popup: generated" in out
    assert "Sync trigger: generated" in out
    assert "Launcher: generated" not in out


def test_setup_reports_failed_sync_trigger_and_returns_1(tmp_path, capsys):
    espanso_dir = tmp_path / "espanso"
    espanso_dir.mkdir()
    assert _run(tmp_path, espanso_dir=espanso_dir, sync_file=False) == 1
    assert "Sync trigger: failed" in capsys.readouterr().out


def test_setup_publish_failure_returns_1(tmp_path, capsys):
    espanso_dir = tmp_path / "espanso"
    espanso_dir.mkdir()
    assert _run(tmp_path, espanso_dir=espanso_dir, publish=False) == 1
    out = capsys.readouterr().out
    assert "Publish: failed" in out
    # The remaining steps still run so the report is complete.
    assert "Command shim:" in out


def test_setup_without_espanso_skips_and_returns_0(tmp_path, capsys):
    assert _run(tmp_path, espanso_dir=None) == 0
    out = capsys.readouterr().out
    assert "Launcher: skipped (no Espanso config)" in out
    assert "Commands popup: skipped (no Espanso config)" in out
    assert "Sync trigger: skipped (no Espanso config)" in out
