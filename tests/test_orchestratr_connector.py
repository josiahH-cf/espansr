"""Tests for espansr ↔ orchestratr connector.

Covers: manifest generation, status --json output, setup integration,
WSL2 launch commands, and passive behavior when orchestratr is absent.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_config_env(tmp_path: Path, *, templates: int = 1, espanso: bool = True):
    """Set up a fake espansr config directory with optional templates and espanso.

    Returns (config_dir, templates_dir, espanso_dir_or_none).
    """
    config_dir = tmp_path / "espansr"
    config_dir.mkdir(parents=True)
    templates_dir = config_dir / "templates"
    templates_dir.mkdir()

    for i in range(templates):
        (templates_dir / f"tmpl_{i}.json").write_text(
            json.dumps(
                {
                    "name": f"Template {i}",
                    "trigger": f":t{i}",
                    "content": f"Content {i}",
                }
            )
        )

    espanso_dir = None
    if espanso:
        espanso_dir = tmp_path / "espanso"
        espanso_dir.mkdir()

    return config_dir, templates_dir, espanso_dir


# ─── AC 1: Manifest generation ──────────────────────────────────────────────


class TestManifestGeneration:
    """orchestratr.yml is generated in the config directory."""

    def test_generate_manifest_writes_yaml(self, tmp_path):
        """generate_manifest() creates orchestratr.yml in the config dir."""
        from espansr.integrations.orchestratr import generate_manifest

        config_dir = tmp_path / "espansr"
        config_dir.mkdir()

        result = generate_manifest(config_dir)

        manifest_path = config_dir / "orchestratr.yml"
        assert manifest_path.exists()
        assert result == manifest_path

    def test_manifest_content_matches_schema(self, tmp_path):
        """Manifest contains required fields matching the orchestratr app registry schema."""
        from espansr.integrations.orchestratr import generate_manifest

        config_dir = tmp_path / "espansr"
        config_dir.mkdir()

        generate_manifest(config_dir)

        manifest = yaml.safe_load((config_dir / "orchestratr.yml").read_text())
        assert manifest["name"] == "espansr"
        assert "description" in manifest
        assert "version" in manifest
        assert "launch" in manifest
        assert "command" in manifest["launch"]
        assert manifest["ready_cmd"] == "espansr status --json"
        assert manifest["ready_timeout_ms"] == 3000
        assert "hotkey" in manifest
        assert manifest["hotkey"]["suggested_chord"] == "e"

    def test_manifest_version_matches_package(self, tmp_path):
        """Manifest version field matches espansr.__version__."""
        from espansr import __version__
        from espansr.integrations.orchestratr import generate_manifest

        config_dir = tmp_path / "espansr"
        config_dir.mkdir()

        generate_manifest(config_dir)

        manifest = yaml.safe_load((config_dir / "orchestratr.yml").read_text())
        assert manifest["version"] == __version__


# ─── AC 3: status --json ────────────────────────────────────────────────────


class TestStatusJson:
    """espansr status --json outputs machine-readable status."""

    def test_status_json_ok(self, tmp_path):
        """status --json returns ok status when templates and espanso are present."""
        from espansr.integrations.orchestratr import get_status_json

        config_dir, templates_dir, espanso_dir = _make_config_env(
            tmp_path, templates=3, espanso=True
        )

        with (
            patch(
                "espansr.integrations.orchestratr.get_config_dir",
                return_value=config_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_templates_dir",
                return_value=templates_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_espanso_config_dir",
                return_value=espanso_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_config",
                return_value=_make_config_stub(last_sync="2025-01-15T10:30:00Z"),
            ),
        ):
            result = get_status_json()

        data = json.loads(result)
        assert data["status"] == "ok"
        assert data["template_count"] == 3
        assert data["espanso_synced"] is True
        assert data["config_dir"] == str(config_dir)
        assert "version" in data

    def test_status_json_degraded(self, tmp_path):
        """status --json returns degraded status when espanso is missing."""
        from espansr.integrations.orchestratr import get_status_json

        config_dir, templates_dir, _ = _make_config_env(
            tmp_path, templates=0, espanso=False
        )

        with (
            patch(
                "espansr.integrations.orchestratr.get_config_dir",
                return_value=config_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_templates_dir",
                return_value=templates_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_espanso_config_dir",
                return_value=None,
            ),
            patch(
                "espansr.integrations.orchestratr.get_config",
                return_value=_make_config_stub(last_sync=""),
            ),
        ):
            result = get_status_json()

        data = json.loads(result)
        assert data["status"] == "degraded"
        assert data["espanso_synced"] is False
        assert data["template_count"] == 0
        assert "errors" in data
        assert len(data["errors"]) > 0

    def test_status_json_includes_version(self, tmp_path):
        """status --json always includes the espansr version."""
        from espansr import __version__
        from espansr.integrations.orchestratr import get_status_json

        config_dir, templates_dir, espanso_dir = _make_config_env(tmp_path)

        with (
            patch(
                "espansr.integrations.orchestratr.get_config_dir",
                return_value=config_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_templates_dir",
                return_value=templates_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_espanso_config_dir",
                return_value=espanso_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_config",
                return_value=_make_config_stub(last_sync="2025-01-15T10:30:00Z"),
            ),
        ):
            result = get_status_json()

        data = json.loads(result)
        assert data["version"] == __version__

    def test_status_json_includes_last_sync(self, tmp_path):
        """status --json includes last_sync from config."""
        from espansr.integrations.orchestratr import get_status_json

        config_dir, templates_dir, espanso_dir = _make_config_env(tmp_path)

        with (
            patch(
                "espansr.integrations.orchestratr.get_config_dir",
                return_value=config_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_templates_dir",
                return_value=templates_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_espanso_config_dir",
                return_value=espanso_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_config",
                return_value=_make_config_stub(last_sync="2025-06-01T12:00:00Z"),
            ),
        ):
            result = get_status_json()

        data = json.loads(result)
        assert data["last_sync"] == "2025-06-01T12:00:00Z"


# ─── AC 5: ready_cmd in manifest ────────────────────────────────────────────


class TestReadyCmd:
    """Manifest includes a ready_cmd for orchestratr polling."""

    def test_manifest_has_ready_cmd(self, tmp_path):
        """ready_cmd field is present and executable."""
        from espansr.integrations.orchestratr import generate_manifest

        config_dir = tmp_path / "espansr"
        config_dir.mkdir()

        generate_manifest(config_dir)

        manifest = yaml.safe_load((config_dir / "orchestratr.yml").read_text())
        assert "ready_cmd" in manifest
        assert "espansr status --json" in manifest["ready_cmd"]


# ─── AC 6: Passive behavior ─────────────────────────────────────────────────


class TestPassiveBehavior:
    """espansr behavior is unchanged when orchestratr is absent."""

    def test_generate_manifest_is_idempotent(self, tmp_path):
        """Calling generate_manifest twice produces identical output."""
        from espansr.integrations.orchestratr import generate_manifest

        config_dir = tmp_path / "espansr"
        config_dir.mkdir()

        generate_manifest(config_dir)
        content_first = (config_dir / "orchestratr.yml").read_text()

        generate_manifest(config_dir)
        content_second = (config_dir / "orchestratr.yml").read_text()

        assert content_first == content_second

    def test_status_json_works_without_manifest(self, tmp_path):
        """get_status_json works even when orchestratr.yml doesn't exist."""
        from espansr.integrations.orchestratr import get_status_json

        config_dir, templates_dir, espanso_dir = _make_config_env(tmp_path)

        with (
            patch(
                "espansr.integrations.orchestratr.get_config_dir",
                return_value=config_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_templates_dir",
                return_value=templates_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_espanso_config_dir",
                return_value=espanso_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_config",
                return_value=_make_config_stub(last_sync="2025-01-15T10:30:00Z"),
            ),
        ):
            result = get_status_json()

        # Should return valid JSON regardless of manifest presence
        data = json.loads(result)
        assert "status" in data


