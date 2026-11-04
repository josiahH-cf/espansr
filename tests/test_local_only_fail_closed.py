"""espansr's sharing paths fail closed for local-only prompts, checked with real Git.

A template is shareable only when it reads as valid JSON whose ``local_only``
is absent or exactly false. One that cannot be read, does not parse without
the mark, or sets ``local_only`` to anything else stops every push and sync
before anything is staged, and keeps an exclusion it already had until a
valid change makes it shareable. Every version a push would send is read,
merge commits included, the commit takes only checked index entries, and only
espansr's own block of ``info/exclude`` ever changes.

Each test builds disposable repositories with a bare remote and searches
every object reachable from the remote's refs for the private text.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SECRET = "PRIVATE-TEXT-4F9K"


@pytest.fixture()
def git_identity(monkeypatch):
    for key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(key, "espansr test")
    for key in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(key, "test@example.invalid")


def _git(cwd: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    if check:
        assert result.returncode == 0, result.stderr
    return result.stdout


def _template(path: Path, name: str, content: str = "", **fields) -> Path:
    data = {"name": name, "content": content or f"{name} body", "trigger": f":{name.lower()}"}
    data.update(fields)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _remote_holds_secret(bare: Path) -> bool:
    """True when any object reachable from any ref of *bare* contains SECRET."""
    listing = _git(bare, "rev-list", "--objects", "--all").split()
    objects = [token for token in listing if len(token) == 40]
    if not objects:
        return False
    batch = subprocess.run(
        ["git", "-C", str(bare), "cat-file", "--batch"],
        input="\n".join(objects).encode() + b"\n",
        capture_output=True,
        check=True,
    )
    return SECRET.encode() in batch.stdout


def _local_commits_with_secret(repo: Path) -> str:
    return _git(repo, "log", "--branches", "--format=%s", "-S", SECRET).strip()


@pytest.fixture()
def store(tmp_path, git_identity):
    from espansr.core.config import Config, ConfigManager
    from espansr.core.remote import RemoteManager

    root, bare = tmp_path / "templates", tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    _template(root / "greeting.json", "Greeting")
    config = ConfigManager(config_path=tmp_path / "config.json")
    config.save(Config())
    remote = RemoteManager(templates_dir=root, config_manager=config)
    remote.set_remote(str(bare))
    _git(root, "checkout", "-q", "-B", "main")
    remote.push()
    return root, bare, remote


def _exclude(root: Path) -> Path:
    path = Path(_git(root, "rev-parse", "--git-path", "info/exclude").strip())
    return path if path.is_absolute() else root / path


def _private(root: Path, name: str = "private.json") -> Path:
    return _template(root / name, "Private", f"{SECRET} body", local_only=True)


def _cut_at_mark(path: Path) -> None:
    raw = path.read_bytes()
    path.write_bytes(raw[: raw.index(b'"local_only"')])


def _set_local_only(value):
    def damage(path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["local_only"] = value
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    return damage


def _unreadable(path: Path) -> None:
    if sys.platform == "win32" or os.geteuid() == 0:
        pytest.skip("needs POSIX permissions that apply to this user")
    path.chmod(0)


def _emptied(path: Path) -> None:
    path.write_bytes(b"")


def _not_utf8(path: Path) -> None:
    """The review's shape: no local_only key and one byte that is not UTF-8 (Latin-1 parses)."""
    path.write_bytes(
        b'{"name":"Private","content":"' + SECRET.encode() + b'\xff","trigger":":private"}\n'
    )


DAMAGE = [
    pytest.param(_cut_at_mark, id="cut-before-the-mark"),
    pytest.param(_set_local_only("true"), id="string-true"),
    pytest.param(_set_local_only(1), id="number-1"),
    pytest.param(_set_local_only(None), id="null"),
    pytest.param(_unreadable, id="unreadable"),
    pytest.param(_emptied, id="emptied"),
    pytest.param(_not_utf8, id="not-utf8"),
]


# ── Template store: RemoteManager.push / push_templates ─────────────────────


