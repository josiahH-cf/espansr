"""Current privacy wins on every read, restore, refresh, pull and push.

A template made local only stops being shared from the moment it is marked:
a retained catalog publication that still describes it is withdrawn when it is
read, not just at the next publish; restoring an older version keeps it
private; a private starter keeps its trigger in any folder; a pull never puts
the remote's file over it, whatever name the pull was given; and every push
entry point reads the outgoing commits right before it pushes. Real files and
real Git (disposable repositories and bare remotes) throughout.
"""

import base64
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from espansr import __main__ as cli
from espansr.core import capability_catalog as cc
from espansr.core.command_catalog import build_command_catalog
from espansr.core.config import Config, ConfigManager
from espansr.core.remote import RemoteConflictError, RemoteError, RemoteManager
from espansr.core.templates import (
    Template,
    TemplateManager,
    local_only_state,
    sync_bundled_templates_to_live,
)
from espansr.integrations import espanso

ROOT = Path(__file__).resolve().parents[1]
SECRET = "PRIVATE-ROUND-SIX-6642"
needs_file_modes = pytest.mark.skipif(
    sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permission bits that apply to this user",
)


def _write(path: Path, name: str, content: str = "", **extra) -> Path:
    data = {"name": name, "content": content or f"{name} body", "trigger": f":{name.lower()}"}
    data.update(extra)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _mark_private(path: Path) -> Path:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["local_only"] = True
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    ).stdout


@pytest.fixture()
def git_identity(monkeypatch):
    for key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(key, "espansr test")
    for key in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(key, "test@example.invalid")


# ─── Finding 1: a retained publication never re-exposes a private template ───


def _shared(text: str) -> list[str]:
    """What of template A a shared output carries: entry, text, definition bytes."""
    found = [
        label for label, marker in (("entry", "template:a"), ("text", SECRET)) if marker in text
    ]
    for chunk in text.split('"definition_bytes"')[1:]:
        encoded = chunk.split('"')[1]
        if SECRET in base64.b64decode(encoded).decode("utf-8", "replace"):
            found.append("definition")
    return found


@pytest.fixture()
def published(tmp_path):
    """A qualified publication of A (with its definition) and B."""

    def make(names=("A", "B")):
        source, installed = tmp_path / "source", tmp_path / "installed"
        for name in names:
            private = name == "A"
            content = f"{name} body {SECRET if private else ''}"
            extra = {"description": f"{SECRET} what A does"} if private else {}
            for root in (source, installed):
                _write(
                    root / f"{name.lower()}.json", name, content, publish_definition=True, **extra
                )
        assert cc.publish_catalog(source, installed)["publication"] == "qualified"
        assert _shared(json.dumps(cc.read_publication(installed))) == [
            "entry",
            "text",
            "definition",
        ]
        return source, installed

    return make


def _toggle(source, installed, shape):
    if shape == "source-copy":
        _mark_private(source / "a.json")
    else:
        _mark_private(installed / "a.json")
    if shape == "all-private":
        _mark_private(installed / "b.json")
    if shape == "with-drift":
        _write(installed / "b.json", "B", "B edited here", publish_definition=True)


SHAPES = ["with-drift", "sole-template", "source-copy", "all-private"]


def _names(shape):
    return ("A",) if shape in ("sole-template", "source-copy") else ("A", "B")


@pytest.mark.parametrize("shape", SHAPES)
def test_inspect_withdraws_a_publication_that_describes_a_template_made_private(published, shape):
    source, installed = published(_names(shape))
    _toggle(source, installed, shape)

    result = cc.inspect_catalog(source, installed)

    assert _shared(json.dumps(result)) == []  # metadata and definition alike
    catalog = result["published"] or result["current"]
    assert _shared(json.dumps(cc.select_entries(catalog))) == []
    assert not (installed / cc.PUBLICATION_PATH).exists()  # connected tools can't read it
    assert (result["status"], result["published"], result["withdrawn_file_removed"]) == (
        "withdrawn",
        None,
        True,
    )


