"""What `espansr sync` and the template push check is exactly what Git publishes.

Real Git with local bare remotes. Sync asks Git which refs its configured push
updates (push.default, remote.<name>.push, pushRemote, followTags), checks every
one of them against what each destination URL lacks, and pushes exactly the
checked objects; a push it cannot check ref by ref is refused with the reason.
"""

import json
import subprocess
from pathlib import Path

import pytest

import espansr.__main__ as cli
from espansr.core import remote as remote_module
from espansr.core.config import Config, ConfigManager
from espansr.core.remote import RemoteError, RemoteManager

SECRET = "PRIVATE-PUSH-SCOPE-6203"
PRIVATE = {
    "name": "Private",
    "trigger": ":private",
    "content": f"{SECRET} body",
    "local_only": True,
}


@pytest.fixture(autouse=True)
def git_identity(monkeypatch):
    for key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(key, "espansr test")
    for key in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(key, "test@example.invalid")


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(repo: Path, rel: str, data) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _holds_secret(bare: Path) -> bool:
    objects = [t for t in _git(bare, "rev-list", "--objects", "--all").split() if len(t) == 40]
    batch = subprocess.run(
        ["git", "-C", str(bare), "cat-file", "--batch"],
        input="\n".join(objects).encode() + b"\n",
        capture_output=True,
        check=True,
    ).stdout
    return SECRET.encode() in batch


def _refs(bare: Path) -> dict:
    out = _git(bare, "for-each-ref", "--format=%(refname) %(objectname)")
    return dict(line.split() for line in out.splitlines())


def _bare(tmp_path: Path, name: str) -> Path:
    bare = tmp_path / f"{name}.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    return bare


@pytest.fixture()
def world(tmp_path):
    """A checkout on main tracking origin/main, with public.txt and a shared template."""
    origin, repo = _bare(tmp_path, "origin"), tmp_path / "work"
    _git(tmp_path, "init", "-q", "-b", "main", str(repo))
    _write(repo, "public.txt", "base\n")
    _write(repo, "templates/shared.json", {"name": "Shared", "trigger": ":s", "content": "s"})
    _commit(repo, "base")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-q", "-u", "origin", "main")
    return repo, origin


def _other(repo: Path, *, private: bool) -> str:
    """Branch other, pushed at the base, then one unpushed commit on it."""
    _git(repo, "branch", "other")
    _git(repo, "push", "-q", "origin", "other")
    _git(repo, "checkout", "-q", "other")
    if private:
        _write(repo, "templates/private.json", PRIVATE)
    else:
        _write(repo, "templates/other.json", {"name": "Other", "trigger": ":o", "content": "o"})
    oid = _commit(repo, "other work")
    _git(repo, "checkout", "-q", "main")
    return oid


def _main_ahead(repo: Path) -> str:
    _write(repo, "public.txt", "changed\n")
    return _commit(repo, "safe change")


def _sync(repo: Path) -> bool:
    return cli._sync_repository(repo, no_push=False)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("push.default", "matching"),
        ("remote.origin.push", "refs/heads/other:refs/heads/other"),
    ],
)
def test_a_configured_push_of_a_private_branch_sends_nothing_and_says_which(
    world, capsys, key, value
):
    """The supervisor's cases: the current branch is safe, other carries a private commit."""
    repo, origin = world
    _other(repo, private=True)
    _main_ahead(repo)
    _git(repo, "config", key, value)
    before = _refs(origin)

    assert _sync(repo) is True  # the reinstall still runs

    assert _refs(origin) == before
    assert not _holds_secret(origin)
    out = capsys.readouterr().out
    setting = "push.default=matching" if key == "push.default" else "remote.origin.push"
    assert f"templates/private.json (in refs/heads/other, which {setting} pushes)" in out
    assert "Take those commits out of other" in out