# ─── AC 7: Setup regenerates manifest ───────────────────────────────────────


class TestSetupIntegration:
    """espansr setup regenerates the orchestratr manifest."""

    def test_setup_generates_manifest(self, tmp_path, capsys):
        """cmd_setup calls manifest generation and prints confirmation."""
        from espansr.__main__ import cmd_setup

        config_dir = tmp_path / "config" / "espansr"
        templates_dir = config_dir / "templates"
        templates_dir.mkdir(parents=True)
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        with (
            patch("espansr.__main__.get_config_dir", return_value=config_dir),
            patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
            patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
            patch("espansr.__main__.get_espanso_config_dir", return_value=None),
        ):
            result = cmd_setup(None)

        assert result == 0
        manifest = config_dir / "orchestratr.yml"
        assert manifest.exists()

        output = capsys.readouterr().out
        assert "orchestratr" in output.lower()

    def test_setup_regenerates_outdated_manifest(self, tmp_path, capsys):
        """cmd_setup overwrites manifest when version has changed."""
        from espansr.__main__ import cmd_setup

        config_dir = tmp_path / "config" / "espansr"
        templates_dir = config_dir / "templates"
        templates_dir.mkdir(parents=True)
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        # Write an outdated manifest
        manifest_path = config_dir / "orchestratr.yml"
        manifest_path.write_text(
            yaml.dump({"name": "espansr", "version": "0.0.0"})
        )

        with (
            patch("espansr.__main__.get_config_dir", return_value=config_dir),
            patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
            patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
            patch("espansr.__main__.get_espanso_config_dir", return_value=None),
        ):
            result = cmd_setup(None)

        assert result == 0
        manifest = yaml.safe_load(manifest_path.read_text())
        # Version should now match current espansr version, not "0.0.0"
        from espansr import __version__

        assert manifest["version"] == __version__

    def test_setup_skips_manifest_when_current(self, tmp_path, capsys):
        """cmd_setup does not rewrite manifest when version is current."""
        from espansr import __version__
        from espansr.__main__ import cmd_setup

        config_dir = tmp_path / "config" / "espansr"
        templates_dir = config_dir / "templates"
        templates_dir.mkdir(parents=True)
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        # Write a current manifest
        from espansr.integrations.orchestratr import generate_manifest

        generate_manifest(config_dir)
        original_mtime = (config_dir / "orchestratr.yml").stat().st_mtime

        import time

        time.sleep(0.05)  # Ensure mtime would differ if rewritten

        with (
            patch("espansr.__main__.get_config_dir", return_value=config_dir),
            patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
            patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
            patch("espansr.__main__.get_espanso_config_dir", return_value=None),
        ):
            cmd_setup(None)

        new_mtime = (config_dir / "orchestratr.yml").stat().st_mtime
        assert new_mtime == original_mtime