@pytest.mark.parametrize("shape", SHAPES)
def test_espansr_catalog_json_shows_nothing_of_a_template_made_private(published, shape, capsys):
    source, installed = published(_names(shape))
    _toggle(source, installed, shape)
    args = SimpleNamespace(
        source=str(source),
        installed=str(installed),
        capability=None,
        host=None,
        client=None,
        input=None,
        intent=None,
        select=None,
        json=True,
    )
    cli.cmd_catalog(args)
    out = capsys.readouterr().out
    assert _shared(out) == []
    assert json.loads(out)["status"] == "withdrawn"
    cli.cmd_catalog(SimpleNamespace(**{**vars(args), "json": False}))
    assert "Capability publication: unavailable" in capsys.readouterr().out  # already removed


@pytest.mark.parametrize("shape", SHAPES)
def test_the_commands_popup_carries_no_descriptor_for_a_template_made_private(
    published, shape, monkeypatch
):
    source, installed = published(_names(shape))
    _toggle(source, installed, shape)
    monkeypatch.setattr("espansr.core.templates.get_bundled_templates_dir", lambda *a, **k: source)
    stub = SimpleNamespace(workflows_for=lambda cap: [], outgoing=lambda cap: [])

    entries = build_command_catalog(TemplateManager(templates_dir=installed), workflow_catalog=stub)

    rows = {entry.trigger: entry for entry in entries}
    assert rows[":a"].capability_descriptor == {}  # A still expands here, unshared
    assert rows[":a"].publication_status == "withdrawn"
    assert _shared(json.dumps([e.capability_descriptor for e in entries])) == []


def test_the_next_complete_publication_returns_without_the_private_template(published):
    source, installed = published()
    _toggle(source, installed, "with-drift")
    withdrawn = cc.inspect_catalog(source, installed)
    _write(installed / "b.json", "B", "B body ", publish_definition=True)  # parity again
    catalog = cc.publish_catalog(source, installed)
    assert [e["id"] for e in catalog["entries"]] == ["template:b"]
    assert cc.inspect_catalog(source, installed)["status"] == "current"
    assert withdrawn["status"] == "withdrawn"


def test_a_publication_with_no_private_template_is_returned_exactly(published):
    source, installed = published()
    file_bytes = (installed / cc.PUBLICATION_PATH).read_bytes()
    _write(installed / "b.json", "B", "B edited here", publish_definition=True)  # drift only

    result = cc.inspect_catalog(source, installed)

    assert result["status"] == "drift"
    assert result["published"] == cc.read_publication(installed)  # not a filtered derivative
    assert cc.digest({k: v for k, v in result["published"].items() if k != "catalog_sha256"}) == (
        result["published"]["catalog_sha256"]
    )
    assert (installed / cc.PUBLICATION_PATH).read_bytes() == file_bytes


@needs_file_modes
def test_a_withdrawal_that_cannot_remove_the_file_still_hides_it(published, capsys):
    source, installed = published()
    _toggle(source, installed, "with-drift")
    meta = installed / "_meta"
    meta.chmod(0o555)
    try:
        result = cc.inspect_catalog(source, installed)
        assert _shared(json.dumps(result)) == []
        with pytest.raises(cc.PublicationWithdrawalFailed, match="could not be removed"):
            cc.publish_catalog(source, installed)
        cli.cmd_catalog(
            SimpleNamespace(
                source=str(source),
                installed=str(installed),
                capability=None,
                host=None,
                client=None,
                input=None,
                intent=None,
                select=None,
                json=False,
            )
        )
    finally:
        meta.chmod(0o755)
    assert (result["status"], result["published"]) == ("withdrawn", None)
    assert result["withdrawn_file_removed"] is False
    assert _shared(json.dumps(result)) == []
    out = capsys.readouterr().out
    assert "Capability publication: withdrawn" in out
    assert "Could not remove" in out and "connected tools can still read it" in out


