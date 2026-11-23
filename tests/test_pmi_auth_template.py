"""Exercise the shipped launcher; PMI owns authentication and its own tests.

These shell fixtures never authenticate, access the network or run a live trigger.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from espansr.core.templates import TemplateManager
from espansr.integrations.espanso import sync_to_espanso

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "pmi_auth.json"
BASH = shutil.which("bash")
PMI_REMOTE = "https://github.com/josiahH-cf/pmiKCkb_and_ownerRouter.git"
VERIFIED_REF = "refs/pmi/auth-verified"


def _git(root, *args):
    return subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


def _data():
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


@pytest.fixture
def launcher(tmp_path):
    if os.name == "nt" or not BASH or not shutil.which("python3") or not shutil.which("git"):
        pytest.skip("Behavioral launcher tests require native POSIX Bash and python3")
    tmp_path = tmp_path.resolve()
    home = tmp_path / "WSL home 'quoted $literal"
    home.mkdir()
    registration = home / ".local/state/pmi-kc-release/checkout-pair.json"
    registration.parent.mkdir(parents=True)
    repository = home / "repository"
    repository.mkdir()
    _git(repository, "init", "-q")
    _git(repository, "config", "user.name", "Fixture")
    _git(repository, "config", "user.email", "fixture@example.invalid")
    _git(repository, "remote", "add", "origin", PMI_REMOTE)
    (repository / ".gitignore").write_text(".env.local\n", encoding="utf-8")
    tracked = repository / "scripts/pmi-auth"
    tracked.parent.mkdir()
    tracked.write_text("exit 91\n", encoding="utf-8")
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "held release fixture")
    release = home / "release 'quoted $literal"
    _git(repository, "worktree", "add", "-q", "--detach", str(release))
    (release / ".env.local").write_text("fixture-only\n", encoding="utf-8")
    tracked.write_text(
        'printf "%s\\n" "$0" "$PWD" "$#" "${BASH_VERSION:+bash}"\n'
        'read -r reply\nprintf "%s\\n" "$reply"\nexit "${TEST_AUTH_EXIT:-0}"\n',
        encoding="utf-8",
    )
    _git(repository, "commit", "-qam", "auth-only fixture")
    auth = home / "auth-current"
    _git(repository, "worktree", "add", "-q", "--detach", str(auth))
    _git(repository, "update-ref", VERIFIED_REF, "HEAD")
    (auth / ".env.local").symlink_to(release / ".env.local")
    entry = auth / "scripts/pmi-auth"
    pair = {
        "schemaVersion": 1,
        "repository": "josiahH-cf/pmiKCkb_and_ownerRouter",
        "nativeRoot": str(release),
        "sourceRoot": str(home / "unused source checkout"),
    }
    registration.write_text(json.dumps(pair), encoding="utf-8")
    unrelated = tmp_path / "unrelated directory"
    unrelated.mkdir()

    def run(status=0):
        return subprocess.run(
            [BASH, "--noprofile", "--norc", "-c", _data()["content"]],
            cwd=unrelated,
            env={**os.environ, "HOME": str(home), "TEST_AUTH_EXIT": str(status)},
            input="inherited terminal input\n",
            text=True,
            capture_output=True,
            timeout=10,
        )

    return run, registration, pair, entry, unrelated


def test_pmi_auth_delegates_without_private_values_or_duplicated_auth():
    data = _data()
    content = data["content"]
    assert data["trigger"] == ":pmi-auth"
    assert data["category"] == "utility"
    assert data["stage"] == "authentication"
    assert not data.get("variables")
    assert len(content.encode("utf-8")) < 2700
    assert content.startswith("(\n  set -euo pipefail\n")
    assert content.endswith('  exec bash "$pmi_auth_root/scripts/pmi-auth"\n)\n')
    assert ".local/state/pmi-kc-release/checkout-pair.json" in content
    assert VERIFIED_REF in content
    assert "/auth-current" in content
    assert not re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", content.replace("git@github.com:", ""))
    for forbidden in ("/home/", "/mnt/", "auth-command-", "ensureAuthenticated", "<<", "{{"):
        assert forbidden not in content


def test_pmi_auth_published_yaml_preserves_exact_expansion_bytes(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    shutil.copyfile(TEMPLATE, templates / TEMPLATE.name)
    matches = tmp_path / "match"
    matches.mkdir()
    with (
        patch("espansr.integrations.espanso.get_match_dir", return_value=matches),
        patch(
            "espansr.integrations.espanso.get_template_manager",
            return_value=TemplateManager(templates_dir=templates),
        ),
    ):
        assert sync_to_espanso(update_bundled=False)
    generated = yaml.safe_load((matches / "espansr.yml").read_text(encoding="utf-8"))
    match = next(m for m in generated["matches"] if m["trigger"] == ":pmi-auth")
    assert match["replace"].encode("utf-8") == _data()["content"].encode("utf-8")
    assert not match.get("vars")


@pytest.mark.parametrize("status", [0, 1, 2, 3, 130])
def test_launcher_preserves_paths_stdin_shell_and_entrypoint_exit(launcher, status):
    run, _, _, entry, unrelated = launcher
    result = run(status)
    assert result.returncode == status, result.stderr
    assert result.stdout.splitlines() == [
        str(entry),
        str(unrelated),
        "0",
        "bash",
        "inherited terminal input",
    ]
    assert not result.stderr


@pytest.mark.parametrize("bad", [None, "{PRIVATE_INVALID_JSON", "[]", "wrong-repository"])
def test_unavailable_or_invalid_registration_stops_without_dispatch(launcher, bad):
    run, registration, pair, _, _ = launcher
    if bad is None:
        registration.unlink()
    elif bad == "wrong-repository":
        pair["repository"] = "example/other-repository"
        registration.write_text(json.dumps(pair), encoding="utf-8")
    else:
        registration.write_text(bad, encoding="utf-8")
    result = run()
    assert result.returncode == 1
    assert not result.stdout
    assert "registered PMI WSL release is unavailable" in result.stderr
    assert "PRIVATE_INVALID_JSON" not in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "root",
    [
        "missing",
        "relative",
        "unverified",
        "wrong-remote",
        "wrong-commit",
        "stale-config",
        "untracked",
    ],
)
def test_unavailable_entrypoint_stops_without_fallback(launcher, root):
    run, registration, pair, entry, _ = launcher
    if root == "missing":
        entry.unlink()
    elif root == "relative":
        pair["nativeRoot"] = "relative-release"
        registration.write_text(json.dumps(pair), encoding="utf-8")
    elif root == "unverified":
        _git(entry.parents[1], "update-ref", "-d", VERIFIED_REF)
    elif root == "wrong-remote":
        _git(entry.parents[1], "remote", "set-url", "origin", "https://example.invalid/wrong")
    elif root == "wrong-commit":
        _git(entry.parents[1], "update-ref", VERIFIED_REF, "HEAD^")
    elif root == "stale-config":
        entry.parents[1].joinpath(".env.local").unlink()
    else:
        entry.parents[1].joinpath("untracked.txt").touch()
    result = run()
    assert result.returncode == 1
    assert not result.stdout
    assert "verified PMI auth checkout is unavailable" in result.stderr


def test_launcher_stays_on_verified_auth_when_registered_release_changes(launcher):
    run, registration, pair, entry, _ = launcher
    assert run().returncode == 0
    auth = entry.parents[1]
    next_release = auth.with_name("next registered release")
    _git(auth, "worktree", "add", "-q", "--detach", str(next_release), "HEAD^")
    (next_release / ".env.local").write_text("fixture-only\n", encoding="utf-8")
    pair["nativeRoot"] = str(next_release)
    registration.write_text(json.dumps(pair), encoding="utf-8")
    assert run().returncode == 1
    (auth / ".env.local").unlink()
    (auth / ".env.local").symlink_to(next_release / ".env.local")
    result = run(3)
    assert result.returncode == 3
    assert result.stdout.splitlines()[0] == str(entry)
