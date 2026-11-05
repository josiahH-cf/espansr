"""espansr never shares a local-only prompt; it still expands on this machine.

``local_only: true`` keeps a template out of every surface that shares it:
the template Git remote, the install checkout's ``espansr sync`` commit and
push, ``scripts/deliver.py``, and the capability catalog that connected tools
read as context. Import preserves the flag, bundled reconciliation never
overwrites or retires a local-only copy, and the editor and ``:coms`` show it.
Git checks run against real repositories and bare remotes.
"""

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from espansr.core.capability_catalog import build_catalog
from espansr.core.command_catalog import LOCAL_ONLY_TEXT, CommandCatalogEntry
from espansr.core.templates import (
    Template,
    TemplateManager,
    import_template,
    is_local_only_file,
    local_only_template_paths,
    sync_bundled_templates_to_live,
)

ROOT = Path(__file__).resolve().parents[1]
SECRETS = ("Secret Plan", ":secret-plan", "my private description", "PRIVATE-CONTENT-123")


def _write(path: Path, name: str, *, trigger=None, local_only=False, **extra) -> Path:
    data = {"name": name, "content": f"{name} body", "trigger": trigger or f":{name.lower()}"}
    data.update(extra)
    if local_only:
        data["local_only"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _secret(path: Path) -> Path:
    return _write(
        path,
        "Secret Plan",
        trigger=":secret-plan",
        local_only=True,
        description="my private description",
        content="PRIVATE-CONTENT-123",
        publish_definition=True,
    )


@pytest.fixture()
def git_identity(monkeypatch):
    for key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(key, "espansr test")
    for key in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(key, "test@example.invalid")


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    ).stdout


def _remote_files(bare: Path, branch: str = "main") -> list[str]:
    out = subprocess.run(
        ["git", "--git-dir", str(bare), "ls-tree", "-r", "--name-only", branch],
        capture_output=True,
        text=True,
    )
    return out.stdout.split() if out.returncode == 0 else []


def _history(bare: Path) -> str:
    """Every version a remote has ever received."""
    return _git(bare, "log", "--all", "-p")


def _other_machine(bare: Path, path: Path, name: str, content: str) -> None:
    """Another machine commits ``name`` and pushes it."""
    subprocess.run(["git", "clone", "-q", str(bare), str(path)], check=True, capture_output=True)
    _write(path / name, Path(name).stem.title(), content=content)
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", f"{name} from another machine")
    _git(path, "push", "-q")


# ── Model, import, discovery of local-only files ────────────────────────────


def test_flag_round_trips_and_is_omitted_when_false():
    assert Template(name="A", content="x", local_only=True).to_dict()["local_only"] is True
    assert "local_only" not in Template(name="A", content="x").to_dict()
    assert Template.from_dict({"name": "A", "content": "x", "local_only": True}).local_only
    assert not Template.from_dict({"name": "A", "content": "x", "local_only": False}).local_only
    # Anything but an explicit false stays private (sharing refuses it until it is fixed).
    for unclear in ("yes", "false", 0, 1, None):
        assert Template.from_dict({"name": "A", "content": "x", "local_only": unclear}).local_only


def test_import_keeps_privacy_but_never_imports_a_publication_opt_in(tmp_path):
    source = _secret(tmp_path / "incoming" / "secret.json")
    result = import_template(source, TemplateManager(templates_dir=tmp_path / "live"))
    saved = json.loads(result.template._path.read_text(encoding="utf-8"))
    assert saved["local_only"] is True
    assert "publish_definition" not in saved


@pytest.mark.parametrize("now_local_only", [True, False])
def test_restoring_a_version_keeps_the_current_local_only_setting(tmp_path, now_local_only):
    manager = TemplateManager(templates_dir=tmp_path)
    template = Template(name="Diary", content="v1", trigger=":diary", local_only=not now_local_only)
    manager.save(template)
    manager.create_version(template, note="first")
    template.content, template.local_only = "v2", now_local_only
    manager.save(template)
    restored = manager.restore_version(template, 1)
    assert restored.content == "v1"
    assert restored.local_only is now_local_only
    assert is_local_only_file(restored._path) is now_local_only


