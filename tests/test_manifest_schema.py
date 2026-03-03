"""Tests for manifest schema alignment + cross-platform path resolution.

Spec: /specs/manifest-schema-alignment.md

Covers:
- Flat YAML schema matching orchestratr's AppEntry
- Manifest written to orchestratr's apps.d/ directory
- Cross-platform path resolution (Linux, macOS, WSL2)
- Bare commands (no wsl.exe wrapping)
- Old manifest cleanup
- orchestratr-not-installed graceful skip
- dry-run support for new manifest logic
"""

import json
from pathlib import Path
from unittest.mock import patch

import yaml

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_config_env(tmp_path: Path, *, templates: int = 1, espanso: bool = True):
    """Set up a fake espansr config directory with optional templates and espanso."""
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


def _make_args(**kwargs):
    """Create a simple namespace to simulate argparse output."""
    import types

    return types.SimpleNamespace(**kwargs)


def _make_config_stub(last_sync: str = ""):
    """Create a minimal config stub with espanso.last_sync set."""
    import types

    espanso = types.SimpleNamespace(last_sync=last_sync)
    return types.SimpleNamespace(espanso=espanso)


# ─── AC 1: Flat YAML schema ─────────────────────────────────────────────────


class TestFlatManifestSchema:
    """Generated manifest uses flat YAML matching orchestratr's AppEntry schema."""

    def test_manifest_has_flat_top_level_keys(self, tmp_path):
        """Manifest contains name, chord, command, environment, description,
        ready_cmd, ready_timeout_ms — all at top level, no nested objects."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            result = generate_manifest(apps_dir)

        manifest = yaml.safe_load(result.read_text())
        assert manifest["name"] == "espansr"
        assert manifest["chord"] == "e"
        assert manifest["command"] == "espansr gui"
        assert manifest["environment"] == "native"
        assert "description" in manifest
        assert manifest["ready_cmd"] == "espansr status --json"
        assert manifest["ready_timeout_ms"] == 3000

    def test_manifest_has_no_nested_objects(self, tmp_path):
        """Manifest must not contain nested launch.* or hotkey.* structures."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            generate_manifest(apps_dir)

        manifest = yaml.safe_load((apps_dir / "espansr.yml").read_text())
        assert "launch" not in manifest
        assert "hotkey" not in manifest
        assert "version" not in manifest

    def test_manifest_no_version_field(self, tmp_path):
        """Manifest does not include a version field (not in orchestratr schema)."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            generate_manifest(apps_dir)

        manifest = yaml.safe_load((apps_dir / "espansr.yml").read_text())
        assert "version" not in manifest


# ─── AC 2: Manifest filename is espansr.yml in apps.d/ ──────────────────────


class TestManifestFilename:
    """Manifest is written as espansr.yml in apps.d/ directory."""

    def test_manifest_filename_is_espansr_yml(self, tmp_path):
        """Output file is named espansr.yml (not orchestratr.yml)."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            result = generate_manifest(apps_dir)

        assert result.name == "espansr.yml"
        assert result.parent == apps_dir


# ─── AC 3–5: Cross-platform path resolution ─────────────────────────────────


