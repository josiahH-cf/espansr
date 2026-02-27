"""Tests for Espanso path consolidation and stale file cleanup.

Covers: path persistence in get_espanso_config_dir(), stale file cleanup,
candidate path enumeration, and cleanup integration with sync.
"""

import logging
from pathlib import Path
from unittest.mock import patch

# ─── Path persistence tests ──────────────────────────────────────────────────


def test_get_espanso_config_dir_persists_resolved_path(tmp_path):
    """After auto-detection, get_espanso_config_dir() persists the path to config."""
    from espansr.core.config import ConfigManager

    # Set up a fake Espanso config dir
    espanso_dir = tmp_path / "espanso_config"
    espanso_dir.mkdir()

    # Set up a ConfigManager with a temp config file
    cm = ConfigManager(config_path=tmp_path / "config.json")
    config = cm.config
    assert config.espanso.config_path == ""  # starts empty

    with (
        patch("espansr.integrations.espanso.get_config", return_value=config),
        patch("espansr.integrations.espanso.save_config") as mock_save,
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        patch("platform.system", return_value="Linux"),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[espanso_dir],
        ),
    ):
        from espansr.integrations.espanso import get_espanso_config_dir

        result = get_espanso_config_dir()

    assert result == espanso_dir
    assert config.espanso.config_path == str(espanso_dir)
    mock_save.assert_called_once_with(config)


def test_get_espanso_config_dir_uses_persisted_path_without_reprobing(tmp_path):
    """When config_path is already set and valid, skip auto-detection."""
    from espansr.core.config import ConfigManager

    espanso_dir = tmp_path / "espanso_config"
    espanso_dir.mkdir()

    cm = ConfigManager(config_path=tmp_path / "config.json")
    config = cm.config
    config.espanso.config_path = str(espanso_dir)

    with (
        patch("espansr.integrations.espanso.get_config", return_value=config),
        patch("espansr.integrations.espanso.save_config") as mock_save,
        patch("espansr.integrations.espanso.is_wsl2") as mock_wsl,
    ):
        from espansr.integrations.espanso import get_espanso_config_dir

        result = get_espanso_config_dir()

    assert result == espanso_dir
    # Should NOT call save (path already persisted) or is_wsl2 (no re-probing)
    mock_save.assert_not_called()
    mock_wsl.assert_not_called()


def test_get_espanso_config_dir_redetects_when_persisted_path_missing(tmp_path):
    """When config_path points to a nonexistent dir, fall back to auto-detection."""
    from espansr.core.config import ConfigManager

    # Persisted path doesn't exist
    gone_dir = tmp_path / "gone"

    # Real Espanso dir does exist
    real_dir = tmp_path / "real_espanso"
    real_dir.mkdir()

    cm = ConfigManager(config_path=tmp_path / "config.json")
    config = cm.config
    config.espanso.config_path = str(gone_dir)

    with (
        patch("espansr.integrations.espanso.get_config", return_value=config),
        patch("espansr.integrations.espanso.save_config") as mock_save,
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        patch("platform.system", return_value="Linux"),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[real_dir],
        ),
    ):
        from espansr.integrations.espanso import get_espanso_config_dir

        result = get_espanso_config_dir()

    assert result == real_dir
    assert config.espanso.config_path == str(real_dir)
    # Called twice: once to clear stale path, once to persist new path
    assert mock_save.call_count == 2


def test_get_espanso_config_dir_clears_stale_path_when_no_candidates(tmp_path):
    """When persisted path is gone and no candidates exist, stale value is cleared."""
    from espansr.core.config import ConfigManager

    gone_dir = tmp_path / "gone"

    cm = ConfigManager(config_path=tmp_path / "config.json")
    config = cm.config
    config.espanso.config_path = str(gone_dir)

    with (
        patch("espansr.integrations.espanso.get_config", return_value=config),
        patch("espansr.integrations.espanso.save_config") as mock_save,
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        patch("platform.system", return_value="Linux"),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[],
        ),
    ):
        from espansr.integrations.espanso import get_espanso_config_dir

        result = get_espanso_config_dir()

    assert result is None
    assert config.espanso.config_path == ""
    # save_config called once to clear the stale value
    mock_save.assert_called_once_with(config)


