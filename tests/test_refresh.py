"""Tests for `espansr refresh` and install-metadata recording."""

import json
from pathlib import Path
from unittest.mock import patch

import espansr.__main__ as cli
from espansr.core import install_meta


def _meta_dir(tmp_path: Path) -> Path:
    """Point the config dir at a temp location for isolation."""
    return tmp_path / "espansr"


def _patch_config_dir(tmp_path: Path):
    """Patch get_config_dir in install_meta to a temp dir."""
    target = _meta_dir(tmp_path)
    target.mkdir(parents=True, exist_ok=True)
    return patch.object(install_meta, "get_config_dir", return_value=target)


# ─── install_meta module ─────────────────────────────────────────────────────


def test_installer_for_platform_picks_powershell_on_windows():
    assert install_meta.installer_for_platform("windows") == "install.ps1"
    assert install_meta.installer_for_platform("linux") == "install.sh"
    assert install_meta.installer_for_platform("macos") == "install.sh"
    assert install_meta.installer_for_platform("wsl2") == "install.sh"


def test_record_and_load_round_trip(tmp_path):
    with _patch_config_dir(tmp_path):
        with patch.object(install_meta, "get_platform", return_value="linux"):
            meta = install_meta.record_install_meta(
                tmp_path / "repo", installer="install.sh", venv_dir=tmp_path / ".venv"
            )
        assert meta.platform == "linux"
        assert meta.installer == "install.sh"

        loaded = install_meta.load_install_meta()
    assert loaded is not None
    assert loaded.repo_dir == str(tmp_path / "repo")
    assert loaded.venv_dir == str(tmp_path / ".venv")
    assert loaded.recorded_at  # timestamp present


def test_load_returns_none_when_missing(tmp_path):
    with _patch_config_dir(tmp_path):
        assert install_meta.load_install_meta() is None


def test_load_ignores_corrupt_metadata(tmp_path):
    with _patch_config_dir(tmp_path):
        install_meta.get_install_meta_path().write_text("{ not json", encoding="utf-8")
        assert install_meta.load_install_meta() is None


def test_load_ignores_unknown_fields(tmp_path):
    with _patch_config_dir(tmp_path):
        install_meta.get_install_meta_path().write_text(
            json.dumps(
                {"platform": "linux", "repo_dir": "/x", "installer": "install.sh", "bogus": 1}
            ),
            encoding="utf-8",
        )
        loaded = install_meta.load_install_meta()
    assert loaded is not None
    assert loaded.repo_dir == "/x"


def test_infer_repo_dir_points_at_repository_root():
    repo = install_meta.infer_repo_dir()
    assert repo is not None
    assert (repo / "install.sh").exists()
    assert (repo / "install.ps1").exists()


# ─── record-install command ──────────────────────────────────────────────────


def test_cmd_record_install_writes_metadata(tmp_path):
    args = type(
        "A",
        (),
        {"repo_dir": str(tmp_path / "repo"), "installer": "install.sh", "venv_dir": ""},
    )()
    with _patch_config_dir(tmp_path):
        with patch.object(install_meta, "get_platform", return_value="linux"):
            rc = cli.cmd_record_install(args)
            assert rc == 0
            loaded = install_meta.load_install_meta()
    assert loaded is not None
    assert loaded.repo_dir == str(tmp_path / "repo")


# ─── refresh command ─────────────────────────────────────────────────────────


def _make_args():
    return type("A", (), {})()


def test_refresh_runs_installer_and_notifies_ok(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    meta = install_meta.InstallMeta(platform="linux", repo_dir=str(repo), installer="install.sh")

    class _Result:
        returncode = 0

    with patch.object(cli, "get_platform", return_value="linux"):
        with patch("espansr.core.install_meta.load_install_meta", return_value=meta):
            with patch.object(cli.subprocess, "run", return_value=_Result()) as run:
                with patch.object(cli, "_notify_refresh_ok") as notify:
                    rc = cli.cmd_refresh(_make_args())

    assert rc == 0
    notify.assert_called_once()
    # The installer was launched from the repo folder.
    called = run.call_args
    assert called.kwargs["cwd"] == str(repo)
    assert "install.sh" in called.args[0][-1]


def test_refresh_opens_folder_on_failure(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "install.sh").write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    meta = install_meta.InstallMeta(platform="linux", repo_dir=str(repo), installer="install.sh")

    class _Result:
        returncode = 1

    with patch.object(cli, "get_platform", return_value="linux"):
        with patch("espansr.core.install_meta.load_install_meta", return_value=meta):
            with patch.object(cli.subprocess, "run", return_value=_Result()):
                with patch.object(cli, "_open_install_folder") as opener:
                    rc = cli.cmd_refresh(_make_args())

    assert rc == 1
    opener.assert_called_once_with(repo)


def test_refresh_uses_powershell_on_windows(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "install.ps1").write_text("exit 0", encoding="utf-8")
    meta = install_meta.InstallMeta(platform="windows", repo_dir=str(repo), installer="install.ps1")

    class _Result:
        returncode = 0

    with patch.object(cli, "get_platform", return_value="windows"):
        with patch("espansr.core.install_meta.load_install_meta", return_value=meta):
            with patch.object(cli.subprocess, "run", return_value=_Result()) as run:
                with patch.object(cli, "_notify_refresh_ok"):
                    rc = cli.cmd_refresh(_make_args())

    assert rc == 0
    argv = run.call_args.args[0]
    assert argv[0] == "powershell"
    assert argv[-1].endswith("install.ps1")


def test_refresh_fails_when_installer_missing(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()  # no installer script inside
    meta = install_meta.InstallMeta(platform="linux", repo_dir=str(repo), installer="install.sh")

    with patch.object(cli, "get_platform", return_value="linux"):
        with patch("espansr.core.install_meta.load_install_meta", return_value=meta):
            with patch.object(cli, "_open_install_folder") as opener:
                rc = cli.cmd_refresh(_make_args())

    assert rc == 1
    opener.assert_called_once_with(repo)


def test_refresh_command_is_registered():
    parser = cli._build_parser()
    args = parser.parse_args(["refresh"])
    assert args.command == "refresh"
