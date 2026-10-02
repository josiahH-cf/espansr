"""Exercise the installer's real alias writer and shell parsing layers."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name == "nt", reason="POSIX shell alias; exercised on Linux and macOS")
@pytest.mark.parametrize("shell", ["bash", "zsh"])
@pytest.mark.parametrize("directory", ["repo with spaces", "owner's $project `literal`"])
def test_alias_runs_literal_path_and_refreshes_legacy_alias(tmp_path, shell, directory):
    executable = shutil.which(shell)
    if executable is None:
        pytest.skip(f"{shell} not installed")
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    body = text.split("setup_shell_alias() {", 1)[1].split("\n}\n", 1)[0]
    target = tmp_path / directory / "espansr"
    target.parent.mkdir()
    target.write_text('#!/bin/sh\nprintf "%s\\n" "$@"\n', encoding="utf-8")
    target.chmod(0o755)
    rc = tmp_path / (".zshrc" if shell == "zsh" else ".bashrc")
    unrelated = b"# keep this configuration\nexport KEEP=unchanged\n"
    # The old installer incorrectly skipped aliases when any line mentioned
    # espansr (for example completions), or left a stale installation target.
    rc.write_bytes(unrelated + b"# espansr completions\nalias espansr='/old/espansr'\n")
    writer = tmp_path / "write-alias.sh"
    writer.write_text(
        "info() { :; }\nok() { :; }\nsetup_shell_alias() {" + body + "\n}\nsetup_shell_alias\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "SHELL": executable,
        "VENV_CMD": str(target),
        "VENV_PYTHON": sys.executable,
        "PYTHONPATH": str(ROOT),
    }
    subprocess.run(["bash", str(writer)], env=env, check=True, capture_output=True, timeout=20)
    updated = rc.read_bytes()
    assert updated.startswith(unrelated)
    assert b"/old/espansr" not in updated
    subprocess.run(["bash", str(writer)], env=env, check=True, capture_output=True, timeout=20)
    assert rc.read_bytes() == updated
    script = 'source "$1"; eval \'espansr --version "argument with spaces"\''
    if shell == "bash":
        script = "shopt -s expand_aliases; " + script
    result = subprocess.run(
        [executable, "-c", script, "alias-test", str(rc)],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    assert result.stdout == "--version\nargument with spaces\n"