def test_publishing_reports_the_withdrawal_and_never_claims_a_kept_publication(
    tmp_path, monkeypatch, capsys
):
    from espansr.core.config import get_templates_dir

    live, source = get_templates_dir(), tmp_path / "source"
    for name in ("A", "B"):
        for root in (source, live):
            _write(root / f"{name.lower()}.json", name, f"{name} {SECRET}", publish_definition=True)
    assert cc.publish_catalog(source, live)["publication"] == "qualified"
    _mark_private(live / "a.json")
    _write(live / "b.json", "B", "B edited here", publish_definition=True)
    espanso_dir = tmp_path / "espanso"
    (espanso_dir / "match").mkdir(parents=True)
    monkeypatch.setattr(espanso, "get_espanso_config_dir", lambda: espanso_dir)

    assert espanso.sync_to_espanso(bundled_dir=source)
    first = capsys.readouterr().out
    assert espanso.sync_to_espanso(bundled_dir=source)
    second = capsys.readouterr().out

    assert not (live / cc.PUBLICATION_PATH).exists()
    assert "Capability catalog withdrawn: it still described a template now marked local" in first
    assert "none is published until it is complete" in second
    assert "retained" not in first + second


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks need privileges on Windows")
def test_a_linked_publication_reads_as_unavailable_instead_of_failing(published, tmp_path):
    source, installed = published()
    elsewhere = tmp_path / "elsewhere"
    (installed / "_meta").rename(elsewhere)
    (installed / "_meta").symlink_to(elsewhere, target_is_directory=True)
    _mark_private(installed / "a.json")
    result = cc.inspect_catalog(source, installed)
    assert (result["status"], result["published"]) == ("unavailable", None)
    assert _shared(json.dumps(result)) == []


def test_a_new_selection_of_a_template_made_private_is_refused(published):
    source, installed = published()
    held = cc.read_publication(installed)  # a caller still holding the old catalog
    _mark_private(installed / "a.json")
    with pytest.raises(ValueError, match="kept private on this machine"):
        cc.freeze_definition(held, "template:a", installed, values={}, context_binding={})
    frozen = cc.freeze_definition(held, "template:b", installed, values={}, context_binding={})
    assert cc.render_frozen(frozen) == "B body "


def test_a_job_frozen_before_the_toggle_still_replays_unchanged(published):
    source, installed = published()
    catalog = cc.read_publication(installed)
    frozen = cc.freeze_definition(catalog, "template:a", installed, values={}, context_binding={})
    _mark_private(installed / "a.json")
    cc.inspect_catalog(source, installed)  # withdraws the publication
    assert SECRET in cc.render_frozen(frozen)  # history is not rewritten


# ─── Finding 2: restoring content never changes sharing ──────────────────────


@pytest.mark.parametrize("stale", [False, True], ids=["current-object", "object-from-before"])
def test_restoring_a_public_version_keeps_a_template_made_private(tmp_path, stale):
    manager = TemplateManager(templates_dir=tmp_path)
    diary = Template(name="Diary", content="public v1", trigger=":diary")
    manager.save(diary)
    manager.create_version(diary, note="v1")
    before_toggle = manager.load(diary._path)
    diary.content, diary.local_only = f"{SECRET} v2", True
    manager.save(diary)

    restored = manager.restore_version(before_toggle if stale else diary, 1)

    assert restored.content == "public v1"
    assert restored.local_only is True
    assert local_only_state(restored._path) == "private"


