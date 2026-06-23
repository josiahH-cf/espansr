"""Tests for `espansr sync` (`_run_sync`) and the `run_installer` refactor."""

import subprocess
from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

import espansr.__main__ as cli


def _cp(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["git"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _git_in_mock(pull=None, push=None):
    """Build a ``_git_in`` stand-in returning canned results for pull/push."""
    pull = pull if pull is not None else _cp(0)
    push = push if push is not None else _cp(0)

    def fake(repo_dir, *args, timeout=120):
        if args[:2] == ("pull", "--rebase"):
            return pull
        if args[:1] == ("push",):
            return push
        return _cp(0)

    return MagicMock(side_effect=fake)


def _args(**kw):
    return type("A", (), kw)()


def _git_subcommands(mock):
    """Return the git arg tuples the mock was called with (without repo_dir)."""
    return [tuple(c.args[1:]) for c in mock.call_args_list]


@contextmanager
def _sync_env(repo, git, *, dirty=False, conflicts=(), ahead=True, worktree=True, installer_rc=0):
    """Patch _run_sync's collaborators; yields the run_installer mock."""
    patchers = [
        patch.object(cli, "_resolve_install_target", return_value=(repo, "install.sh", "linux")),
        patch.object(cli.shutil, "which", return_value="git"),
        patch.object(cli, "_is_git_worktree", return_value=worktree),
        patch.object(cli, "_git_in", git),
        patch.object(cli, "_worktree_dirty", return_value=dirty),
        patch.object(cli, "_conflicted_files", return_value=list(conflicts)),
        patch.object(cli, "_ahead_of_upstream", return_value=ahead),
        patch.object(cli, "run_installer", return_value=installer_rc),
    ]
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patchers]
        yield entered[-1]  # run_installer mock


# ─── parser registration ─────────────────────────────────────────────────────


def test_sync_parses_no_push():
    parser = cli._build_parser()
    assert parser.parse_args(["sync"]).no_push is False
    assert parser.parse_args(["sync", "--no-push"]).no_push is True


def test_configure_remote_desktop_parses_revert():
    parser = cli._build_parser()
    args = parser.parse_args(["configure-remote-desktop", "--revert"])
    assert args.command == "configure-remote-desktop"
    assert args.revert is True


# ─── run_installer refactor ──────────────────────────────────────────────────


def test_cmd_refresh_delegates_to_run_installer(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    with (
        patch.object(cli, "_resolve_install_target", return_value=(repo, "install.sh", "linux")),
        patch.object(cli, "run_installer", return_value=0) as installer,
    ):
        rc = cli.cmd_refresh(_args())
    assert rc == 0
    installer.assert_called_once_with(repo, "install.sh", "linux")


# ─── sync orchestration ──────────────────────────────────────────────────────


def test_sync_clean_pulls_pushes_and_reinstalls(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git = _git_in_mock()
    with _sync_env(repo, git) as installer:
        rc = cli._run_sync(no_push=False)

    assert rc == 0
    installer.assert_called_once_with(repo, "install.sh", "linux")
    cmds = _git_subcommands(git)
    assert ("fetch", "--prune") in cmds
    assert ("pull", "--rebase") in cmds
    assert ("push",) in cmds


def test_sync_no_push_skips_push(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git = _git_in_mock()
    with _sync_env(repo, git) as installer:
        rc = cli._run_sync(no_push=True)

    assert rc == 0
    installer.assert_called_once()
    assert ("push",) not in _git_subcommands(git)


def test_sync_conflict_aborts_and_skips_reinstall(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git = _git_in_mock(pull=_cp(1, stdout="CONFLICT (content): merge conflict in a.py"))
    with _sync_env(repo, git, conflicts=["a.py"]) as installer:
        rc = cli._run_sync(no_push=False)

    assert rc == 1
    installer.assert_not_called()
    cmds = _git_subcommands(git)
    assert ("rebase", "--abort") in cmds
    assert ("push",) not in cmds


def test_sync_push_failure_is_nonfatal(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git = _git_in_mock(push=_cp(1, stderr="rejected"))
    with _sync_env(repo, git) as installer:
        rc = cli._run_sync(no_push=False)

    assert rc == 0  # reinstall still runs; push failure is non-fatal
    installer.assert_called_once()


def test_sync_not_a_git_repo_reinstalls_only(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git = MagicMock()
    with _sync_env(repo, git, worktree=False) as installer:
        rc = cli._run_sync(no_push=False)

    assert rc == 0
    installer.assert_called_once_with(repo, "install.sh", "linux")
    git.assert_not_called()


def test_sync_dirty_tree_stashes_and_pops(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git = _git_in_mock()
    with _sync_env(repo, git, dirty=True, ahead=False) as installer:
        rc = cli._run_sync(no_push=False)

    assert rc == 0
    cmds = _git_subcommands(git)
    assert ("stash", "push", "-u", "-m", "espansr-sync") in cmds
    assert ("stash", "pop") in cmds
    installer.assert_called_once()


# ─── configure-remote-desktop command ────────────────────────────────────────


def test_cmd_configure_remote_desktop_applies():
    with patch("espansr.integrations.espanso.apply_remote_desktop_config", return_value=True) as ap:
        rc = cli.cmd_configure_remote_desktop(_args(revert=False))
    assert rc == 0
    ap.assert_called_once_with(revert=False)


def test_cmd_configure_remote_desktop_revert_passes_flag():
    with patch("espansr.integrations.espanso.apply_remote_desktop_config", return_value=True) as ap:
        rc = cli.cmd_configure_remote_desktop(_args(revert=True))
    assert rc == 0
    ap.assert_called_once_with(revert=True)


def test_cmd_configure_remote_desktop_reports_failure():
    with patch("espansr.integrations.espanso.apply_remote_desktop_config", return_value=False):
        rc = cli.cmd_configure_remote_desktop(_args(revert=False))
    assert rc == 1