class TestResolveOrchestratrAppsDir:
    """resolve_orchestratr_apps_dir() returns the correct path per platform."""

    def test_linux_apps_dir(self, tmp_path):
        """On Linux: ~/.config/orchestratr/apps.d/"""
        from espansr.integrations.orchestratr import resolve_orchestratr_apps_dir

        orchestratr_dir = tmp_path / ".config" / "orchestratr"
        orchestratr_dir.mkdir(parents=True)

        with (
            patch(
                "espansr.integrations.orchestratr.get_platform",
                return_value="linux",
            ),
            patch.dict("os.environ", {"XDG_CONFIG_HOME": str(tmp_path / ".config")}),
        ):
            result = resolve_orchestratr_apps_dir()

        assert result == orchestratr_dir / "apps.d"

    def test_linux_environment_native(self, tmp_path):
        """On Linux, environment is 'native'."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            generate_manifest(apps_dir)

        manifest = yaml.safe_load((apps_dir / "espansr.yml").read_text())
        assert manifest["environment"] == "native"

    def test_wsl2_apps_dir(self, tmp_path):
        """On WSL2: /mnt/c/Users/<username>/AppData/Roaming/orchestratr/apps.d/"""
        from espansr.integrations.orchestratr import resolve_orchestratr_apps_dir

        win_user = "testuser"
        orchestratr_dir = (
            tmp_path / "mnt" / "c" / "Users" / win_user
            / "AppData" / "Roaming" / "orchestratr"
        )
        orchestratr_dir.mkdir(parents=True)

        with (
            patch(
                "espansr.integrations.orchestratr.get_platform",
                return_value="wsl2",
            ),
            patch(
                "espansr.integrations.orchestratr.get_windows_username",
                return_value=win_user,
            ),
            patch(
                "espansr.integrations.orchestratr._wsl2_orchestratr_base",
                return_value=orchestratr_dir,
            ),
        ):
            result = resolve_orchestratr_apps_dir()

        assert result == orchestratr_dir / "apps.d"

    def test_wsl2_environment_wsl(self, tmp_path):
        """On WSL2, environment is 'wsl'."""
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

    def test_macos_apps_dir(self, tmp_path):
        """On macOS: ~/Library/Application Support/orchestratr/apps.d/"""
        from espansr.integrations.orchestratr import resolve_orchestratr_apps_dir

        orchestratr_dir = tmp_path / "Library" / "Application Support" / "orchestratr"
        orchestratr_dir.mkdir(parents=True)

        with (
            patch(
                "espansr.integrations.orchestratr.get_platform",
                return_value="macos",
            ),
            patch("pathlib.Path.home", return_value=tmp_path),
        ):
            result = resolve_orchestratr_apps_dir()

        assert result == orchestratr_dir / "apps.d"

    def test_macos_environment_native(self, tmp_path):
        """On macOS, environment is 'native'."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="macos",
        ):
            generate_manifest(apps_dir)

        manifest = yaml.safe_load((apps_dir / "espansr.yml").read_text())
        assert manifest["environment"] == "native"

    def test_orchestratr_not_installed_returns_none(self, tmp_path):
        """Returns None when orchestratr base directory doesn't exist."""
        from espansr.integrations.orchestratr import resolve_orchestratr_apps_dir

        with (
            patch(
                "espansr.integrations.orchestratr.get_platform",
                return_value="linux",
            ),
            patch.dict("os.environ", {"XDG_CONFIG_HOME": str(tmp_path / ".config")}),
        ):
            # Don't create the orchestratr directory
            result = resolve_orchestratr_apps_dir()

        assert result is None


# ─── AC 6–7: Bare commands (no wsl.exe wrapping) ────────────────────────────


class TestBareCommands:
    """command and ready_cmd are always bare (no wsl.exe wrapping)."""

    def test_command_is_bare_on_wsl2(self, tmp_path):
        """On WSL2, command is 'espansr gui' — not wrapped with wsl.exe."""
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

    def test_ready_cmd_is_bare_on_wsl2(self, tmp_path):
        """On WSL2, ready_cmd is 'espansr status --json' — not wrapped."""
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

    def test_command_is_bare_on_linux(self, tmp_path):
        """On Linux, command is the bare 'espansr gui'."""
        from espansr.integrations.orchestratr import generate_manifest

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            generate_manifest(apps_dir)

        manifest = yaml.safe_load((apps_dir / "espansr.yml").read_text())
        assert manifest["command"] == "espansr gui"


# ─── AC 8–9: Setup integration ──────────────────────────────────────────────


class TestSetupOrchestratrIntegration:
    """espansr setup writes manifest to apps.d/ with proper feedback."""

    def test_setup_prints_registered_message(self, tmp_path, capsys):
        """Setup prints 'Registered with orchestratr at <path>' on success."""
        from espansr.__main__ import cmd_setup

        config_dir = tmp_path / "config" / "espansr"
        templates_dir = config_dir / "templates"
        templates_dir.mkdir(parents=True)
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

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
        output = capsys.readouterr().out
        assert "Registered with orchestratr" in output

    def test_setup_skips_when_orchestratr_not_installed(self, tmp_path, capsys):
        """Setup prints info message and continues when orchestratr is not found."""
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
            patch(
                "espansr.integrations.orchestratr.resolve_orchestratr_apps_dir",
                return_value=None,
            ),
        ):
            result = cmd_setup(None)

        assert result == 0
        output = capsys.readouterr().out
        assert "orchestratr not found" in output.lower() or "skipping" in output.lower()


