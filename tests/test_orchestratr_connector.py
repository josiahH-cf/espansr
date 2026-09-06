"""Tests for espansr ↔ orchestratr connector.

Covers: manifest generation, status --json output, setup integration,
flat AppEntry schema, and passive behavior when orchestratr is absent.
"""

import json
import os
from unittest.mock import patch

import pytest
import yaml

from tests.orchestratr_helpers import (
    _make_args,
    _make_bundled_dir,
    _make_config_env,
    _make_config_stub,
)

# ─── AC 1: Manifest generation ──────────────────────────────────────────────


class TestManifestGeneration:
    """espansr.yml is generated in the apps.d/ directory with flat schema."""

    def test_generate_manifest_writes_yaml(self, tmp_path):
        """generate_manifest() creates espansr.yml in the apps.d/ dir."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        result = generate_manifest(apps_dir)

        manifest_path = apps_dir / "espansr.yml"
        assert manifest_path.exists()
        assert result == manifest_path

    def test_manifest_content_matches_flat_schema(self, tmp_path):
        """Manifest contains flat top-level fields matching orchestratr AppEntry."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            generate_manifest(apps_dir)

        manifest = yaml.safe_load((apps_dir / "espansr.yml").read_text())
        assert manifest["name"] == "espansr"
        assert manifest["chord"] == "e"
        assert manifest["command"] == "espansr gui"
        assert manifest["environment"] == "native"
        assert "description" in manifest
        assert manifest["ready_cmd"] == "espansr status --json"
        assert manifest["ready_timeout_ms"] == 3000
        # No nested objects or version
        assert "launch" not in manifest
        assert "hotkey" not in manifest
        assert "version" not in manifest


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

        config_dir, templates_dir, _ = _make_config_env(tmp_path, templates=0, espanso=False)

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

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            generate_manifest(apps_dir)

        manifest = yaml.safe_load((apps_dir / "espansr.yml").read_text())
        assert "ready_cmd" in manifest
        assert manifest["ready_cmd"] == "espansr status --json"


# ─── AC 6: Passive behavior ─────────────────────────────────────────────────


class TestPassiveBehavior:
    """espansr behavior is unchanged when orchestratr is absent."""

    def test_generate_manifest_is_idempotent(self, tmp_path):
        """Calling generate_manifest twice produces identical output."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            generate_manifest(apps_dir)
            content_first = (apps_dir / "espansr.yml").read_text()

            generate_manifest(apps_dir)
            content_second = (apps_dir / "espansr.yml").read_text()

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
    """espansr setup registers with orchestratr via apps.d/."""

    def test_setup_generates_manifest(self, tmp_path, capsys):
        """cmd_setup calls manifest generation and prints confirmation."""
        from espansr.__main__ import cmd_setup

        config_dir = tmp_path / "config" / "espansr"
        templates_dir = config_dir / "templates"
        templates_dir.mkdir(parents=True)
        bundled_dir = _make_bundled_dir(tmp_path)

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with (
            patch("espansr.__main__.get_config_dir", return_value=config_dir),
            patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
            patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
            patch("espansr.__main__.get_espanso_config_dir", return_value=None),
            patch(
                "espansr.integrations.orchestratr.resolve_orchestratr_apps_dir",
                return_value=apps_dir,
            ),
        ):
            result = cmd_setup(None)

        assert result == 0
        manifest = apps_dir / "espansr.yml"
        assert manifest.exists()

        output = capsys.readouterr().out
        assert "Registered with orchestratr" in output

    def test_setup_regenerates_outdated_manifest(self, tmp_path, capsys):
        """cmd_setup overwrites manifest when schema has changed."""
        from espansr.__main__ import cmd_setup

        config_dir = tmp_path / "config" / "espansr"
        templates_dir = config_dir / "templates"
        templates_dir.mkdir(parents=True)
        bundled_dir = _make_bundled_dir(tmp_path)

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        # Write an old nested-format manifest
        manifest_path = apps_dir / "espansr.yml"
        manifest_path.write_text(
            yaml.dump({"name": "espansr", "version": "0.0.0", "launch": {"command": "espansr gui"}})
        )

        with (
            patch("espansr.__main__.get_config_dir", return_value=config_dir),
            patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
            patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
            patch("espansr.__main__.get_espanso_config_dir", return_value=None),
            patch(
                "espansr.integrations.orchestratr.resolve_orchestratr_apps_dir",
                return_value=apps_dir,
            ),
        ):
            result = cmd_setup(None)

        assert result == 0
        manifest = yaml.safe_load(manifest_path.read_text())
        # Should now be flat schema — no nested objects
        assert "chord" in manifest
        assert "launch" not in manifest

    def test_setup_skips_manifest_when_current(self, tmp_path, capsys):
        """cmd_setup does not rewrite manifest when it matches current schema."""
        from espansr.__main__ import cmd_setup

        config_dir = tmp_path / "config" / "espansr"
        templates_dir = config_dir / "templates"
        templates_dir.mkdir(parents=True)
        bundled_dir = _make_bundled_dir(tmp_path)

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        # Write a current flat-format manifest using a consistent platform mock
        from espansr.integrations.orchestratr import generate_manifest

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            generate_manifest(apps_dir)
        manifest_path = apps_dir / "espansr.yml"
        # Pin an obviously stale mtime: any rewrite would replace it with "now".
        stale_mtime = 1_000_000_000
        os.utime(manifest_path, (stale_mtime, stale_mtime))

        with (
            patch("espansr.__main__.get_config_dir", return_value=config_dir),
            patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
            patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
            patch("espansr.__main__.get_espanso_config_dir", return_value=None),
            patch(
                "espansr.integrations.orchestratr.resolve_orchestratr_apps_dir",
                return_value=apps_dir,
            ),
            patch(
                "espansr.integrations.orchestratr.get_platform",
                return_value="linux",
            ),
        ):
            cmd_setup(None)

        assert manifest_path.stat().st_mtime == stale_mtime


# ─── AC 3 (CLI): status --json via argparse ─────────────────────────────────


class TestStatusJsonCli:
    """espansr status --json works end-to-end through the CLI handler."""

    def test_cmd_status_json_flag(self, tmp_path, capsys):
        """cmd_status with --json prints valid JSON to stdout."""
        from espansr.__main__ import cmd_status

        config_dir, templates_dir, espanso_dir = _make_config_env(tmp_path)

        args = _make_args(json=True)

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

        args = _make_args(json=False)

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
    """WSL2 environments produce environment: wsl with bare commands."""

    def test_wsl2_manifest_has_wsl_environment(self, tmp_path):
        """On WSL2, environment field is 'wsl'."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="wsl2",
        ):
            generate_manifest(apps_dir)

        manifest = yaml.safe_load((apps_dir / "espansr.yml").read_text())
        assert manifest["environment"] == "wsl"

    def test_wsl2_command_is_bare(self, tmp_path):
        """On WSL2, command is bare 'espansr gui' — not wrapped with wsl.exe."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="wsl2",
        ):
            generate_manifest(apps_dir)

        manifest = yaml.safe_load((apps_dir / "espansr.yml").read_text())
        assert manifest["command"] == "espansr gui"
        assert "wsl.exe" not in manifest["command"]

    def test_wsl2_ready_cmd_is_bare(self, tmp_path):
        """On WSL2, ready_cmd is bare — not wrapped with wsl.exe."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="wsl2",
        ):
            generate_manifest(apps_dir)

        manifest = yaml.safe_load((apps_dir / "espansr.yml").read_text())
        assert manifest["ready_cmd"] == "espansr status --json"
        assert "wsl.exe" not in manifest["ready_cmd"]