def test_moving_or_renaming_a_template_keeps_it_local_only(tmp_path):
    manager = TemplateManager(templates_dir=tmp_path)
    template = Template(name="Diary", content="x", trigger=":diary", local_only=True)
    assert manager.save(template)
    assert manager.save_to_folder(template, "private")
    template.name = "Journal"
    assert manager.save(template)
    assert template._path.parent.name == "private"
    assert local_only_template_paths(tmp_path) == [template._path]


def test_local_only_paths_walk_folders_like_the_store(tmp_path):
    _write(tmp_path / "shared.json", "Shared")
    mine = _write(tmp_path / "work" / "mine.json", "Mine", local_only=True)
    _write(tmp_path / "_versions" / "old.json", "Old", local_only=True)
    _write(tmp_path / "_meta" / "x.json", "Meta", local_only=True)
    (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
    assert local_only_template_paths(tmp_path) == [mine]


def test_a_marked_template_that_does_not_parse_still_counts_as_local_only(tmp_path):
    body = {"name": "Diary", "content": "PRIVATE", "local_only": True}
    bom = tmp_path / "bom.json"  # Notepad and PowerShell 5 write a byte-order mark
    bom.write_bytes(b"\xef\xbb\xbf" + json.dumps(body).encode("utf-8"))
    typo = tmp_path / "typo.json"
    typo.write_text('{"name": "Plans", "local_only": true,}', encoding="utf-8")
    shared = tmp_path / "shared_bom.json"
    shared.write_bytes(b"\xef\xbb\xbf" + json.dumps({**body, "local_only": False}).encode())
    utf16 = tmp_path / "utf16.json"  # PowerShell 5's Out-File default
    utf16.write_bytes(json.dumps(body).encode("utf-16"))
    mentioned = _write(tmp_path / "mentions.json", "Doc", content='Set "local_only": true to hide')
    assert is_local_only_file(bom) and is_local_only_file(typo) and is_local_only_file(utf16)
    assert not is_local_only_file(shared) and not is_local_only_file(mentioned)


# ── Capability catalog (connected tools' shared context) ────────────────────


def test_catalog_never_describes_a_local_only_definition(tmp_path):
    source, installed = tmp_path / "source", tmp_path / "installed"
    for root in (source, installed):
        _write(root / "shared.json", "Shared")
        _secret(root / "secret_plan.json")
    catalog = build_catalog(source, installed)
    serialized = json.dumps(catalog)
    assert catalog["validation"] == "passed"
    assert catalog["publication"] == "qualified"
    assert [e["template_id"] for e in catalog["entries"]] == ["shared"]
    assert not [s for s in (*SECRETS, "secret_plan") if s in serialized]
    assert "definition_bytes" not in serialized
    assert catalog["coverage"]["unmanaged_installed_templates"] == 1


def test_marking_an_installed_starter_local_only_withdraws_it_without_drift(tmp_path):
    source, installed = tmp_path / "source", tmp_path / "installed"
    for root in (source, installed):
        _write(root / "other.json", "Other")
    _write(source / "starter.json", "Starter", trigger=":starter")
    _write(installed / "starter.json", "Starter", trigger=":starter", local_only=True)
    catalog = build_catalog(source, installed)
    assert catalog["publication"] == "qualified"
    assert [e["template_id"] for e in catalog["entries"]] == ["other"]
    assert ":starter" not in json.dumps(catalog)
    assert catalog["coverage"]["unmanaged_installed_templates"] == 1


def _published_pair(tmp_path):
    from espansr.core.capability_catalog import PUBLICATION_PATH, publish_catalog

    source, installed = tmp_path / "source", tmp_path / "installed"
    for root in (source, installed):
        _write(root / "other.json", "Other")
        _write(root / "starter.json", "Starter", trigger=":starter", description="once shared")
    publish_catalog(source, installed)
    published = installed / PUBLICATION_PATH
    assert ":starter" in published.read_text(encoding="utf-8")
    _write(installed / "other.json", "Other", content="edited here")  # unrelated drift
    return source, installed, published


def test_a_retained_publication_that_describes_a_now_private_template_is_withdrawn(tmp_path):
    from espansr.core.capability_catalog import PublicationWithdrawn, publish_catalog

    source, installed, published = _published_pair(tmp_path)
    _write(installed / "starter.json", "Starter", trigger=":starter", local_only=True)
    with pytest.raises(PublicationWithdrawn):
        publish_catalog(source, installed)  # unqualified, so nothing replaces it
    assert not published.exists()


def test_an_unqualified_build_keeps_a_publication_that_describes_nothing_private(tmp_path):
    from espansr.core.capability_catalog import PublicationWithdrawn, publish_catalog

    source, installed, published = _published_pair(tmp_path)
    before = published.read_bytes()
    with pytest.raises(ValueError) as raised:
        publish_catalog(source, installed)
    assert not isinstance(raised.value, PublicationWithdrawn)
    assert published.read_bytes() == before


def _workflow(root: Path, capabilities: list[str]) -> None:
    manifest = {
        "workflow_schema": 1,
        "id": "flow",
        "name": "Flow",
        "description": "Two steps.",
        "entry_points": [capabilities[0]],
        "nodes": [
            {"capability": cap, "role": f"Step {cap}.", "x": 100 * i, "y": 0}
            for i, cap in enumerate(capabilities)
        ],
        "edges": [],
    }
    path = root / "_meta" / "workflows" / "flow.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_a_workflow_built_on_a_local_only_capability_is_omitted_not_failed(tmp_path):
    _write(tmp_path / "alpha.json", "Alpha", capability_id="alpha")
    _write(tmp_path / "beta.json", "Beta", capability_id="beta", local_only=True)
    _workflow(tmp_path, ["alpha", "beta"])
    catalog = build_catalog(tmp_path)
    assert catalog["validation"] == "passed"
    assert [e["id"] for e in catalog["entries"]] == ["template:alpha"]


def test_a_workflow_with_a_genuinely_missing_capability_still_fails(tmp_path):
    _write(tmp_path / "alpha.json", "Alpha", capability_id="alpha")
    _workflow(tmp_path, ["alpha", "missing"])
    assert build_catalog(tmp_path)["validation"] == "failed"


# ── Bundled starter reconciliation ───────────────────────────────────────────


def test_bundled_sync_never_overwrites_a_local_only_starter_copy(tmp_path):
    bundled, live = tmp_path / "bundled", tmp_path / "live"
    _write(bundled / "starter.json", "Starter", trigger=":starter")
    mine = _write(
        live / "starter.json", "Starter", trigger=":starter", local_only=True, note="mine"
    )
    before = mine.read_bytes()
    report, result = sync_bundled_templates_to_live(templates_dir=live, bundled_dir=bundled)
    assert mine.read_bytes() == before
    assert result.updated == 0
    assert mine in report.unbundled


def test_bundled_sync_never_retires_a_local_only_copy(tmp_path):
    bundled, live = tmp_path / "bundled", tmp_path / "live"
    _write(bundled / "other.json", "Other")
    kept = _write(live / "feat.json", "Feat", trigger=":feat", local_only=True)
    _, result = sync_bundled_templates_to_live(templates_dir=live, bundled_dir=bundled)
    assert kept.exists()
    assert result.retired == 0


def test_bundled_sync_does_not_shadow_a_trigger_a_local_only_copy_owns(tmp_path):
    bundled, live = tmp_path / "bundled", tmp_path / "live"
    _write(bundled / "starter.json", "Starter", trigger=":starter")
    _write(live / "my_starter.json", "My starter", trigger=":starter", local_only=True)
    _, result = sync_bundled_templates_to_live(templates_dir=live, bundled_dir=bundled)
    assert not (live / "starter.json").exists()
    assert result.copied == 0


# ── Template Git remote (espansr push) ───────────────────────────────────────


@pytest.fixture()
def remote_store(tmp_path, git_identity):
    from espansr.core.config import Config, ConfigManager
    from espansr.core.remote import RemoteManager

    store, bare = tmp_path / "templates", tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True
    )
    _write(store / "greeting.json", "Greeting")
    manager = ConfigManager(config_path=tmp_path / "config.json")
    manager.save(Config())
    remote = RemoteManager(templates_dir=store, config_manager=manager)
    remote.set_remote(str(bare))
    _git(store, "checkout", "-q", "-B", "main")
    return store, bare, remote


