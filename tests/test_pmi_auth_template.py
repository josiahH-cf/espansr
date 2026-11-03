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


def _data():
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


@pytest.fixture
def launcher(tmp_path):
    if os.name == "nt" or not BASH or not shutil.which("python3"):
        pytest.skip("Behavioral launcher tests require native POSIX Bash and python3")
    home = tmp_path / "WSL home 'quoted $literal"
    home.mkdir()
    registration = home / ".local/state/pmi-kc-release/checkout-pair.json"
    registration.parent.mkdir(parents=True)
    release = home / "release 'quoted $literal"
    entry = release / "scripts/pmi-auth"
    entry.parent.mkdir(parents=True)
    entry.write_text(
        'printf "%s\\n" "$0" "$PWD" "$#" "${BASH_VERSION:+bash}"\n'
        'read -r reply\nprintf "%s\\n" "$reply"\nexit "${TEST_AUTH_EXIT:-0}"\n',
        encoding="utf-8",
    )
    # Deliberately not executable: the shipped command must select Bash itself.
    entry.chmod(0o600)
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
    assert len(content.encode("utf-8")) < 1200
    assert content.startswith("(\n  set -euo pipefail\n")
    assert content.endswith('  exec bash "$pmi_auth_root/scripts/pmi-auth"\n)\n')
    assert ".local/state/pmi-kc-release/checkout-pair.json" in content
    assert not re.search(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", content)
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


@pytest.mark.parametrize("root", ["missing", "relative"])
def test_unavailable_entrypoint_stops_without_fallback(launcher, root):
    run, registration, pair, entry, _ = launcher
    if root == "missing":
        entry.unlink()
    else:
        pair["nativeRoot"] = "relative-release"
        registration.write_text(json.dumps(pair), encoding="utf-8")
    result = run()
    assert result.returncode == 1
    assert not result.stdout
    assert "no readable scripts/pmi-auth entrypoint" in result.stderr


def test_launcher_follows_the_next_registered_release(launcher):
    run, registration, pair, entry, _ = launcher
    assert run().returncode == 0
    next_release = entry.parents[1].with_name("next registered release")
    next_entry = next_release / "scripts/pmi-auth"
    next_entry.parent.mkdir(parents=True)
    next_entry.write_text("printf 'next release\\n'\nexit 3\n", encoding="utf-8")
    pair["nativeRoot"] = str(next_release)
    registration.write_text(json.dumps(pair), encoding="utf-8")
    entry.unlink()
    result = run()
    assert result.returncode == 3
    assert result.stdout == "next release\n"
