"""Execute the real installer decision paths without changing the workstation."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(os.name != "nt", reason="Native PowerShell installer; tested on Windows CI")
@pytest.mark.parametrize(
    "scenario,events,version",
    [
        ("missing", ["download", "install"], "2.4.1"),
        ("older", ["download", "stop", "install"], "2.4.1"),
        ("current", [], "2.4.1"),
        ("newer", [], "2.5.0"),
        ("flag-optout", [], "2.3.0"),
        ("env-optout", [], "2.3.0"),
        ("unknown", [], ""),
        ("custom", [], "2.3.0"),
        ("network-failure", ["download"], "2.3.0"),
        ("bad-hash", ["download"], "2.3.0"),
        ("installer-failure", ["download", "stop", "install"], "2.3.0"),
        ("stale-path", ["download", "stop", "install"], "2.3.0"),
    ],
)
def test_windows_runtime_upgrade_decisions(tmp_path, scenario, events, version):
    result = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "tests/fixtures/espanso_runtime_scenarios.ps1"),
            "-Helper",
            str(ROOT / "espansr/resources/espanso_runtime.ps1"),
            "-Root",
            str(tmp_path),
            "-Scenario",
            scenario,
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=20,
    )
    data = json.loads(result.stdout.splitlines()[-1])
    assert data["events"] == events
    assert data["version"] == version
    assert data["remaining"] == 0
    if scenario in {"network-failure", "bad-hash", "installer-failure", "stale-path"}:
        assert "[WARN]" in result.stdout
        assert "Verified Espanso" not in result.stdout


@pytest.mark.skipif(os.name == "nt", reason="POSIX installer; tested on Linux and macOS CI")
@pytest.mark.parametrize(
    "platform,owner,version,optout,expected,code",
    [
        ("linux", "espanso", "2.3.0", False, ["x11", "start"], 0),
        ("linux", "espanso-wayland", "2.3.0", False, ["wayland", "start"], 0),
        ("linux", "appimage", "2.3.0", False, ["appimage", "start"], 0),
        ("macos", "brew", "2.3.0", False, ["brew-upgrade", "start"], 0),
        ("linux", "custom", "2.3.0", False, [], 1),
        ("linux", "espanso", "2.4.1", False, [], 0),
        ("linux", "espanso", "2.5.0", False, [], 0),
        ("linux", "espanso", "2.3.0", True, [], 0),
        ("wsl2", "custom", "2.3.0", False, [], 0),
    ],
)
def test_unix_runtime_upgrade_decisions(tmp_path, platform, owner, version, optout, expected, code):
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    body = text.split("ESPANSO_INSTALLED_THIS_RUN=0", 1)[1].split("\ninstall_espanso ||", 1)[0]
    bin_dir = tmp_path / (".local/bin" if owner == "appimage" else "system/bin")
    bin_dir.mkdir(parents=True)
    version_file = tmp_path / "version"
    version_file.write_text(version, encoding="utf-8")
    executable = bin_dir / "espanso"
    executable.write_text(
        '#!/bin/sh\ncat "$TEST_VERSION_FILE"\n[ "$(cat "$TEST_VERSION_FILE")" != "2.3.0" ]\n',
        encoding="utf-8",
    )
    executable.chmod(0o755)
    log = tmp_path / "calls"
    log.touch()
    script = tmp_path / "runtime.sh"
    script.write_text(
        "set -eu\ninfo() { :; }\nok() { :; }\nwarn() { :; }\n" + body + "\n" + r"""
uname() { echo x86_64; }
dpkg-query() { printf '%s: %s\n' "$TEST_OWNER" "$TEST_EXECUTABLE"; }
upgrade() { echo "$1" >> "$TEST_LOG"; echo 2.4.1 > "$TEST_VERSION_FILE"; }
install_espanso_deb() { upgrade "$1"; }
install_espanso_appimage_x11() { upgrade appimage; }
brew() { if [ "$1" = list ]; then return 0; fi; upgrade brew-upgrade; }
start_espanso_service() { echo start >> "$TEST_LOG"; }
install_espanso
""",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "HOME": str(tmp_path),
        "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
        "PLATFORM": platform,
        "PYTHON_BIN": sys.executable,
        "ESPANSO_MIN": "2.4.1",
        "NO_ESPANSO": "1" if optout else "0",
        "TEST_VERSION_FILE": str(version_file),
        "TEST_OWNER": owner,
        "TEST_EXECUTABLE": str(executable),
        "TEST_LOG": str(log),
    }
    result = subprocess.run(
        [shutil.which("bash"), str(script)],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == code, result.stderr
    assert log.read_text().splitlines() == expected
