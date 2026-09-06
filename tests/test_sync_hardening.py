"""Hardening tests for `espansr sync` (`_run_sync`): installer failures
propagate, offline fetch reinstalls the current checkout, a failed stash pop
is fatal, a failed commit surfaces stderr, a missing upstream is reported
distinctly, git timeouts do not produce tracebacks, and the yolo commit lists
the files it recorded."""

import subprocess
from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

import espansr.__main__ as cli


def _cp(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(
        args=["git"], returncode=returncode, stdout=stdout, stderr=stderr
    )


def _git_mock(responses=None, raises=None):
    """Build a ``_git_in`` stand-in.

    ``responses`` maps a leading git-arg tuple (e.g. ``("stash", "pop")``) to a
    CompletedProcess; ``raises`` maps a prefix to an exception to raise.
    Everything else succeeds silently.
    """
    responses = responses or {}
    raises = raises or {}

    def fake(repo_dir, *args, timeout=120):
        for prefix, exc in raises.items():
            if args[: len(prefix)] == prefix:
                raise exc
        for prefix, result in responses.items():
            if args[: len(prefix)] == prefix:
                return result
        return _cp(0)

    return MagicMock(side_effect=fake)


def _subcommands(mock):
    return [tuple(c.args[1:]) for c in mock.call_args_list]


@contextmanager
def _sync_env(repo, git, *, dirty=False, conflicts=(), ahead=True, installer_rc=0):
    patchers = [
        patch.object(cli, "_resolve_install_target", return_value=(repo, "install.sh", "linux")),
        patch.object(cli.shutil, "which", return_value="git"),
        patch.object(cli, "_is_git_worktree", return_value=True),
        patch.object(cli, "_git_in", git),
        patch.object(cli, "_worktree_dirty", return_value=dirty),
        patch.object(cli, "_conflicted_files", return_value=list(conflicts)),
        patch.object(cli, "_ahead_of_upstream", return_value=ahead),
        patch.object(cli, "run_installer", return_value=installer_rc),
    ]
    with ExitStack() as stack:
        entered = [stack.enter_context(p) for p in patchers]
        yield entered[-1]


def test_installer_failure_propagates(tmp_path):
    git = _git_mock()
    with _sync_env(tmp_path, git, installer_rc=1) as installer:
        rc = cli._run_sync(no_push=False)
    assert rc == 1
    installer.assert_called_once()


def test_offline_fetch_reinstalls_current_checkout(tmp_path, capsys):
    git = _git_mock({("fetch",): _cp(128, stderr="fatal: unable to access")})
    with _sync_env(tmp_path, git) as installer:
        rc = cli._run_sync(no_push=False)

    assert rc == 0
    installer.assert_called_once()
    assert "reinstalling current checkout" in capsys.readouterr().out
    assert ("pull", "--rebase") not in _subcommands(git)


def test_fetch_timeout_reinstalls_current_checkout(tmp_path, capsys):
    git = _git_mock(raises={("fetch",): subprocess.TimeoutExpired(["git", "fetch"], 120)})
    with _sync_env(tmp_path, git) as installer:
        rc = cli._run_sync(no_push=False)
    assert rc == 0
    installer.assert_called_once()
    assert "git fetch failed" in capsys.readouterr().out


def test_stash_pop_failure_without_conflict_is_fatal(tmp_path, capsys):
    git = _git_mock(
        {("stash", "pop"): _cp(1, stderr="error: could not restore untracked files from stash")}
    )
    with _sync_env(tmp_path, git, dirty=True) as installer:
        rc = cli._run_sync(no_push=False)

    out = capsys.readouterr().out
    assert rc == 1
    installer.assert_not_called()
    assert "could not restore untracked files" in out
    assert "git stash list" in out
    cmds = _subcommands(git)
    assert ("stash", "push", "-u", "-m", "espansr-sync") in cmds
    assert not any(c[:1] == ("add",) for c in cmds)
    assert not any(c[:1] == ("commit",) for c in cmds)
    assert ("push",) not in cmds


def test_stash_pop_conflict_is_fatal_and_points_at_stash(tmp_path, capsys):
    git = _git_mock({("stash", "pop"): _cp(1, stdout="CONFLICT (content)")})
    with _sync_env(tmp_path, git, dirty=True, conflicts=["a.py"]) as installer:
        rc = cli._run_sync(no_push=False)
    out = capsys.readouterr().out
    assert rc == 1
    installer.assert_not_called()
    assert "conflicted with the update" in out
    assert "git stash list" in out
    assert ("push",) not in _subcommands(git)


def test_commit_failure_surfaces_stderr_and_returns_1(tmp_path, capsys):
    git = _git_mock(
        {("commit",): _cp(128, stderr="Author identity unknown\n*** Please tell me who you are.")}
    )
    with _sync_env(tmp_path, git, dirty=True) as installer:
        rc = cli._run_sync(no_push=False)

    out = capsys.readouterr().out
    assert rc == 1
    installer.assert_not_called()
    assert "Could not commit local changes" in out
    assert "Author identity unknown" in out
    assert ("push",) not in _subcommands(git)


def test_no_upstream_is_reported_distinctly(tmp_path, capsys):
    git = _git_mock()
    with _sync_env(tmp_path, git, ahead=None) as installer:
        rc = cli._run_sync(no_push=False)

    out = capsys.readouterr().out
    assert rc == 0
    installer.assert_called_once()
    assert "No upstream configured; push skipped." in out
    assert "Nothing to push" not in out
    assert ("push",) not in _subcommands(git)


def test_level_with_upstream_prints_nothing_to_push(tmp_path, capsys):
    git = _git_mock()
    with _sync_env(tmp_path, git, ahead=False):
        cli._run_sync(no_push=False)
    assert "Nothing to push." in capsys.readouterr().out


def test_ahead_of_upstream_distinguishes_missing_upstream(tmp_path):
    with patch.object(cli, "_git_in", return_value=_cp(128, stderr="no upstream")):
        assert cli._ahead_of_upstream(tmp_path) is None
    with patch.object(cli, "_git_in", return_value=_cp(0, stdout="0\n")):
        assert cli._ahead_of_upstream(tmp_path) is False
    with patch.object(cli, "_git_in", return_value=_cp(0, stdout="2\n")):
        assert cli._ahead_of_upstream(tmp_path) is True


def test_git_timeout_yields_rc_1_and_message(tmp_path, capsys):
    argv = ["git", "-C", str(tmp_path), "pull", "--rebase"]
    git = _git_mock(raises={("pull", "--rebase"): subprocess.TimeoutExpired(argv, 120)})
    with _sync_env(tmp_path, git, dirty=False) as installer:
        rc = cli._run_sync(no_push=False)

    out = capsys.readouterr().out
    assert rc == 1
    installer.assert_not_called()
    assert "git pull --rebase timed out after 120 s" in out
    assert "Traceback" not in out


def test_git_oserror_yields_rc_1_and_message(tmp_path, capsys):
    git = _git_mock(raises={("stash", "push"): OSError("git vanished")})
    with _sync_env(tmp_path, git, dirty=True) as installer:
        rc = cli._run_sync(no_push=False)
    assert rc == 1
    installer.assert_not_called()
    assert "git failed: git vanished" in capsys.readouterr().out


def test_yolo_commit_lists_committed_files(tmp_path, capsys):
    git = _git_mock(
        {
            ("show", "--name-only", "--format=", "HEAD"): _cp(
                0, stdout="templates/greet.json\nREADME.md\n"
            )
        }
    )
    with _sync_env(tmp_path, git, dirty=True, ahead=True):
        rc = cli._run_sync(no_push=False)

    out = capsys.readouterr().out
    assert rc == 0
    assert "Committed local changes." in out
    committed_index = out.index("Committed:")
    assert "  templates/greet.json\n  README.md\n" in out[committed_index:]
    assert ("show", "--name-only", "--format=", "HEAD") in _subcommands(git)


def test_no_push_skips_commit_and_listing(tmp_path, capsys):
    git = _git_mock()
    with _sync_env(tmp_path, git, dirty=True):
        rc = cli._run_sync(no_push=True)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Committed:" not in out
    assert not any(c[:1] == ("commit",) for c in _subcommands(git))


def test_push_failure_output_masks_credentials(tmp_path, capsys):
    git = _git_mock(
        {
            ("push",): _cp(
                1, stderr="fatal: unable to access 'https://bob:hunter2@example.com/r.git'"
            )
        }
    )
    with _sync_env(tmp_path, git, ahead=True):
        cli._run_sync(no_push=False)
    out = capsys.readouterr().out
    assert "hunter2" not in out
    assert "https://bob:***@example.com/r.git" in out