# ─── AC 10: manifest_needs_update detects old schema ────────────────────────


class TestManifestNeedsUpdate:
    """manifest_needs_update() detects schema changes from old nested format."""

    def test_detects_old_nested_format(self, tmp_path):
        """Old nested manifest (launch.command) triggers regeneration."""
        from espansr.integrations.orchestratr import manifest_needs_update

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)
        manifest_path = apps_dir / "espansr.yml"
        old_manifest = {
            "name": "espansr",
            "version": "1.1.0",
            "launch": {"command": "espansr gui"},
            "hotkey": {"suggested_chord": "e"},
        }
        manifest_path.write_text(yaml.dump(old_manifest))

        assert manifest_needs_update(apps_dir) is True

    def test_current_flat_manifest_is_up_to_date(self, tmp_path):
        """A properly-formatted flat manifest does not need updating."""
        from espansr.integrations.orchestratr import generate_manifest, manifest_needs_update

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            generate_manifest(apps_dir)

        with patch(
            "espansr.integrations.orchestratr.get_platform",
            return_value="linux",
        ):
            assert manifest_needs_update(apps_dir) is False

    def test_missing_manifest_needs_update(self, tmp_path):
        """Missing manifest triggers regeneration."""
        from espansr.integrations.orchestratr import manifest_needs_update

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        assert manifest_needs_update(apps_dir) is True


# ─── AC 11: dry-run support ─────────────────────────────────────────────────


class TestDryRunManifest:
    """espansr setup --dry-run shows what would be written without writing."""

    def test_dry_run_shows_manifest_path(self, tmp_path, capsys):
        """--dry-run prints the path where manifest would be written."""
        from espansr.__main__ import cmd_setup

        config_dir = tmp_path / "config" / "espansr"
        templates_dir = config_dir / "templates"
        templates_dir.mkdir(parents=True)
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        apps_dir = tmp_path / "orchestratr" / "apps.d"
        apps_dir.mkdir(parents=True)

        args = _make_args(strict=False, dry_run=True, verbose=False)

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
            cmd_setup(args)

        output = capsys.readouterr().out
        assert "dry-run" in output.lower()
        assert "orchestratr" in output.lower()
        # Must NOT actually write the file
        assert not (apps_dir / "espansr.yml").exists()


# ─── AC (cleanup): Old manifest removal ─────────────────────────────────────


class TestOldManifestCleanup:
    """Old manifest at espansr config dir is cleaned up after writing new one."""

    def test_old_manifest_deleted_after_new_written(self, tmp_path, capsys):
        """Old orchestratr.yml in espansr config dir is removed after new manifest."""
        from espansr.__main__ import cmd_setup

        config_dir = tmp_path / "config" / "espansr"
        templates_dir = config_dir / "templates"
        templates_dir.mkdir(parents=True)
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

        # Create old manifest in espansr config dir
        old_manifest = config_dir / "orchestratr.yml"
        old_manifest.write_text(yaml.dump({"name": "espansr", "version": "0.0.0"}))

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
            cmd_setup(None)

        assert not old_manifest.exists(), "Old manifest should be deleted"
        output = capsys.readouterr().out
        assert "cleaned up" in output.lower() or "removed" in output.lower()

    def test_no_error_when_old_manifest_absent(self, tmp_path, capsys):
        """No error when there's no old manifest to clean up."""
        from espansr.__main__ import cmd_setup

        config_dir = tmp_path / "config" / "espansr"
        templates_dir = config_dir / "templates"
        templates_dir.mkdir(parents=True)
        bundled_dir = tmp_path / "bundled"
        bundled_dir.mkdir()

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