def test_push_never_commits_a_local_only_template(remote_store):
    store, bare, remote = remote_store
    _secret(store / "secret_plan.json")
    _write(store / "work" / "mine.json", "Mine", local_only=True)
    remote.push()
    files = _remote_files(bare)
    assert "greeting.json" in files
    assert not [f for f in files if f in ("secret_plan.json", "work/mine.json")]
    assert _git(store, "status", "--porcelain") == ""  # excluded locally, not left dirty
    exclude = (store / ".git" / "info" / "exclude").read_text(encoding="utf-8")
    assert "/secret_plan.json" in exclude and "/work/mine.json" in exclude
    assert ".git/info/exclude" not in files and ".gitignore" in files


def test_a_template_shared_before_it_was_marked_local_only_leaves_the_remote(remote_store):
    store, bare, remote = remote_store
    later = _write(store / "later.json", "Later")
    remote.push()
    assert "later.json" in _remote_files(bare)
    _write(later, "Later", local_only=True)
    remote.push()
    assert "later.json" not in _remote_files(bare)
    assert json.loads(later.read_text(encoding="utf-8"))["local_only"] is True


def test_targeted_push_skips_a_local_only_template(remote_store):
    store, bare, remote = remote_store
    _secret(store / "secret_plan.json")
    remote.push_templates(["secret_plan.json", "greeting.json"])
    assert _remote_files(bare) == [".gitignore", "greeting.json"]
    assert "secret_plan" not in _history(bare)  # not even its name in a commit message