@pytest.mark.parametrize("damage", DAMAGE)
def test_push_fails_closed_until_a_valid_change_makes_it_shareable(store, damage):
    from espansr.core.remote import RemoteError

    root, bare, remote = store
    path = _private(root)
    remote.push()  # the exclusion is now established
    damage(path)
    with pytest.raises(RemoteError, match="cannot tell whether private.json is local only"):
        remote.push()
    path.chmod(0o644)
    assert not _remote_holds_secret(bare)
    assert "/private.json" in _exclude(root).read_text(encoding="utf-8")
    assert _git(root, "diff", "--cached", "--name-only") == ""

    _template(path, "Private", "now meant to be shared")  # an explicit, valid change
    remote.push()
    assert "/private.json" not in _exclude(root).read_text(encoding="utf-8")
    assert "now meant to be shared" in _git(bare, "show", "main:private.json")


def test_a_cut_file_that_still_spells_the_mark_stays_private(store):
    """The review's exact case: only the closing brace is gone, so the mark remains."""
    root, bare, remote = store
    path = _private(root)
    remote.push()
    path.write_bytes(path.read_bytes().rstrip()[:-1])
    remote.push()
    assert not _remote_holds_secret(bare)


def test_a_file_that_is_not_utf8_but_spells_the_mark_stays_private(store):
    root, bare, remote = store
    path = _private(root)
    remote.push()
    path.write_bytes(path.read_bytes().replace(b" body", b" body\xff"))
    _template(root / "greeting.json", "Greeting", "greeting v2")
    remote.push()
    assert "greeting v2" in _git(bare, "show", "main:greeting.json")
    assert "/private.json" in _exclude(root).read_text(encoding="utf-8")
    assert not _remote_holds_secret(bare)


def test_a_selected_push_also_fails_closed(store):
    from espansr.core.remote import RemoteError

    root, bare, remote = store
    _set_local_only("true")(_private(root))
    _template(root / "greeting.json", "Greeting", "greeting v2")
    with pytest.raises(RemoteError, match="cannot tell whether"):
        remote.push_templates(["greeting.json"])
    assert "greeting v2" not in _git(bare, "show", "main:greeting.json")


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])  # PowerShell 5 writes UTF-16
@pytest.mark.parametrize("selected", [False, True])
def test_push_refuses_an_unmarked_earlier_version_of_a_renamed_local_only_template(
    store, selected, encoding
):
    """Committed before it was marked (say an offline push), then marked and renamed."""
    from espansr.core.remote import RemoteError

    root, bare, remote = store
    _template(root / "draft.json", "Draft", f"{SECRET} body", trigger=":secret")
    _git(root, "add", "draft.json")
    _git(root, "commit", "-q", "-m", "work in progress")
    (root / "draft.json").unlink()
    secret = _template(
        root / "secret.json", "Secret", f"{SECRET} body", trigger=":secret", local_only=True
    )
    secret.write_bytes(secret.read_text(encoding="utf-8").encode(encoding))
    _template(root / "greeting.json", "Greeting", "greeting v2")
    with pytest.raises(RemoteError, match="contain local-only templates: draft.json"):
        remote.push_templates(["greeting.json"]) if selected else remote.push()
    assert not _remote_holds_secret(bare)


def _merge_that_alone_adds(repo: Path, path: str) -> None:
    """A merge commit whose own tree adds a marked file a later commit deletes."""
    folder = Path(path).parent.as_posix()
    prefix = "" if folder == "." else f"{folder}/"
    _git(repo, "checkout", "-q", "-b", "side")
    _template(repo / f"{prefix}side.json", "Side")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "side")
    _git(repo, "checkout", "-q", "main")
    _template(repo / f"{prefix}main_two.json", "MainTwo")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "main")
    _git(repo, "merge", "-q", "--no-ff", "--no-commit", "side")
    _template(repo / path, "Merged", f"{SECRET} body", local_only=True)
    _git(repo, "add", path)
    _git(repo, "commit", "-q", "-m", "merge side")
    _git(repo, "rm", "-q", path)
    _git(repo, "commit", "-q", "-m", "drop it")


def test_push_reads_the_versions_only_a_merge_commit_records(store):
    from espansr.core.remote import RemoteError

    root, bare, remote = store
    _merge_that_alone_adds(root, "merged.json")
    with pytest.raises(RemoteError, match="merged.json"):
        remote.push()
    assert not _remote_holds_secret(bare)