def test_a_matching_push_sends_every_matching_branch_once_each_is_checked(world, capsys):
    repo, origin = world
    other = _other(repo, private=False)
    main = _main_ahead(repo)
    _git(repo, "config", "push.default", "matching")

    assert _sync(repo) is True

    refs = _refs(origin)
    assert (refs["refs/heads/main"], refs["refs/heads/other"]) == (main, other)
    assert "Pushed to origin as push.default=matching does: main, other." in capsys.readouterr().out


def test_a_push_refspec_sends_what_it_maps_and_says_this_branch_stays(world, capsys):
    repo, origin = world
    before = _refs(origin)["refs/heads/main"]
    other = _other(repo, private=False)
    _main_ahead(repo)
    _git(repo, "config", "remote.origin.push", "refs/heads/other:refs/heads/other")

    assert _sync(repo) is True

    assert _refs(origin)["refs/heads/other"] == other
    assert _refs(origin)["refs/heads/main"] == before  # Git's own push would not send main
    out = capsys.readouterr().out
    assert "Not pushed: remote.origin.push does not push refs/heads/main to origin." in out


@pytest.mark.parametrize(
    "settings",
    [
        {},
        {"push.default": "simple"},
        {"push.default": "upstream"},
        {"push.default": "current"},
        {"remote.origin.push": "refs/heads/main:refs/heads/main"},
        {"remote.origin.push": "HEAD"},
    ],
)
def test_an_ordinary_sync_pushes_the_branch_as_before(world, capsys, settings):
    repo, origin = world
    for key, value in settings.items():
        _git(repo, "config", key, value)
    main = _main_ahead(repo)

    assert _sync(repo) is True

    assert _refs(origin) == {"refs/heads/main": main}
    assert _git(repo, "rev-parse", "origin/main") == main
    assert "Pushed local changes." in capsys.readouterr().out


def test_follow_tags_pushes_the_followed_tag_explicitly(world, capsys):
    repo, origin = world
    main = _main_ahead(repo)
    _git(repo, "tag", "-a", "-m", "release", "v1")
    _git(repo, "config", "push.followTags", "true")

    assert _sync(repo) is True

    assert _refs(origin) == {"refs/heads/main": main, "refs/tags/v1": _git(repo, "rev-parse", "v1")}
    assert "Pushed local changes and tags v1." in capsys.readouterr().out


def test_a_tag_refspec_that_names_a_private_commit_sends_nothing(world, capsys):
    repo, origin = world
    _git(repo, "checkout", "-q", "-b", "scratch")
    _write(repo, "templates/private.json", PRIVATE)
    _commit(repo, "private scratch")
    _git(repo, "tag", "keep")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "branch", "-q", "-D", "scratch")
    _main_ahead(repo)
    _git(repo, "config", "--add", "remote.origin.push", "refs/heads/main:refs/heads/main")
    _git(repo, "config", "--add", "remote.origin.push", "refs/tags/*:refs/tags/*")
    before = _refs(origin)

    assert _sync(repo) is True

    assert _refs(origin) == before
    assert not _holds_secret(origin)
    assert "(in refs/tags/keep, which remote.origin.push pushes)" in capsys.readouterr().out


def test_a_configured_deletion_is_refused_and_nothing_changes(world, capsys):
    repo, origin = world
    _git(repo, "push", "-q", "origin", "main:refs/heads/old")
    _main_ahead(repo)
    _git(repo, "config", "--add", "remote.origin.push", "refs/heads/main:refs/heads/main")
    _git(repo, "config", "--add", "remote.origin.push", ":refs/heads/old")
    before = _refs(origin)

    assert _sync(repo) is True

    assert _refs(origin) == before
    assert "would delete refs/heads/old on origin" in capsys.readouterr().out


def test_a_mirror_remote_is_refused(world, capsys):
    repo, origin = world
    _main_ahead(repo)
    _git(repo, "config", "remote.origin.mirror", "true")
    before = _refs(origin)

    assert _sync(repo) is True

    assert _refs(origin) == before
    assert "origin is a mirror (remote.origin.mirror)" in capsys.readouterr().out