def test_push_command_counts_only_the_templates_it_sent(remote_store, capsys, monkeypatch):
    import espansr.__main__ as cli
    import espansr.core.remote as remote_module

    store, bare, remote = remote_store
    _secret(store / "secret_plan.json")
    monkeypatch.setattr(remote_module, "RemoteManager", lambda: remote)
    args = argparse.Namespace(message=None, template=["secret_plan.json", "greeting.json"])
    assert cli.cmd_push(args) == 0
    out = capsys.readouterr().out
    assert "Not pushed: secret_plan.json is local only." in out
    assert "Pushed 1 template(s) to remote." in out


def test_push_unstages_a_new_local_only_template_staged_by_hand(remote_store):
    store, bare, remote = remote_store
    _secret(store / "secret_plan.json")
    _git(store, "add", "-f", "secret_plan.json")
    remote.push()
    assert _remote_files(bare) == [".gitignore", "greeting.json"]
    assert "PRIVATE-CONTENT-123" not in _history(bare)
    assert _git(store, "status", "--porcelain") == ""


def test_push_refuses_a_force_staged_local_only_template(remote_store):
    from espansr.core.remote import RemoteError

    store, bare, remote = remote_store
    _secret(store / "secret_plan.json")
    _git(store, "add", "-f", "secret_plan.json")
    with pytest.raises(RemoteError, match="local-only"):
        remote.push_templates(["greeting.json"])
    assert _remote_files(bare) == []
    assert "secret_plan.json" not in _git(store, "diff", "--cached", "--name-only")


def test_history_check_reads_every_version_the_commits_would_send(tmp_path, git_identity):
    from espansr.core.remote import local_only_in_history

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _write(repo / "shared.json", "Shared")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    base = _git(repo, "rev-parse", "HEAD").strip()
    _secret(repo / "café plan.json")  # marked when committed, removed later
    _write(repo / "later.json", "Later", content="committed before it was marked")
    _write(repo / "_versions" / "v1.json", "Old", local_only=True)  # history store, not a prompt
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "work")
    _git(repo, "rm", "-q", "café plan.json")
    _git(repo, "commit", "-q", "-m", "drop it")
    unpushed = [f"{base}..HEAD"]
    assert local_only_in_history(repo, unpushed, ["later.json"]) == ["café plan.json", "later.json"]
    assert local_only_in_history(repo, unpushed, []) == ["café plan.json"]
    assert local_only_in_history(repo, ["HEAD..HEAD"], ["later.json"]) == []
    assert local_only_in_history(repo, ["no-such-ref..HEAD"], []) is None  # never a silent pass