def test_the_history_check_reads_merges_and_reports_unclear_versions(tmp_path, git_identity):
    from espansr.core.remote import local_only_in_history

    repo = tmp_path / "repo"
    _git(tmp_path, "init", "-q", "-b", "main", str(repo))
    _template(repo / "base.json", "Base")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD").strip()
    _merge_that_alone_adds(repo, "merged.json")
    _template(repo / "odd.json", "Odd", f"{SECRET} body", local_only="yes")
    _git(repo, "add", "odd.json")
    _git(repo, "commit", "-q", "-m", "odd")
    _git(repo, "rm", "-q", "odd.json")
    _git(repo, "commit", "-q", "-m", "drop odd")
    assert local_only_in_history(repo, [f"{base}..HEAD"], []) == ["merged.json", "odd.json"]


EXCLUDE = b"# user rules\r\n*.tmp\r\nnotes/\x0cpage\r\nlast-line-without-newline"


def test_push_changes_only_its_own_block_of_the_exclude_file(store):
    root, _, remote = store
    exclude = _exclude(root)
    exclude.write_bytes(EXCLUDE)
    path = _private(root)
    remote.push()
    listed = exclude.read_bytes()
    assert listed.startswith(EXCLUDE) and b"\n/private.json\n" in listed
    assert _git(root, "check-ignore", "private.json").strip() == "private.json"
    path.unlink()
    remote.push()
    assert exclude.read_bytes() == EXCLUDE

    exclude.write_bytes(EXCLUDE + b"\r\n")  # a final newline is kept the same way
    _private(root)
    remote.push()
    (root / "private.json").unlink()
    remote.push()
    assert exclude.read_bytes() == EXCLUDE + b"\r\n"


def test_a_damaged_exclude_block_is_a_controlled_refusal(store):
    from espansr.core.remote import _LOCAL_ONLY_BEGIN, RemoteError

    root, bare, remote = store
    damaged = b"keep-me\n" + _LOCAL_ONLY_BEGIN.encode() + b"\n/private.json\n"
    _exclude(root).write_bytes(damaged)
    _private(root)
    with pytest.raises(RemoteError, match="could not update"):
        remote.push()
    assert _exclude(root).read_bytes() == damaged
    assert _git(root, "diff", "--cached", "--name-only") == ""
    assert not _remote_holds_secret(bare)


def test_push_from_a_linked_worktree_keeps_the_exclusion_in_the_shared_git_dir(store, tmp_path):
    from espansr.core.config import Config, ConfigManager
    from espansr.core.remote import RemoteManager

    root, bare, _ = store
    worktree = tmp_path / "worktree"
    _git(root, "worktree", "add", "-q", "-b", "elsewhere", str(worktree))
    assert (worktree / ".git").is_file()
    config = ConfigManager(config_path=tmp_path / "wt-config.json")
    config.save(Config())
    _private(worktree)
    RemoteManager(templates_dir=worktree, config_manager=config).push()
    assert "/private.json" in _exclude(worktree).read_text(encoding="utf-8")
    assert _exclude(worktree) == _exclude(root)
    assert not _remote_holds_secret(bare)


def test_pull_keeps_a_template_whose_privacy_is_unknown_like_a_private_one(store, tmp_path):
    from espansr.core.remote import RemoteConflictError

    root, bare, remote = store
    path = _private(root)
    remote.push()
    _cut_at_mark(path)
    kept = path.read_bytes()
    other = tmp_path / "other"
    _git(tmp_path, "clone", "-q", str(bare), str(other))
    _template(other / "private.json", "Theirs", "the other machine's file")
    _git(other, "add", "-A")
    _git(other, "commit", "-q", "-m", "theirs")
    _git(other, "push", "-q")
    with pytest.raises(RemoteConflictError):
        remote.pull()
    assert path.read_bytes() == kept


# ── Install checkout: espansr sync's _sync_repository ───────────────────────


@pytest.fixture()
def checkout(tmp_path, git_identity, monkeypatch):
    upstream, repo = tmp_path / "upstream.git", tmp_path / "checkout"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(upstream))
    _git(tmp_path, "clone", "-q", str(upstream), str(repo))
    _git(repo, "checkout", "-q", "-B", "main")
    _template(repo / "templates" / "shared.json", "Shared")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    _git(repo, "push", "-q", "-u", "origin", "main")
    return repo, upstream