# ─── Candidate path enumeration tests ────────────────────────────────────────


def test_get_candidate_paths_linux(tmp_path):
    """_get_candidate_paths() returns Linux paths when not WSL2."""
    with (
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        patch("platform.system", return_value="Linux"),
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        from espansr.integrations.espanso import _get_candidate_paths

        paths = _get_candidate_paths()

    # Should include standard Linux paths
    assert tmp_path / ".config" / "espanso" in paths
    assert tmp_path / ".espanso" in paths


def test_get_candidate_paths_wsl2_includes_windows(tmp_path):
    """_get_candidate_paths() includes Windows-side paths on WSL2."""
    with (
        patch("espansr.integrations.espanso.is_wsl2", return_value=True),
        patch(
            "espansr.integrations.espanso.get_windows_username",
            return_value="TestUser",
        ),
        patch("platform.system", return_value="Linux"),
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        from espansr.integrations.espanso import _get_candidate_paths

        paths = _get_candidate_paths()

    # Should include WSL2 Windows-side paths
    assert Path("/mnt/c/Users/TestUser/.config/espanso") in paths
    assert Path("/mnt/c/Users/TestUser/.espanso") in paths
    assert Path("/mnt/c/Users/TestUser/AppData/Roaming/espanso") in paths
    # Should also include Linux-side paths
    assert tmp_path / ".config" / "espanso" in paths


def test_get_candidate_paths_macos(tmp_path):
    """_get_candidate_paths() returns macOS paths on Darwin."""
    with (
        patch("espansr.integrations.espanso.is_wsl2", return_value=False),
        patch("platform.system", return_value="Darwin"),
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        from espansr.integrations.espanso import _get_candidate_paths

        paths = _get_candidate_paths()

    assert tmp_path / "Library" / "Application Support" / "espanso" in paths
    assert tmp_path / ".config" / "espanso" in paths


# ─── Stale file cleanup tests ────────────────────────────────────────────────


def test_clean_stale_deletes_managed_files_from_noncanonical(tmp_path):
    """clean_stale_espanso_files() removes managed files from non-canonical dirs."""
    canonical = tmp_path / "canonical" / "match"
    canonical.mkdir(parents=True)

    stale_dir = tmp_path / "stale" / "match"
    stale_dir.mkdir(parents=True)

    # Create managed files in stale location
    (stale_dir / "espansr.yml").write_text("matches: []")
    (stale_dir / "espansr-launcher.yml").write_text("matches: []")

    with (
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            return_value=tmp_path / "canonical",
        ),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[tmp_path / "canonical", tmp_path / "stale"],
        ),
    ):
        from espansr.integrations.espanso import clean_stale_espanso_files

        clean_stale_espanso_files()

    assert not (stale_dir / "espansr.yml").exists()
    assert not (stale_dir / "espansr-launcher.yml").exists()


def test_clean_stale_preserves_canonical_files(tmp_path):
    """clean_stale_espanso_files() does not delete files from the canonical dir."""
    canonical = tmp_path / "canonical" / "match"
    canonical.mkdir(parents=True)

    # Create managed files in canonical location
    (canonical / "espansr.yml").write_text("matches: []")
    (canonical / "espansr-launcher.yml").write_text("matches: []")

    with (
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            return_value=tmp_path / "canonical",
        ),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[tmp_path / "canonical"],
        ),
    ):
        from espansr.integrations.espanso import clean_stale_espanso_files

        clean_stale_espanso_files()

    assert (canonical / "espansr.yml").exists()
    assert (canonical / "espansr-launcher.yml").exists()


def test_clean_stale_does_not_delete_user_files(tmp_path):
    """clean_stale_espanso_files() only removes espansr-managed file names."""
    stale_dir = tmp_path / "stale" / "match"
    stale_dir.mkdir(parents=True)

    # Create a user-authored file and a managed file
    (stale_dir / "my-custom-triggers.yml").write_text("matches: []")
    (stale_dir / "espansr.yml").write_text("matches: []")

    canonical = tmp_path / "canonical"
    canonical.mkdir()

    with (
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            return_value=canonical,
        ),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[canonical, tmp_path / "stale"],
        ),
    ):
        from espansr.integrations.espanso import clean_stale_espanso_files

        clean_stale_espanso_files()

    # User file preserved, managed file removed
    assert (stale_dir / "my-custom-triggers.yml").exists()
    assert not (stale_dir / "espansr.yml").exists()