def test_push_works_in_a_store_whose_git_folder_is_a_file(tmp_path, git_identity):
    from espansr.core.config import Config, ConfigManager
    from espansr.core.remote import RemoteManager

    main, store, bare = tmp_path / "main", tmp_path / "store", tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True
    )
    main.mkdir()
    _git(main, "init", "-q", "-b", "main")
    _write(main / "greeting.json", "Greeting")
    _git(main, "add", "-A")
    _git(main, "commit", "-q", "-m", "init")
    _git(main, "worktree", "add", "-q", "-b", "store", str(store))
    assert (store / ".git").is_file()  # a worktree, as a submodule would be
    _secret(store / "secret_plan.json")
    manager = ConfigManager(config_path=tmp_path / "config.json")
    manager.save(Config())
    remote = RemoteManager(templates_dir=store, config_manager=manager)
    remote.set_remote(str(bare))
    remote.push()
    assert "greeting.json" in _remote_files(bare, "store")
    assert "PRIVATE-CONTENT-123" not in _history(bare)


def test_push_untracks_a_version_staged_before_the_template_was_marked(remote_store):
    store, bare, remote = remote_store
    notes = _write(store / "notes.json", "Notes", content="shared v1")
    remote.push()
    _write(notes, "Notes", content="staged v2")
    _git(store, "add", "notes.json")
    _secret(notes)
    remote.push()
    assert "notes.json" not in _remote_files(bare)
    assert "staged v2" not in _history(bare) and "PRIVATE-CONTENT-123" not in _history(bare)


def test_pull_refuses_to_put_the_remotes_file_over_a_local_only_one(remote_store, tmp_path):
    from espansr.core.remote import RemoteConflictError

    store, bare, remote = remote_store
    remote.push()
    mine = _secret(store / "notes.json")
    remote.push()
    before = mine.read_bytes()
    _other_machine(bare, tmp_path / "other", "notes.json", "shared from another machine")
    with pytest.raises(RemoteConflictError, match="local only on this machine"):
        remote.pull()
    assert mine.read_bytes() == before


def test_pull_after_a_rejected_push_gives_a_newly_local_only_template_back(remote_store, tmp_path):
    from espansr.core.remote import RemoteError

    store, bare, remote = remote_store
    notes = _write(store / "notes.json", "Notes", content="shared v1")
    remote.push()
    _other_machine(bare, tmp_path / "other", "other.json", "unrelated")
    _secret(notes)
    before = notes.read_bytes()
    with pytest.raises(RemoteError, match="rejected"):
        remote.push()
    remote.pull()  # the rebase replays the commit that stops sharing notes.json
    assert notes.read_bytes() == before
    assert not (store / ".git" / "espansr-local-only").exists()
    remote.push()
    assert _remote_files(bare) == [".gitignore", "greeting.json", "other.json"]
    assert "PRIVATE-CONTENT-123" not in _history(bare)


def test_a_concurrent_edit_never_costs_a_newly_local_only_template(remote_store, tmp_path):
    from espansr.core.remote import RemoteConflictError, RemoteError

    store, bare, remote = remote_store
    notes = _write(store / "notes.json", "Notes", content="shared v1")
    remote.push()
    _other_machine(bare, tmp_path / "other", "notes.json", "v2 from another machine")
    _secret(notes)
    before = notes.read_bytes()
    with pytest.raises(RemoteError, match="rejected"):
        remote.push()
    with pytest.raises(RemoteConflictError):
        remote.pull()
    assert notes.read_bytes() == before
    assert "PRIVATE-CONTENT-123" not in _history(bare)


def test_pulling_named_templates_never_replaces_a_local_only_one(remote_store):
    store, bare, remote = remote_store
    notes = _write(store / "notes.json", "Notes", content="shared v1")
    remote.push()
    _secret(notes)
    before = notes.read_bytes()
    remote.pull_templates(["notes.json"])
    assert notes.read_bytes() == before