def _sync(repo: Path) -> bool:
    import espansr.__main__ as cli

    return cli._sync_repository(repo, no_push=False)


@pytest.mark.parametrize(
    "damage",
    [
        pytest.param(_cut_at_mark, id="cut-before-the-mark"),
        pytest.param(_set_local_only("true"), id="string-true"),
        pytest.param(_not_utf8, id="not-utf8"),
    ],
)
def test_sync_neither_commits_nor_pushes_while_privacy_is_unknown(checkout, capsys, damage):
    repo, upstream = checkout
    damage(_template(repo / "templates" / "mine.json", "Mine", f"{SECRET} body", local_only=True))
    _template(repo / "templates" / "shared.json", "Shared", "shared v2")
    assert _sync(repo) is True  # the reinstall still runs
    assert "cannot tell whether these are local only" in capsys.readouterr().out
    assert _local_commits_with_secret(repo) == ""
    assert not _remote_holds_secret(upstream)


def test_sync_never_pushes_a_matching_branch_that_holds_a_private_version(checkout, capsys):
    """With push.default=matching, the push also sends feature, so it is checked and refused."""
    repo, upstream = checkout
    _git(repo, "checkout", "-q", "-b", "feature")
    _template(repo / "templates" / "feature.json", "Feature")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "feature")
    _git(repo, "push", "-q", "-u", "origin", "feature")
    _template(repo / "templates" / "mine.json", "Mine", f"{SECRET} body", local_only=True)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "private work on feature")
    _git(repo, "checkout", "-q", "main")
    _git(repo, "config", "push.default", "matching")
    _template(repo / "templates" / "shared.json", "Shared", "shared v2")
    before = _git(upstream, "rev-parse", "main", "feature")
    assert _sync(repo) is True
    assert _git(upstream, "rev-parse", "main", "feature") == before  # nothing pushed
    assert not _remote_holds_secret(upstream)
    out = capsys.readouterr().out
    assert "templates/mine.json (in refs/heads/feature, which push.default=matching pushes)" in out


@pytest.mark.parametrize(
    ("settings", "branch", "expected"),
    [
        ({}, "main", ("origin", [("refs/heads/main", "refs/heads/main")])),
        ({"push.default": "simple"}, "work", None),  # Git refuses a differently named upstream
        (
            {"push.default": "upstream"},
            "work",
            ("origin", [("refs/heads/work", "refs/heads/main")]),
        ),
        ({"push.default": "current"}, "work", ("origin", [("refs/heads/work", "refs/heads/work")])),
        (
            {"push.default": "matching"},
            "main",
            ("origin", [("refs/heads/main", "refs/heads/main")]),
        ),
        ({"push.default": "nothing"}, "main", None),
        (
            {"remote.pushDefault": "fork"},
            "main",
            ("fork", [("refs/heads/main", "refs/heads/main")]),
        ),
        (
            {"remote.origin.push": "refs/heads/main:refs/heads/elsewhere"},
            "main",
            ("origin", [("refs/heads/main", "refs/heads/elsewhere")]),
        ),
        (
            {"remote.origin.push": "HEAD"},
            "main",
            ("origin", [("refs/heads/main", "refs/heads/main")]),
        ),
    ],
)
def test_sync_plans_the_push_git_itself_would_make(checkout, settings, branch, expected):
    import espansr.__main__ as cli

    repo, upstream = checkout
    _git(repo, "remote", "add", "fork", str(upstream))
    if branch != "main":
        _git(repo, "checkout", "-q", "-b", branch, "--track", "origin/main")
    for key, value in settings.items():
        _git(repo, "config", key, value)
    _git(repo, "commit", "-q", "--allow-empty", "-m", "ahead")
    plan = cli._plan_push(repo)
    if expected is None:
        assert isinstance(plan, cli._NoPush)
        return
    assert (plan.remote, [(u.source, u.target) for u in plan.updates]) == expected
    assert [u.oid for u in plan.updates] == [_git(repo, "rev-parse", "HEAD").strip()]


def _stage_private_version_git_will_not_refresh(repo: Path) -> None:
    shared = repo / "templates" / "shared.json"
    public = shared.read_bytes()
    _template(shared, "Shared", f"{SECRET} body", local_only=True)
    _git(repo, "add", "templates/shared.json")
    _git(repo, "update-index", "--assume-unchanged", "templates/shared.json")
    shared.write_bytes(public)  # the file looks shared again; git add -A will not look