def test_a_restored_private_template_stays_out_of_the_catalog_and_the_remote(
    tmp_path, git_identity
):
    store, bare = tmp_path / "store", tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    store.mkdir()
    _git(store, "init", "-q", "-b", "main")
    manager = TemplateManager(templates_dir=store)
    _write(store / "greeting.json", "Greeting")
    diary = Template(name="Diary", content="public v1", trigger=":diary")
    manager.save(diary)
    config = ConfigManager(config_path=tmp_path / "config.json")
    config.save(Config())
    remote = RemoteManager(templates_dir=store, config_manager=config)
    remote.set_remote(str(bare))
    remote.push()  # v1 shared earlier: already-exported history stays as it is
    manager.create_version(diary, note="v1")
    diary.content, diary.local_only = f"{SECRET} v2", True
    manager.save(diary)
    stale = manager.load(diary._path)
    stale.local_only = False  # an object that never saw the toggle
    manager.restore_version(stale, 1)

    assert "template:diary" not in json.dumps(cc.build_catalog(store, None))
    remote.push()
    tree = _git(bare, "ls-tree", "-r", "--name-only", "main").split()
    assert "diary.json" not in tree and "greeting.json" in tree
    assert SECRET not in _git(bare, "log", "--all", "-p")
    assert local_only_state(store / "diary.json") == "private"


# ─── Finding 3: a private starter owns its trigger in any folder ─────────────


@pytest.fixture()
def moved_starter(tmp_path, monkeypatch):
    """The live store (the config's) with the private starter moved into folders."""
    from espansr.core.config import get_templates_dir

    live = get_templates_dir()
    bundled = tmp_path / "bundled"
    _write(bundled / "starter.json", "Starter", "canonical")
    _write(bundled / "other.json", "Other", "canonical other")
    mine = _write(
        live / "personal" / "deep" / "my_starter.json",
        "Starter",
        f"{SECRET} mine",
        local_only=True,
    )
    assert json.loads(mine.read_text(encoding="utf-8"))["trigger"] == ":starter"
    return live, bundled, mine, mine.read_bytes()


def _after_refresh(live, mine, before):
    assert not (live / "starter.json").exists()  # no public twin
    assert mine.read_bytes() == before and local_only_state(mine) == "private"
    assert (live / "other.json").exists()  # other starters still arrive


def test_starter_updates_never_seed_a_twin_of_a_moved_private_starter(moved_starter):
    live, bundled, mine, before = moved_starter
    report, result = sync_bundled_templates_to_live(templates_dir=live, bundled_dir=bundled)
    assert result.copied == 1 and not report.errors
    _after_refresh(live, mine, before)


def test_setup_never_seeds_a_twin_of_a_moved_private_starter(moved_starter, monkeypatch, capsys):
    live, bundled, mine, before = moved_starter
    monkeypatch.setattr(cli, "get_espanso_config_dir", lambda: None)
    monkeypatch.setattr(cli, "_get_bundled_dir", lambda: bundled)
    cli.cmd_setup(SimpleNamespace(strict=False, dry_run=False, verbose=True))
    out = capsys.readouterr().out
    _after_refresh(live, mine, before)
    assert "Duplicate trigger" not in out
    assert "starter.json: skipped (its trigger belongs to your local-only template)" in out


def test_publishing_with_starter_updates_expands_the_moved_private_starter(
    moved_starter, tmp_path, monkeypatch, capsys
):
    live, bundled, mine, before = moved_starter
    espanso_dir = tmp_path / "espanso"
    (espanso_dir / "match").mkdir(parents=True)
    monkeypatch.setattr(espanso, "get_espanso_config_dir", lambda: espanso_dir)

    assert espanso.sync_to_espanso(update_bundled=True, bundled_dir=bundled)

    assert "Duplicate trigger" not in capsys.readouterr().out
    _after_refresh(live, mine, before)
    matches = (espanso_dir / "match" / "espansr.yml").read_text(encoding="utf-8")
    assert matches.count("trigger: :starter") == 1 and f"{SECRET} mine" in matches