@pytest.fixture()
def private_on_origin(world, tmp_path):
    """origin already holds a private version (sent by plain git); mirror never got it."""
    repo, origin = world
    mirror = _bare(tmp_path, "mirror")
    _git(repo, "push", "-q", str(mirror), "main")
    _write(repo, "templates/private.json", PRIVATE)
    _commit(repo, "private version sent by plain git")
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "rm", "-q", "templates/private.json")
    _commit(repo, "remove it")
    _main_ahead(repo)
    return repo, origin, mirror


def test_a_pushurl_elsewhere_is_checked_against_what_that_url_has(private_on_origin, capsys):
    repo, _, mirror = private_on_origin
    _git(repo, "config", "remote.origin.pushurl", str(mirror))
    before = _refs(mirror)

    assert _sync(repo) is True

    assert _refs(mirror) == before
    assert not _holds_secret(mirror)
    out = capsys.readouterr().out
    assert "  templates/private.json\n" in out
    assert f"origin pushes to {mirror}, which lacks those commits" in out
    assert "reset --soft" not in out  # origin/main already holds the private version


def test_two_pushurls_each_get_the_checked_push(private_on_origin, tmp_path, capsys):
    """One URL already has the private version and one does not; neither gets it."""
    repo, origin, mirror = private_on_origin
    _git(repo, "config", "--add", "remote.origin.pushurl", str(origin))
    _git(repo, "config", "--add", "remote.origin.pushurl", str(mirror))
    before = _refs(mirror)

    assert _sync(repo) is True

    assert _refs(mirror) == before and not _holds_secret(mirror)
    assert "Not pushing: unpushed commits include local-only templates:" in capsys.readouterr().out


def test_two_clean_pushurls_both_receive_the_push(world, tmp_path):
    repo, origin = world
    second = _bare(tmp_path, "second")
    _git(repo, "push", "-q", str(second), "main")
    main = _main_ahead(repo)
    _git(repo, "config", "--add", "remote.origin.pushurl", str(origin))
    _git(repo, "config", "--add", "remote.origin.pushurl", str(second))

    assert _sync(repo) is True

    assert _refs(origin)["refs/heads/main"] == _refs(second)["refs/heads/main"] == main


def test_the_pushed_object_is_the_one_checked(world, monkeypatch):
    """A commit made while the check runs is not pushed with the checked one."""
    repo, origin = world
    checked = _main_ahead(repo)
    real = remote_module.outgoing_privacy
    late = []

    def check_then_commit(*args, **kwargs):
        result = real(*args, **kwargs)
        if not late:
            _write(repo, "templates/late.json", PRIVATE)
            late.append(_commit(repo, "made during the check"))
        return result

    monkeypatch.setattr(remote_module, "outgoing_privacy", check_then_commit)

    assert _sync(repo) is True

    assert _refs(origin)["refs/heads/main"] == checked
    assert _git(repo, "rev-parse", "HEAD") == late[0]
    assert not _holds_secret(origin)


def test_git_refusing_the_configured_push_is_reported(world, capsys):
    repo, origin = world
    _git(repo, "checkout", "-q", "-b", "work", "--track", "origin/main")
    _git(repo, "config", "push.default", "simple")
    _main_ahead(repo)
    before = _refs(origin)

    assert _sync(repo) is True

    assert _refs(origin) == before
    out = capsys.readouterr().out
    assert "Not pushing: Git would not push this branch:" in out
    assert "does not match" in out


def test_a_destination_espansr_cannot_read_stops_the_push(world, monkeypatch, capsys):
    repo, origin = world
    _main_ahead(repo)
    url = "https://bob:hunter2@example.invalid/r.git"
    monkeypatch.setattr(remote_module, "push_urls", lambda repo, remote: [url])
    monkeypatch.setattr(remote_module, "destination_commits", lambda *args: None)
    pushes = []
    real_git = cli._git_in

    def no_real_push(repo_dir, *args, **kwargs):
        if args[:1] == ("push",) and "--dry-run" not in args:
            pushes.append(args)
        return real_git(repo_dir, *args, **kwargs)

    monkeypatch.setattr(cli, "_git_in", no_real_push)

    assert _sync(repo) is True

    out = capsys.readouterr().out
    assert "could not read what https://bob:***@example.invalid/r.git already has" in out
    assert "hunter2" not in out
    assert pushes == []