# ─── AC 3 (CLI): status --json via argparse ─────────────────────────────────


class TestStatusJsonCli:
    """espansr status --json works end-to-end through the CLI handler."""

    def test_cmd_status_json_flag(self, tmp_path, capsys):
        """cmd_status with --json prints valid JSON to stdout."""
        from espansr.__main__ import cmd_status

        config_dir, templates_dir, espanso_dir = _make_config_env(tmp_path)

        args = _make_args(json_output=True)

        with (
            patch(
                "espansr.__main__.get_config_dir",
                return_value=config_dir,
            ),
            patch(
                "espansr.__main__.get_templates_dir",
                return_value=templates_dir,
            ),
            patch(
                "espansr.__main__.get_espanso_config_dir",
                return_value=espanso_dir,
            ),
            patch(
                "espansr.__main__.get_config",
                return_value=_make_config_stub(last_sync="2025-01-15T10:30:00Z"),
            ),
        ):
            result = cmd_status(args)

        assert result == 0
        output = capsys.readouterr().out.strip()
        data = json.loads(output)
        assert "version" in data
        assert "status" in data

    def test_cmd_status_without_json(self, tmp_path, capsys):
        """cmd_status without --json prints human-readable output (unchanged behavior)."""
        from espansr.__main__ import cmd_status

        _, _, espanso_dir = _make_config_env(tmp_path)

        args = _make_args(json_output=False)

        with (
            patch(
                "espansr.__main__.get_espanso_config_dir",
                return_value=espanso_dir,
            ),
            patch("shutil.which", return_value="/usr/bin/espanso"),
            patch("espansr.__main__.get_platform", return_value="linux"),
        ):
            result = cmd_status(args)

        assert result == 0
        output = capsys.readouterr().out
        # Human-readable output should NOT be JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(output)

    def test_status_parser_accepts_json_flag(self):
        """The argparse parser accepts --json for the status subcommand."""
        from espansr.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["status", "--json"])
        assert args.json is True

    def test_status_parser_defaults_no_json(self):
        """The argparse parser defaults --json to False for status."""
        from espansr.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["status"])
        assert args.json is False


# ─── WSL2 manifest ───────────────────────────────────────────────────────────


class TestWsl2Manifest:
    """WSL2 environments produce cross-environment launch commands."""

    def test_wsl2_manifest_uses_wsl_exe(self, tmp_path):
        """On WSL2, launch command uses wsl.exe wrapper."""
        from espansr.integrations.orchestratr import generate_manifest

        config_dir = tmp_path / "espansr"
        config_dir.mkdir()

        with (
            patch(
                "espansr.integrations.orchestratr.get_platform",
                return_value="wsl2",
            ),
            patch(
                "espansr.integrations.orchestratr.get_wsl_distro_name",
                return_value="Ubuntu",
            ),
        ):
            generate_manifest(config_dir)

        manifest = yaml.safe_load((config_dir / "orchestratr.yml").read_text())
        assert "wsl.exe" in manifest["launch"]["command"]
        assert "Ubuntu" in manifest["launch"]["command"]

    def test_wsl2_ready_cmd_uses_wsl_exe(self, tmp_path):
        """On WSL2, ready_cmd uses wsl.exe wrapper."""
        from espansr.integrations.orchestratr import generate_manifest

        config_dir = tmp_path / "espansr"
        config_dir.mkdir()

        with (
            patch(
                "espansr.integrations.orchestratr.get_platform",
                return_value="wsl2",
            ),
            patch(
                "espansr.integrations.orchestratr.get_wsl_distro_name",
                return_value="Ubuntu",
            ),
        ):
            generate_manifest(config_dir)

        manifest = yaml.safe_load((config_dir / "orchestratr.yml").read_text())
        assert "wsl.exe" in manifest["ready_cmd"]


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_args(**kwargs):
    """Create a simple namespace to simulate argparse output."""
    import types

    return types.SimpleNamespace(**kwargs)


def _make_config_stub(last_sync: str = ""):
    """Create a minimal config stub with espanso.last_sync set."""
    import types

    espanso = types.SimpleNamespace(last_sync=last_sync)
    return types.SimpleNamespace(espanso=espanso)