def test_the_live_listing_never_counts_copies_kept_inside_git(tmp_path):
    _write(tmp_path / "notes.json", "Notes")
    _write(tmp_path / ".git" / "espansr-local-only-20261104" / "notes.json", "Notes")
    names = [t._path.relative_to(tmp_path).as_posix() for t in TemplateManager(tmp_path).list_all()]
    assert names == ["notes.json"]


# ─── Finding 4: a pull never replaces a private template ─────────────────────


@pytest.fixture()
def stores(tmp_path, git_identity):
    """This machine's store with notes.json and personal/diary.json shared, then marked
    private; another machine changes both on the remote."""
    bare, store, other = tmp_path / "remote.git", tmp_path / "store", tmp_path / "other"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    store.mkdir()
    _git(store, "init", "-q", "-b", "main")
    for rel in ("greeting.json", "notes.json", "personal/diary.json"):
        _write(store / rel, Path(rel).stem.title(), "shared v1")
    config = ConfigManager(config_path=tmp_path / "config.json")
    config.save(Config())
    remote = RemoteManager(templates_dir=store, config_manager=config)
    remote.set_remote(str(bare))
    remote.push()
    subprocess.run(["git", "clone", "-q", str(bare), str(other)], check=True)
    return bare, store, other, remote


def _change_remote(other: Path, change) -> None:
    _git(other, "pull", "-q", "--rebase")
    change(other)
    _git(other, "add", "-A")
    _git(other, "commit", "-q", "-m", "other machine")
    _git(other, "push", "-q")


def _private_pair(store, other):
    for rel in ("notes.json", "personal/diary.json"):
        path = store / rel
        _write(path, path.stem.title(), f"{SECRET} {rel}", local_only=True)
    _change_remote(
        other,
        lambda o: [
            _write(o / rel, Path(rel).stem.title(), "remote v2")
            for rel in ("greeting.json", "notes.json", "personal/diary.json")
        ],
    )
    return {rel: (store / rel).read_bytes() for rel in ("notes.json", "personal/diary.json")}


@pytest.mark.parametrize(
    "name",
    ["notes.json", "./notes.json", "personal/../notes.json", "ABSOLUTE", "personal/diary.json"],
)
def test_a_targeted_pull_never_replaces_a_private_template_whatever_the_name(stores, name):
    _, store, other, remote = stores
    saved = _private_pair(store, other)
    name = str(store / "notes.json") if name == "ABSOLUTE" else name

    remote.pull_templates([name])

    assert {rel: (store / rel).read_bytes() for rel in saved} == saved
    assert remote.pulled == [] and len(remote.skipped_local_only) == 1


@pytest.mark.parametrize("name", ["personal", ".", "..", "/elsewhere/notes.json", ".git/config"])
def test_a_targeted_pull_refuses_folders_and_paths_outside_the_store(stores, name):
    _, store, other, remote = stores
    saved = _private_pair(store, other)
    head = _git(store, "rev-parse", "HEAD")
    try:
        remote.pull_templates(["greeting.json", name])
        refused = ""
    except RemoteError as exc:
        refused = str(exc)
    assert {rel: (store / rel).read_bytes() for rel in saved} == saved
    assert "remote v2" not in (store / "greeting.json").read_text(encoding="utf-8")
    assert _git(store, "rev-parse", "HEAD") == head
    assert "Nothing was changed" in refused


def test_a_targeted_pull_refuses_a_glob_and_changes_nothing(stores):
    _, store, other, remote = stores
    saved = _private_pair(store, other)
    with pytest.raises(RemoteError, match="is a pattern, not a template file name"):
        remote.pull_templates(["greeting.json", "*.json", "personal/*"])
    assert {rel: (store / rel).read_bytes() for rel in saved} == saved
    assert "remote v2" not in (store / "greeting.json").read_text(encoding="utf-8")