@pytest.fixture()
def store_on_origin(tmp_path):
    """A template store whose origin already holds a private version its mirror lacks."""
    origin, mirror, store = (
        _bare(tmp_path, "s-origin"),
        _bare(tmp_path, "s-mirror"),
        tmp_path / "store",
    )
    store.mkdir()
    _git(store, "init", "-q", "-b", "main")
    _write(store, "greeting.json", {"name": "Greeting", "trigger": ":greet", "content": "hi"})
    config = ConfigManager(config_path=tmp_path / "config.json")
    config.save(Config())
    manager = RemoteManager(templates_dir=store, config_manager=config)
    manager.set_remote(str(origin))
    manager.push()
    _git(store, "push", "-q", str(mirror), "main")
    _write(store, "private.json", PRIVATE)
    _commit(store, "private version sent by plain git")
    _git(store, "push", "-q", "origin", "main")
    _git(store, "rm", "-q", "private.json")
    _commit(store, "remove it")
    _write(store, "greeting.json", {"name": "Greeting", "trigger": ":greet", "content": "hello"})
    _commit(store, "safe change")
    return store, mirror, manager


def test_the_template_push_checks_what_its_pushurl_has(store_on_origin):
    store, mirror, manager = store_on_origin
    _git(store, "config", "remote.origin.pushurl", str(mirror))
    before = _refs(mirror)

    with pytest.raises(
        RemoteError, match=r"contain local-only templates: private\.json"
    ) as refused:
        manager.push()

    assert _refs(mirror) == before and not _holds_secret(mirror)
    assert "take them out of those commits" in str(refused.value)
    assert "reset --soft" not in str(refused.value)


def test_the_template_push_to_its_fetch_url_is_unchanged(store_on_origin):
    """Fetched and pushed alike: the history origin has is not sent again or refused."""
    store, _, manager = store_on_origin
    assert manager.push() is True
    assert _git(store, "rev-parse", "origin/main") == _git(store, "rev-parse", "HEAD")


def _advance_remote(bare: Path, tmp_path: Path, branch: str, name: str) -> None:
    """Another machine pushes one commit to *branch* of *bare*."""
    clone = tmp_path / f"elsewhere-{name}"
    _git(tmp_path, "clone", "-q", "-b", branch, str(bare), str(clone))
    _write(clone, f"{name}.txt", "from elsewhere\n")
    _commit(clone, f"{name} elsewhere")
    _git(clone, "push", "-q", "origin", branch)


def test_a_branch_git_rejects_is_named_and_the_rest_is_pushed(world, tmp_path, capsys):
    repo, origin = world
    _other(repo, private=False)
    _advance_remote(origin, tmp_path, "other", "other")  # local other is now behind and ahead
    main = _main_ahead(repo)
    _git(repo, "config", "push.default", "matching")

    assert _sync(repo) is True

    assert _refs(origin)["refs/heads/main"] == main
    out = capsys.readouterr().out
    assert "Not pushed: Git rejects refs/heads/other (non-fast-forward)." in out
    assert "does not push" not in out


def test_the_branch_git_rejects_is_never_called_unconfigured(world, tmp_path, monkeypatch, capsys):
    """The remote moves between the pull and the push: Git rejects main, as it says."""
    repo, origin = world
    ours = _main_ahead(repo)
    real_plan = cli._plan_push

    def remote_moves_first(repo_dir):
        _advance_remote(origin, tmp_path, "main", "late")
        return real_plan(repo_dir)

    monkeypatch.setattr(cli, "_plan_push", remote_moves_first)

    assert _sync(repo) is True

    assert _refs(origin)["refs/heads/main"] != ours
    assert _git(origin, "log", "-1", "--format=%s", "main") == "late elsewhere"
    out = capsys.readouterr().out
    assert "Not pushed: Git rejects refs/heads/main (fetch first)." in out
    assert "does not push" not in out