def test_push_refuses_unpushed_commits_that_carry_a_now_local_only_version(remote_store, tmp_path):
    from espansr.core.remote import RemoteError

    store, bare, remote = remote_store
    remote.push()
    diary = _write(store / "diary.json", "Diary", content="PRIVATE-DIARY")
    _git(store, "remote", "set-url", "origin", str(tmp_path / "offline.git"))
    with pytest.raises(RemoteError):
        remote.push()  # committed here, never sent
    _git(store, "remote", "set-url", "origin", str(bare))
    _write(diary, "Diary", content="PRIVATE-DIARY", local_only=True)
    with pytest.raises(RemoteError, match=r"contain local-only templates: diary\.json") as refused:
        remote.push()
    assert "reset --soft origin/main" in str(refused.value)
    assert "PRIVATE-DIARY" not in _history(bare)
    _git(store, "reset", "-q", "--soft", "origin/main")  # the fix the message names
    remote.push()
    assert "PRIVATE-DIARY" not in _history(bare)
    assert json.loads(diary.read_text(encoding="utf-8"))["content"] == "PRIVATE-DIARY"


def test_push_keeps_a_local_only_template_private_even_when_it_does_not_parse(remote_store):
    store, bare, remote = remote_store
    body = json.dumps({"name": "Diary", "content": "PRIVATE-BOM", "local_only": True})
    (store / "diary.json").write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
    (store / "plans.json").write_text(
        '{"name": "Plans", "content": "PRIVATE-TYPO", "local_only": true,}', encoding="utf-8"
    )
    remote.push()
    assert _remote_files(bare) == [".gitignore", "greeting.json"]
    assert "PRIVATE" not in _history(bare)


# ── Install checkout (espansr sync / :sync) ──────────────────────────────────


@pytest.fixture()
def checkout(tmp_path, git_identity):
    upstream, repo = tmp_path / "upstream.git", tmp_path / "checkout"
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(upstream)], check=True, capture_output=True
    )
    subprocess.run(
        ["git", "clone", "-q", str(upstream), str(repo)], check=True, capture_output=True
    )
    _git(repo, "checkout", "-q", "-B", "main")
    _write(repo / "templates" / "shared.json", "Shared")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    _git(repo, "push", "-q", "-u", "origin", "main")
    return repo, upstream


def _sync(repo: Path) -> bool:
    import espansr.__main__ as cli

    return cli._sync_repository(repo, no_push=False)