def test_sync_never_commits_a_staged_private_version_git_did_not_refresh(checkout, capsys):
    repo, upstream = checkout
    _stage_private_version_git_will_not_refresh(repo)
    gitdir = Path(_git(repo, "rev-parse", "--absolute-git-dir").strip())
    (gitdir / "refs" / "stash.lock").write_text("")  # another git process holds refs/stash
    _template(repo / "templates" / "other.json", "Other")
    assert _sync(repo) is True
    assert "Not committed: the staged templates/shared.json" in capsys.readouterr().out
    assert _local_commits_with_secret(repo) == ""
    assert "templates/other.json" in _git(upstream, "ls-tree", "-r", "--name-only", "main")
    assert not _remote_holds_secret(upstream)


def test_sync_stops_when_git_stash_saves_changes_but_cannot_finish(checkout, capsys):
    repo, upstream = checkout
    _stage_private_version_git_will_not_refresh(repo)
    assert _sync(repo) is False
    out = capsys.readouterr().out
    assert "git stash saved your local changes but could not finish" in out
    assert "espansr-sync" in _git(repo, "stash", "list")
    assert _local_commits_with_secret(repo) == ""
    assert not _remote_holds_secret(upstream)


# ── Delivery, catalog, starters ─────────────────────────────────────────────


def _deliver_module():
    import importlib.util

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("deliver_r4", root / "scripts" / "deliver.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_delivery_reads_merge_commits_and_unclear_versions(checkout, monkeypatch):
    deliver = _deliver_module()
    repo, _ = checkout
    _merge_that_alone_adds(repo, "templates/merged.json")
    _template(repo / "templates" / "odd.json", "Odd", f"{SECRET} body", local_only="yes")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "odd")
    _git(repo, "rm", "-q", "templates/odd.json")
    _git(repo, "commit", "-q", "-m", "drop odd")
    monkeypatch.setattr(deliver, "ROOT", repo)

    def in_repo(argv, cwd=None, **kwargs):  # real git, run in the disposable checkout
        return deliver.run(argv, cwd=repo, **kwargs)

    delivery = deliver.Delivery(
        branch="agent/feat-x", message="feat: x\n", body=None, paths=[], runner=in_repo
    )
    assert delivery._local_only_history() == ["templates/merged.json", "templates/odd.json"]


def test_delivery_refuses_a_listed_template_whose_privacy_is_unknown(tmp_path, monkeypatch):
    deliver = _deliver_module()
    checkout = tmp_path / "checkout"
    path = _template(checkout / "templates" / "odd.json", "Odd", local_only="true")
    monkeypatch.setattr(deliver, "ROOT", checkout)
    calls = []

    def runner(argv, cwd=None, **kwargs):
        calls.append(" ".join(argv))
        out = {"git rev-parse --abbrev-ref HEAD": "main\n"}.get(" ".join(argv), "")
        if argv[:3] == ["git", "status", "--porcelain"]:
            out = f"?? {path.relative_to(checkout).as_posix()}\n"
        return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")

    delivery = deliver.Delivery(
        branch="agent/feat-odd",
        message="feat: odd\n",
        body=None,
        paths=["templates/odd.json"],
        runner=runner,
        python="py",
        sleep=lambda _: None,
    )
    assert delivery.deliver() == deliver.EXIT_PREFLIGHT
    assert not [c for c in calls if c.startswith(("git add", "git commit", "git push", "gh "))]


def test_delivery_counts_an_unpushed_version_that_is_not_utf8_as_unclear(checkout, monkeypatch):
    deliver = _deliver_module()
    repo, _ = checkout
    _not_utf8(repo / "templates" / "odd.json")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "odd bytes")
    _git(repo, "rm", "-q", "templates/odd.json")
    _git(repo, "commit", "-q", "-m", "drop odd")
    monkeypatch.setattr(deliver, "ROOT", repo)

    def in_repo(argv, cwd=None, **kwargs):
        return deliver.run(argv, cwd=repo, **kwargs)

    delivery = deliver.Delivery(
        branch="agent/feat-x", message="feat: x\n", body=None, paths=[], runner=in_repo
    )
    assert delivery._local_only_history() == ["templates/odd.json"]