def test_clean_stale_silent_on_permission_error(tmp_path, caplog):
    """clean_stale_espanso_files() logs warning but doesn't crash on PermissionError."""
    stale_dir = tmp_path / "stale" / "match"
    stale_dir.mkdir(parents=True)

    stale_file = stale_dir / "espansr.yml"
    stale_file.write_text("matches: []")

    canonical = tmp_path / "canonical"
    canonical.mkdir()

    with (
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            return_value=canonical,
        ),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[canonical, tmp_path / "stale"],
        ),
        patch("pathlib.Path.unlink", side_effect=PermissionError("access denied")),
        caplog.at_level(logging.WARNING),
    ):
        from espansr.integrations.espanso import clean_stale_espanso_files

        # Should not raise
        clean_stale_espanso_files()

    # Should have logged a warning
    assert any("permission" in record.message.lower() or "access denied" in record.message.lower() for record in caplog.records)


def test_clean_stale_handles_no_canonical_dir(tmp_path):
    """clean_stale_espanso_files() does nothing when no canonical dir is found."""
    stale_dir = tmp_path / "stale" / "match"
    stale_dir.mkdir(parents=True)
    (stale_dir / "espansr.yml").write_text("matches: []")

    with (
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            return_value=None,
        ),
    ):
        from espansr.integrations.espanso import clean_stale_espanso_files

        # Should not raise, and should not delete anything (no canonical to compare against)
        clean_stale_espanso_files()

    # File should still exist — we can't clean without knowing what's canonical
    assert (stale_dir / "espansr.yml").exists()


# ─── Integration: cleanup called before sync ──────────────────────────────────


def test_sync_calls_cleanup_before_write(tmp_path):
    """sync_to_espanso() calls clean_stale_espanso_files() before writing."""
    from espansr.core.templates import TemplateManager

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    with (
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.get_template_manager"
        ) as mock_mgr,
        patch(
            "espansr.integrations.espanso.clean_stale_espanso_files"
        ) as mock_clean,
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=templates_dir)

        from espansr.integrations.espanso import sync_to_espanso

        sync_to_espanso()

    mock_clean.assert_called_once()


def test_espanso_manager_sync_calls_cleanup(tmp_path):
    """EspansoManager.sync() calls clean_stale_espanso_files() before writing."""
    from espansr.core.templates import TemplateManager

    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()

    match_dir = tmp_path / "espanso" / "match"
    match_dir.mkdir(parents=True)

    with (
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            return_value=tmp_path / "espanso",
        ),
        patch(
            "espansr.integrations.espanso.get_match_dir",
            return_value=match_dir,
        ),
        patch(
            "espansr.integrations.espanso.get_template_manager"
        ) as mock_mgr,
        patch(
            "espansr.integrations.espanso.clean_stale_espanso_files"
        ) as mock_clean,
    ):
        mock_mgr.return_value = TemplateManager(templates_dir=templates_dir)

        from espansr.integrations.espanso import EspansoManager

        manager = EspansoManager()
        manager.sync()

    mock_clean.assert_called_once()


def test_clean_stale_skips_nonexistent_match_dirs(tmp_path):
    """clean_stale_espanso_files() skips candidates whose match/ dir doesn't exist."""
    canonical = tmp_path / "canonical"
    canonical.mkdir()

    # This candidate exists but has no match/ dir
    no_match = tmp_path / "no_match_dir"
    no_match.mkdir()

    # This candidate doesn't exist at all
    nonexistent = tmp_path / "nonexistent"

    with (
        patch(
            "espansr.integrations.espanso.get_espanso_config_dir",
            return_value=canonical,
        ),
        patch(
            "espansr.integrations.espanso._get_candidate_paths",
            return_value=[canonical, no_match, nonexistent],
        ),
    ):
        from espansr.integrations.espanso import clean_stale_espanso_files

        # Should not raise
        clean_stale_espanso_files()