def test_a_targeted_pull_still_updates_a_shareable_template(stores):
    _, store, other, remote = stores
    saved = _private_pair(store, other)
    remote.pull_templates(["greeting.json", "notes.json"])
    assert "remote v2" in (store / "greeting.json").read_text(encoding="utf-8")
    assert (remote.pulled, remote.skipped_local_only) == (["greeting.json"], ["notes.json"])
    assert {rel: (store / rel).read_bytes() for rel in saved} == saved


def test_the_pull_command_names_what_it_did_not_pull(stores, monkeypatch, capsys):
    _, store, other, remote = stores
    _private_pair(store, other)
    monkeypatch.setattr("espansr.core.remote.RemoteManager", lambda *a, **k: remote)
    monkeypatch.setattr("espansr.integrations.espanso.sync_to_espanso", lambda **k: True)
    assert cli.cmd_pull(SimpleNamespace(template=["notes.json", "greeting.json"])) == 0
    out = capsys.readouterr().out
    assert "Pulled 1 template(s) from remote: greeting.json" in out
    assert "Not pulled: notes.json is local only here" in out and "your copy is unchanged" in out
    assert "Pulled 2" not in out


def _stop_sharing(store, remote, rel="notes.json"):
    """notes.json was never shared: take it out of the store's history and the remote."""
    _git(store, "rm", "-q", "--cached", rel)
    _git(store, "commit", "-q", "-m", "stop sharing")
    _git(store, "push", "-q", "origin", "main")


def _rename_onto(o):
    _write(o / "elsewhere.json", "Elsewhere", "remote file")
    _git(o, "add", "-A")
    _git(o, "commit", "-q", "-m", "add")
    _git(o, "mv", "elsewhere.json", "notes.json")


FULL_PULL = {
    "tracked-remote-modifies": ("tracked", lambda o: _write(o / "notes.json", "Notes", "v2")),
    "tracked-remote-deletes": ("tracked", lambda o: _git(o, "rm", "-q", "notes.json")),
    "tracked-remote-renames-away": ("tracked", lambda o: _git(o, "mv", "notes.json", "x.json")),
    "ignored-remote-readds": ("ignored", lambda o: _write(o / "notes.json", "Notes", "theirs")),
    "ignored-remote-renames-onto": ("ignored", _rename_onto),
    "ignored-unrelated": ("ignored", lambda o: _write(o / "greeting.json", "Greeting", "v2")),
    "untracked-remote-adds": ("untracked", lambda o: _write(o / "notes.json", "Notes", "x")),
    "untracked-unrelated": ("untracked", lambda o: _write(o / "greeting.json", "Greeting", "v2")),
}
EXPECTED = {
    "tracked-remote-modifies": "refused",
    "tracked-remote-deletes": "stopped",
    "tracked-remote-renames-away": "stopped",
    "ignored-remote-readds": "refused",
    "ignored-remote-renames-onto": "refused",
    "ignored-unrelated": "pulled",
    "untracked-remote-adds": "refused",
    "untracked-unrelated": "pulled",
}


@pytest.mark.parametrize("case", list(FULL_PULL))
def test_a_full_pull_keeps_a_private_template_in_every_git_state(stores, case):
    bare, store, other, remote = stores
    state, change = FULL_PULL[case]
    notes = store / "notes.json"
    if state == "untracked":
        _stop_sharing(store, remote)
    _write(notes, "Notes", f"{SECRET} mine", local_only=True)
    if state == "ignored":
        remote.push()  # stops sharing it: excluded and untracked here
    before = notes.read_bytes()
    _change_remote(other, change)

    try:
        remote.pull()
        outcome = "pulled"
    except RemoteConflictError as exc:
        outcome, message = "refused", str(exc)
        assert "local only on this machine. Your copy is unchanged" in message
    except RemoteError as exc:
        outcome, message = "stopped", str(exc)
        assert "is local only here, but this store still tracks it" in message
        assert "Your copy is unchanged" in message

    assert outcome == EXPECTED[case]
    assert notes.read_bytes() == before and local_only_state(notes) == "private"
    assert SECRET not in _git(bare, "log", "--all", "-p")
    assert not (store / ".git" / "espansr-local-only").exists()