@pytest.fixture()
def renamed_draft(tmp_path, git_identity):
    """The review's delivery case: an unmarked draft committed, then removed, on the branch."""
    bare, repo = tmp_path / "origin.git", tmp_path / "repo"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    _git(tmp_path, "init", "-q", "-b", "main", str(repo))
    _template(repo / "templates" / "shared.json", "Shared")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base public")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-q", "-u", "origin", "main")
    _git(repo, "checkout", "-q", "-b", "agent/feat-review")
    _template(repo / "templates" / "draft.json", "Secret", SECRET)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "offline unmarked draft")
    _git(repo, "rm", "-q", "templates/draft.json")
    _git(repo, "commit", "-q", "-m", "remove old draft name")
    _template(repo / "templates" / "shared.json", "Shared", "safe delivery change")
    return repo, bare


def _public_delivery(deliver, repo: Path):
    def in_repo(argv, cwd=None, **kwargs):  # real git, run in the disposable checkout
        return deliver.run(argv, cwd=repo, **kwargs)

    return deliver.Delivery(
        branch="agent/feat-review",
        message="feat: public change\n",
        body=None,
        paths=["templates/shared.json"],
        runner=in_repo,
    )


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_delivery_refuses_an_earlier_version_of_a_private_template_under_another_name(
    renamed_draft, monkeypatch, encoding
):
    """The private copy is untracked and not listed; its identity still finds the old draft."""
    deliver = _deliver_module()
    repo, bare = renamed_draft
    private = _template(repo / "templates" / "private.json", "Secret", SECRET, local_only=True)
    private.write_bytes(private.read_text(encoding="utf-8").encode(encoding))
    monkeypatch.setattr(deliver, "ROOT", repo)
    delivery = _public_delivery(deliver, repo)
    head = _git(repo, "rev-parse", "HEAD")

    with pytest.raises(deliver.DeliveryError, match=r"never delivered: \['templates/draft.json'\]"):
        delivery.preflight()
    assert _git(repo, "rev-parse", "HEAD") == head  # nothing was committed
    with pytest.raises(deliver.DeliveryError) as recheck:
        delivery.publish()  # the recheck right before the push refuses on its own
    assert recheck.value.code == deliver.EXIT_PUBLISH
    assert not [c for c in delivery.commands if c.startswith(("git push", "gh "))]
    assert not _remote_holds_secret(bare)


def test_delivery_still_commits_a_public_change_no_private_template_claims(
    renamed_draft, monkeypatch
):
    """A private copy of the public change's text does not make the public template private."""
    deliver = _deliver_module()
    repo, _ = renamed_draft
    _template(repo / "templates" / "mine.json", "Mine", "safe delivery change", local_only=True)
    monkeypatch.setattr(deliver, "ROOT", repo)
    delivery = _public_delivery(deliver, repo)

    delivery.preflight()

    assert _git(repo, "log", "-1", "--format=%s").strip() == "feat: public change"
    assert _git(repo, "show", "--name-only", "--format=", "HEAD").split() == [
        "templates/shared.json"
    ]
    assert delivery._local_only_history() == []
    assert "?? templates/mine.json" in _git(repo, "status", "--porcelain")


def test_catalog_never_describes_a_template_whose_privacy_is_unclear(tmp_path):
    from espansr.core.capability_catalog import build_catalog

    source = tmp_path / "source"
    _template(source / "open.json", "Open")
    _template(source / "odd.json", "Odd", f"{SECRET} body", local_only="true")
    catalog = json.dumps(build_catalog(source, None))
    assert "template:open" in catalog
    assert "template:odd" not in catalog and SECRET not in catalog


def test_starter_updates_never_replace_a_copy_with_a_set_local_only(tmp_path):
    from espansr.core.templates import sync_bundled_templates_to_live

    bundled, live = tmp_path / "bundled", tmp_path / "live"
    _template(bundled / "starter.json", "Starter", "bundled v2")
    mine = _template(live / "starter.json", "Starter", f"{SECRET} edits", local_only="true")
    before = mine.read_bytes()
    sync_bundled_templates_to_live(templates_dir=live, bundled_dir=bundled)
    assert mine.read_bytes() == before
