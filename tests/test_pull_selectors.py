"""`espansr pull --template` takes exact file names: never a folder, pattern or pathspec.

Real Git with a local bare remote, in the reviewed shape: the remote has public
personal/private.json and personal/shared.json, this machine marked
personal/private.json local only with private content, and the remote's
shared.json moved on. Whatever selector is given, the private bytes and flag
stay; a folder, pattern or pathspec magic is refused before anything changes.
"""

import json
import logging
import subprocess
from pathlib import Path

import pytest

import espansr.__main__ as cli
from espansr.core.config import Config, ConfigManager
from espansr.core.remote import RemoteError, RemoteManager

PUBLIC = {"name": "Synthetic template", "content": "SYNTHETIC REMOTE PUBLIC VALUE", "trigger": ":p"}
PRIVATE = {**PUBLIC, "content": "SYNTHETIC PRIVATE LOCAL VALUE", "local_only": True}


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


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture()
def store(tmp_path):
    bare, seed, repo = tmp_path / "remote.git", tmp_path / "seed", tmp_path / "repo"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    _git(tmp_path, "init", "-q", "-b", "main", str(seed))
    _write(seed / "personal" / "private.json", PUBLIC)
    _write(
        seed / "personal" / "shared.json", {"name": "Shared", "content": "shared", "trigger": ":s"}
    )
    _write(seed / "personal" / "notes[1].json", {"name": "N", "content": "n v1", "trigger": ":n"})
    _git(seed, "add", ".")
    _git(seed, "commit", "-q", "-m", "public templates")
    _git(seed, "remote", "add", "origin", str(bare))
    _git(seed, "push", "-q", "origin", "main")
    _git(tmp_path, "clone", "-q", str(bare), str(repo))
    for name, data in (
        ("shared.json", {"name": "Shared", "content": "shared v2", "trigger": ":s"}),
        ("notes[1].json", {"name": "N", "content": "n v2", "trigger": ":n"}),
        ("private.json", {**PUBLIC, "content": "SYNTHETIC REMOTE PUBLIC VALUE v2"}),
    ):
        _write(seed / "personal" / name, data)
    _git(seed, "commit", "-q", "-am", "remote moves on")
    _git(seed, "push", "-q", "origin", "main")
    _write(repo / "personal" / "private.json", PRIVATE)
    config = ConfigManager(config_path=tmp_path / "config.json")
    config.save(Config())
    return repo, RemoteManager(templates_dir=repo, config_manager=config)


def _private_kept(repo: Path) -> bool:
    data = json.loads((repo / "personal" / "private.json").read_text(encoding="utf-8"))
    return data == PRIVATE


def _shared(repo: Path) -> str:
    return json.loads((repo / "personal" / "shared.json").read_text(encoding="utf-8"))["content"]


@pytest.mark.parametrize(
    "name",
    ["personal/private.json", "./personal/private.json", "personal/../personal/private.json"],
)
def test_an_exact_private_name_is_skipped_and_its_bytes_and_flag_stay(store, name, caplog):
    repo, remote = store
    with caplog.at_level(logging.WARNING, logger="espansr.core.remote"):
        assert remote.pull_templates([name]) is True
    assert _private_kept(repo)
    assert (remote.pulled, remote.skipped_local_only) == ([], ["personal/private.json"])
    assert "it is local only here and is never replaced" in caplog.text


def test_an_exact_public_name_is_pulled(store):
    repo, remote = store
    assert remote.pull_templates(["personal/shared.json"]) is True
    assert _shared(repo) == "shared v2"
    assert remote.pulled == ["personal/shared.json"]
    assert _private_kept(repo)


@pytest.mark.parametrize("name", ["personal", "personal/", "./personal"])
def test_a_folder_is_refused_and_nothing_changes(store, name):
    repo, remote = store
    with pytest.raises(RemoteError, match="is a folder; name the template files in it"):
        remote.pull_templates(["personal/shared.json", name])
    assert _private_kept(repo)
    assert _shared(repo) == "shared"


@pytest.mark.parametrize(
    "name",
    [
        "personal/*.json",
        "personal/*",
        "*.json",
        "personal/priv?te.json",
        "personal/[ps]*.json",
        ":(glob)personal/*.json",
        ":(literal)personal/private.json",
        ":(top)personal/private.json",
        ":/personal/private.json",
        ":!personal/shared.json",
    ],
)
def test_a_pattern_or_pathspec_is_refused_and_nothing_changes(store, name):
    repo, remote = store
    with pytest.raises(RemoteError, match="is a pattern, not a template file name") as refused:
        remote.pull_templates(["personal/shared.json", name])
    assert "Nothing was changed." in str(refused.value)
    assert _private_kept(repo)
    assert _shared(repo) == "shared"  # the exact public name in the same call waits too
    assert _git(repo, "status", "--porcelain") == "M personal/private.json"


def test_a_file_whose_name_holds_pattern_characters_is_pulled_by_that_exact_name(store):
    repo, remote = store
    assert remote.pull_templates(["personal/notes[1].json"]) is True
    data = json.loads((repo / "personal" / "notes[1].json").read_text(encoding="utf-8"))
    assert data["content"] == "n v2"
    assert _private_kept(repo)


def test_the_pull_command_says_why_a_pattern_is_refused(store, monkeypatch, capsys):
    repo, remote = store
    monkeypatch.setattr("espansr.core.remote.RemoteManager", lambda *a, **k: remote)
    args = type("A", (), {"template": [":(glob)personal/*.json"]})()
    assert cli.cmd_pull(args) == 1
    out = capsys.readouterr().out
    assert ":(glob)personal/*.json is a pattern, not a template file name" in out
    assert _private_kept(repo)