def test_an_automatic_pull_never_replaces_a_private_template(stores):
    _, store, other, remote = stores
    saved = _private_pair(store, other)
    config = remote._config_manager.config
    config.remote.auto_pull = True
    remote._config_manager.save(config)
    assert remote.auto_pull() is False  # refused, logged, non-blocking
    assert {rel: (store / rel).read_bytes() for rel in saved} == saved


# ─── Every push entry point reads the outgoing commits before pushing ────────


def _deliver_module():
    spec = importlib.util.spec_from_file_location("deliver_r6", ROOT / "scripts" / "deliver.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def delivery_checkout(tmp_path, git_identity, monkeypatch):
    """A disposable checkout with a bare origin; deliver.py runs real Git in it."""
    deliver = _deliver_module()
    bare, repo = tmp_path / "origin.git", tmp_path / "repo"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    subprocess.run(["git", "clone", "-q", str(bare), str(repo)], check=True, capture_output=True)
    _write(repo / "templates" / "shared.json", "Shared", "v1")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "push", "-q", "origin", "HEAD:main")
    monkeypatch.setattr(deliver, "ROOT", repo)

    def runner(argv, cwd=None, **kwargs):
        if argv[0] == "gh":  # GitHub is a stand-in; everything else is real
            info = {"number": 1, "state": "OPEN", "url": "https://example.invalid/pr/1"}
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(info), stderr="")
        return deliver.run(argv, cwd=repo, **kwargs)

    def delivery():
        return deliver.Delivery(
            branch="agent/feat-shared",
            message="feat: shared\n",
            body=None,
            paths=["templates/shared.json"],
            runner=runner,
            python=sys.executable,
            sleep=lambda _: None,
        )

    return deliver, bare, repo, delivery


def _reachable(bare: Path) -> str:
    objects = _git(bare, "rev-list", "--objects", "--all").split("\n")
    return "".join(
        subprocess.run(
            ["git", "-C", str(bare), "cat-file", "-p", line.split(" ")[0]],
            capture_output=True,
            text=True,
        ).stdout
        for line in objects
        if line
    )


@pytest.mark.parametrize("local_only", [True, "yes"], ids=["private", "unclear"])
def test_delivery_never_commits_or_pushes_a_template_staged_before_it(
    delivery_checkout, local_only
):
    deliver, bare, repo, delivery = delivery_checkout
    _write(repo / "templates" / "shared.json", "Shared", "v2")
    _write(repo / "templates" / "secret.json", "Secret", SECRET, local_only=local_only)
    _git(repo, "add", "-f", "templates/secret.json")

    run = delivery()
    run.preflight()
    run.publish()

    assert _git(repo, "show", "--name-only", "--format=", "HEAD").split() == [
        "templates/shared.json"
    ]
    assert "templates/secret.json" in _git(repo, "diff", "--cached", "--name-only")  # kept
    assert SECRET not in _reachable(bare)


def test_delivery_reads_the_outgoing_commits_again_right_before_pushing(delivery_checkout):
    deliver, bare, repo, delivery = delivery_checkout
    _write(repo / "templates" / "shared.json", "Shared", "v2")
    run = delivery()
    run.preflight()
    # Something commits a private template after preflight (another session, a hook).
    _write(repo / "templates" / "late.json", "Late", SECRET, local_only=True)
    _git(repo, "add", "-f", "templates/late.json")
    _git(repo, "commit", "-q", "-m", "late")

    with pytest.raises(deliver.DeliveryError) as stopped:
        run.publish()

    assert stopped.value.code == deliver.EXIT_PUBLISH
    assert "templates/late.json" in str(stopped.value)
    assert SECRET not in _reachable(bare)
    assert not [c for c in run.commands if c.startswith(("git push", "gh "))]