def test_sync_commits_and_pushes_everything_except_local_only_templates(checkout, capsys):
    repo, upstream = checkout
    _write(repo / "templates" / "shared.json", "Shared", note="edited")
    _secret(repo / "templates" / "secret_plan.json")
    assert _sync(repo) is True
    assert _remote_files(upstream) == ["templates/shared.json"]
    shared = subprocess.run(
        ["git", "--git-dir", str(upstream), "show", "main:templates/shared.json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "edited" in shared
    assert "?? templates/secret_plan.json" in _git(repo, "status", "--porcelain")
    out = capsys.readouterr().out
    assert "Not committed: templates/secret_plan.json is local only. Move it to " in out


def test_sync_with_only_local_only_changes_commits_nothing_and_still_reinstalls(checkout):
    repo, upstream = checkout
    before = _git(repo, "rev-parse", "HEAD")
    _secret(repo / "templates" / "secret_plan.json")
    assert _sync(repo) is True
    assert _git(repo, "rev-parse", "HEAD") == before
    assert _remote_files(upstream) == ["templates/shared.json"]


def test_sync_never_pushes_an_unpushed_commit_that_contains_a_local_only_template(checkout, capsys):
    repo, upstream = checkout
    _secret(repo / "templates" / "secret_plan.json")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "oops")
    assert _sync(repo) is True  # reinstall still proceeds
    assert _remote_files(upstream) == ["templates/shared.json"]
    out = capsys.readouterr().out
    assert "Not pushing: unpushed commits include local-only templates:" in out
    assert "templates/secret_plan.json" in out


def test_sync_keeps_a_hand_staged_local_only_template_out_of_the_commit(checkout):
    repo, upstream = checkout
    _write(repo / "templates" / "shared.json", "Shared", note="edited")
    _secret(repo / "templates" / "secret_plan.json")
    _git(repo, "add", "-A")  # staged by habit before syncing
    assert _sync(repo) is True
    assert _remote_files(upstream) == ["templates/shared.json"]
    assert "edited" in _git(upstream, "show", "main:templates/shared.json")
    assert "PRIVATE-CONTENT-123" not in _history(upstream)
    assert "?? templates/secret_plan.json" in _git(repo, "status", "--porcelain")


@pytest.mark.parametrize("cover_up", ["removed-by-a-later-commit", "renamed-on-disk"])
def test_sync_never_pushes_history_that_still_carries_a_local_only_version(
    checkout, capsys, cover_up
):
    repo, upstream = checkout
    secret = _secret(repo / "templates" / "secret_plan.json")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "oops")
    if cover_up == "removed-by-a-later-commit":
        _git(repo, "rm", "-q", "--cached", "templates/secret_plan.json")
        _git(repo, "commit", "-q", "-m", "remove it")
    else:
        secret.rename(secret.with_name("renamed_plan.json"))
    assert _sync(repo) is True  # reinstall still proceeds
    assert "PRIVATE-CONTENT-123" not in _history(upstream)
    out = capsys.readouterr().out
    assert "Not pushing: unpushed commits include local-only templates:" in out
    assert "  templates/secret_plan.json" in out
    assert "reset --soft origin/main" in out
    _git(repo, "reset", "-q", "--soft", "origin/main")  # the fix the message names
    assert _sync(repo) is True
    assert "PRIVATE-CONTENT-123" not in _history(upstream)
    assert "Not pushing" not in capsys.readouterr().out


