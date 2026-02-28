"""Tests for setup and platform resilience hardening.

Covers: lru_cache on get_platform()/get_platform_config(), PlatformConfig frozen,
        _get_bundled_dir() importlib.resources fallback, --strict flag, post-copy validation.
Spec: /specs/setup-platform-resilience.md
"""

import json
from pathlib import Path
from unittest.mock import patch

from espansr.core.platform import (
    PlatformConfig,
    get_platform,
    get_platform_config,
)


# ─── Task 1: Platform config caching ─────────────────────────────────────────


def test_get_platform_cached():
    """get_platform() returns the same object on consecutive calls (lru_cache)."""
    with (
        patch("platform.system", return_value="Linux"),
        patch(
            "builtins.open",
            __import__("unittest.mock", fromlist=["mock_open"]).mock_open(
                read_data="Linux version 5.15 generic ubuntu"
            ),
        ),
    ):
        get_platform.cache_clear()
        first = get_platform()
        second = get_platform()
    assert first == second
    assert first is second  # same cached object (string interning aside, identity check)
    get_platform.cache_clear()


def test_get_platform_config_cached():
    """get_platform_config() returns the identical object on repeat calls (lru_cache)."""
    import os

    with (
        patch("espansr.core.platform.get_platform", return_value="linux"),
        patch.dict(os.environ, {}, clear=False),
        patch.object(os.environ, "get", side_effect=lambda k, d=None: d),
    ):
        get_platform_config.cache_clear()
        first = get_platform_config()
        second = get_platform_config()
    assert first is second  # identity — same cached object
    get_platform_config.cache_clear()


def test_platform_config_frozen():
    """PlatformConfig is frozen — attributes cannot be reassigned."""
    import pytest

    pc = PlatformConfig(
        platform="linux",
        espansr_config_dir=Path("/tmp/espansr"),
        espanso_candidate_dirs=[Path("/tmp/espanso")],
    )
    with pytest.raises(AttributeError):
        pc.platform = "windows"


# ─── Task 2: Bundled template path fallback ──────────────────────────────────


def test_bundled_dir_fallback_importlib(tmp_path):
    """_get_bundled_dir() uses importlib.resources when repo-level templates/ is absent."""
    from espansr.__main__ import _get_bundled_dir

    # When the repo-level path doesn't exist, result should still be a valid Path
    # pointing at the package-data location via importlib.resources.
    # We patch __file__ to point somewhere with no sibling templates/ dir.
    fake_main = tmp_path / "espansr" / "__main__.py"
    fake_main.parent.mkdir(parents=True)
    fake_main.touch()

    with patch("espansr.__main__.__file__", str(fake_main)):
        result = _get_bundled_dir()

    # The repo-level path (tmp_path / "templates") doesn't exist,
    # so _get_bundled_dir should have used the importlib fallback.
    # Result must be a Path (may or may not exist in test env, but
    # it should NOT be the non-existent repo-level path).
    assert isinstance(result, Path)
    repo_level = fake_main.resolve().parent.parent / "templates"
    assert result != repo_level or result.is_dir()


def test_bundled_dir_prefers_repo_level(tmp_path):
    """_get_bundled_dir() returns the repo-level path when it exists."""
    from espansr.__main__ import _get_bundled_dir

    # Create a fake repo structure with templates/
    fake_main = tmp_path / "espansr" / "__main__.py"
    fake_main.parent.mkdir(parents=True)
    fake_main.touch()
    (tmp_path / "templates").mkdir()

    with patch("espansr.__main__.__file__", str(fake_main)):
        result = _get_bundled_dir()

    assert result == tmp_path / "templates"


# ─── Task 3: --strict flag and validation step ───────────────────────────────


def _make_bundled_dir(tmp_path: Path) -> Path:
    """Create a fake bundled templates directory with a valid template."""
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


def test_setup_strict_returns_1_without_espanso(tmp_path):
    """espansr setup --strict returns 1 when Espanso config is not detected."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)

    # Simulate argparse namespace with strict=True
    import argparse

    args = argparse.Namespace(strict=True)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        result = cmd_setup(args)

    assert result == 1


def test_setup_strict_returns_0_with_espanso(tmp_path):
    """espansr setup --strict returns 0 when Espanso config is detected."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)
    espanso_dir = tmp_path / "espanso"
    espanso_dir.mkdir()

    import argparse

    args = argparse.Namespace(strict=True)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch(
            "espansr.__main__.get_espanso_config_dir",
            return_value=espanso_dir,
        ),
        patch("espansr.__main__.clean_stale_espanso_files"),
        patch("espansr.__main__.generate_launcher_file", return_value=True),
    ):
        result = cmd_setup(args)

    assert result == 0


def test_setup_without_strict_returns_0_without_espanso(tmp_path):
    """espansr setup (no --strict) still returns 0 when Espanso is missing."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)

    import argparse

    args = argparse.Namespace(strict=False)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        result = cmd_setup(args)

    assert result == 0


def test_setup_validates_copied_templates(tmp_path, capsys):
    """cmd_setup runs validation on copied templates after copying."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"
    bundled_dir = _make_bundled_dir(tmp_path)

    import argparse

    args = argparse.Namespace(strict=False)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled_dir),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        cmd_setup(args)

    output = capsys.readouterr().out
    # Validation step should report on templates — either "valid" or specific issues
    assert "Validation:" in output or "valid" in output.lower()


def test_setup_prints_validation_warnings(tmp_path, capsys):
    """cmd_setup prints validation warnings for templates with issues."""
    from espansr.__main__ import cmd_setup

    config_dir = tmp_path / "config" / "espansr"
    templates_dir = config_dir / "templates"

    # Create a bundled template with a bad trigger (no prefix)
    bundled = tmp_path / "bundled"
    bundled.mkdir()
    (bundled / "bad_template.json").write_text(
        json.dumps(
            {
                "name": "Bad Template",
                "description": "Has a trigger without proper prefix.",
                "trigger": "nocolon",
                "content": "some content with {{unused_var}}",
                "variables": [],
            }
        )
    )

    import argparse

    args = argparse.Namespace(strict=False)

    with (
        patch("espansr.__main__.get_config_dir", return_value=config_dir),
        patch("espansr.__main__.get_templates_dir", return_value=templates_dir),
        patch("espansr.__main__._get_bundled_dir", return_value=bundled),
        patch("espansr.__main__.get_espanso_config_dir", return_value=None),
    ):
        cmd_setup(args)

    output = capsys.readouterr().out
    # Should see warning/error output about the bad trigger
    assert "Bad Template" in output or "nocolon" in output or "Warning" in output