def test_sync_leaves_a_tracked_template_marked_local_only_unpublished(checkout):
    repo, upstream = checkout
    _write(repo / "templates" / "shared.json", "Shared", local_only=True, note="private edit")
    assert _sync(repo) is True
    published = subprocess.run(
        ["git", "--git-dir", str(upstream), "show", "main:templates/shared.json"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "private edit" not in published and "local_only" not in published


# ── Delivery route and bundled invariant ─────────────────────────────────────


def _deliver_module():
    spec = importlib.util.spec_from_file_location("deliver_lo", ROOT / "scripts" / "deliver.py")
    deliver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(deliver)
    return deliver


def test_deliver_refuses_a_local_only_template(tmp_path, monkeypatch, capsys):
    deliver = _deliver_module()
    checkout = tmp_path / "checkout"
    _secret(checkout / "templates" / "secret_plan.json")
    monkeypatch.setattr(deliver, "ROOT", checkout)
    calls = []

    def runner(argv, cwd=None, **kwargs):
        calls.append(" ".join(argv))
        out = {"git rev-parse --abbrev-ref HEAD": "main\n"}.get(" ".join(argv), "")
        if argv[:3] == ["git", "status", "--porcelain"]:
            out = "?? templates/secret_plan.json\n"
        return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")

    delivery = deliver.Delivery(
        branch="agent/feat-private",
        message="feat: private\n",
        body=None,
        paths=["templates/secret_plan.json"],
        runner=runner,
        python="py",
        sleep=lambda _: None,
    )
    assert delivery.deliver() == deliver.EXIT_PREFLIGHT
    assert "local-only templates are never delivered: ['templates/secret_plan.json']" in (
        capsys.readouterr().out
    )
    assert not [c for c in calls if c.startswith(("git add", "git commit", "git push", "gh "))]


def test_deliver_refuses_unpushed_commits_that_carry_a_local_only_version(
    tmp_path, monkeypatch, capsys
):
    deliver = _deliver_module()
    checkout = tmp_path / "checkout"
    _write(checkout / "templates" / "shared.json", "Shared")
    monkeypatch.setattr(deliver, "ROOT", checkout)
    blob = "b" * 40
    raw = f":000000 100644 {'0' * 40} {blob} A\0templates/old_plan.json\0".encode()
    private = json.dumps({"name": "Old", "content": "PRIVATE", "local_only": True}).encode()
    calls = []

    def runner(argv, cwd=None, **kwargs):
        key = " ".join(argv)
        calls.append(key)
        if argv == ["git", "cat-file", "blob", blob]:
            return subprocess.CompletedProcess(argv, 0, stdout=private, stderr=b"")
        out = {"git rev-parse --abbrev-ref HEAD": "main\n"}.get(key, "")
        if argv[:3] == ["git", "status", "--porcelain"]:
            out = " M templates/shared.json\n"
        if argv[:3] == ["git", "remote", "get-url"]:
            out = "https://github.com/o/r.git\n"  # its ls-remote answers that it has nothing
        if argv[:2] == ["git", "log"] and "HEAD" in argv:
            out = raw
        return subprocess.CompletedProcess(argv, 0, stdout=out, stderr="")

    delivery = deliver.Delivery(
        branch="agent/feat-shared",
        message="feat: shared\n",
        body=None,
        paths=["templates/shared.json"],
        runner=runner,
        python="py",
        sleep=lambda _: None,
    )
    assert delivery.deliver() == deliver.EXIT_PREFLIGHT
    assert "carry local-only templates, never delivered: ['templates/old_plan.json']" in (
        capsys.readouterr().out
    )
    assert not [c for c in calls if c.startswith(("git add", "git commit", "git push", "gh "))]


def test_no_bundled_template_is_local_only():
    """This repository is public: a local-only prompt never ships in templates/."""
    assert local_only_template_paths(ROOT / "templates") == []


# ── Local surfaces show the flag ─────────────────────────────────────────────


def test_list_marks_local_only_templates(tmp_path, capsys):
    import espansr.__main__ as cli

    _write(tmp_path / "shared.json", "Shared")
    _write(tmp_path / "mine.json", "Mine", local_only=True)
    with patch(
        "espansr.core.templates.get_template_manager",
        return_value=TemplateManager(templates_dir=tmp_path),
    ):
        assert cli.cmd_list(argparse.Namespace()) == 0
    lines = capsys.readouterr().out.splitlines()
    assert any(":mine" in line and line.endswith("(local only)") for line in lines)
    assert any(":shared" in line and "local only" not in line for line in lines)


@pytest.fixture()
def editor(qtbot, tmp_path):
    from espansr.ui.template_editor import TemplateEditorWidget

    manager = TemplateManager(templates_dir=tmp_path)
    with (
        patch("espansr.ui.template_editor.get_template_manager", return_value=manager),
        patch("espansr.ui.template_editor.get_config"),
    ):
        widget = TemplateEditorWidget()
        qtbot.addWidget(widget)
        yield widget, manager


def test_editor_toggle_saves_and_reloads_the_flag(editor):
    widget, manager = editor
    widget._name_edit.setText("Mine")
    widget._trigger_edit.setText(":mine")
    widget._content_edit.setPlainText("private body")
    widget._local_only_check.setChecked(True)
    saved = widget.save_current(emit_signal=False)
    on_disk = json.loads(saved._path.read_text(encoding="utf-8"))
    assert on_disk["local_only"] is True

    widget.load_template(manager.get("Mine"))
    assert widget._local_only_check.isChecked()
    assert not widget.has_unsaved_changes()
    widget._local_only_check.setChecked(False)
    assert widget.has_unsaved_changes()
    widget.save_current(emit_signal=False)
    assert "local_only" not in json.loads(saved._path.read_text(encoding="utf-8"))
    widget.clear()
    assert not widget._local_only_check.isChecked()


@pytest.mark.parametrize("local_only", [True, False])
def test_command_detail_shows_local_only(qtbot, local_only):
    from espansr.ui.commands_popup import CommandRowWidget

    entry = CommandCatalogEntry(
        ":mine", "Mine", "desc", "preview", "template", capability_id="mine", local_only=local_only
    )
    row = CommandRowWidget(entry)
    qtbot.addWidget(row)
    assert row._local_only_label.isVisibleTo(row) is local_only
    assert (row._local_only_label.text() == LOCAL_ONLY_TEXT) is local_only
