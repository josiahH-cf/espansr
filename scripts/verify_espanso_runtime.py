"""Disposable CI: real Espanso install/upgrade and native counter availability.

Windows and Linux start with the official 2.3.0 package and exercise the real
upgrade scripts. macOS exercises the actual Homebrew install/upgrade route.
Services and desktop typing are skipped; version probing, config enablement,
and counter availability use the real installed runtime. Never run locally.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]
LEGACY_URL = "https://github.com/espanso/espanso/releases/download/v2.3.0/"
LEGACY_ASSETS = {
    "windows": (
        "Espanso-Win-Installer-x86_64.exe",
        "d146ca640d35f175cbef04d04f137b9759cdab08cb1035b277c8bac0f70f13be",
    ),
    "linux": (
        "espanso-debian-x11-amd64.deb",
        "0f73eac09f1069982aaed0041442a28645ac3e0bbd5a0f24b4dfed3187c3c47d",
    ),
}


def run(argv, env, *, script=None):
    result = subprocess.run(
        argv, input=script, env=env, capture_output=True, text=True, errors="replace", timeout=600
    )
    if result.returncode:
        raise RuntimeError(f"{argv!r} failed\n{result.stdout}\n{result.stderr}")
    return result.stdout


def legacy_package(root, platform):
    name, expected = LEGACY_ASSETS[platform]
    package = root / name
    with urllib.request.urlopen(LEGACY_URL + name, timeout=120) as response:
        package.write_bytes(response.read())
    assert hashlib.sha256(package.read_bytes()).hexdigest() == expected
    return package


def verify(root):
    from espansr.core.command_catalog import CommandCatalogEntry
    from espansr.core.usage import enable_native_stats, native_version, refresh_usage

    env = dict(os.environ)
    env.pop("ESPANSR_NO_ESPANSO", None)
    uninstall = None
    try:
        if os.name == "nt":
            env["LOCALAPPDATA"] = str(root / "app data with spaces")
            install_dir = Path(env["LOCALAPPDATA"]) / "Programs" / "Espanso"
            package = legacy_package(root, "windows")
            run(
                [
                    str(package),
                    "/VERYSILENT",
                    "/SUPPRESSMSGBOXES",
                    "/NORESTART",
                    "/SP-",
                    f"/DIR={install_dir}",
                ],
                env,
            )
            uninstall = install_dir / "unins000.exe"
            binary = install_dir / "espansod.exe"
            old = subprocess.run(
                [str(binary), "--version"], env=env, capture_output=True, text=True
            )
            assert old.stdout.strip() == "2.3.0", old.stdout
            helper = SOURCE / "espansr" / "resources" / "espanso_runtime.ps1"
            wrapper = root / "ensure-runtime.ps1"
            wrapper.write_text(
                "param([string]$Helper)\n. $Helper\nEnsure-EspansoRuntime\n", encoding="utf-8"
            )
            output = run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(wrapper),
                    "-Helper",
                    str(helper),
                ],
                env,
            )
            assert "Verified Espanso" in output, output
            version = run([str(binary), "--version"], env).strip()
        else:
            if sys.platform != "darwin":
                package = legacy_package(root, "linux")
                run(
                    ["sudo", "apt-get", "install", "-y", "--no-install-recommends", str(package)],
                    env,
                )
                old = subprocess.run(["espanso", "--version"], capture_output=True, text=True)
                assert old.stdout.strip() == "2.3.0", old.stdout
            # Execute the real functions, overriding only service start on a
            # headless runner. Downloads, checksums, package managers and the
            # minimum-version check are unchanged.
            text = (SOURCE / "install.sh").read_text(encoding="utf-8")
            body = text.split("ESPANSO_INSTALLED_THIS_RUN=0", 1)[1].split(
                "\ninstall_espanso ||", 1
            )[0]
            env.update(
                {
                    "PLATFORM": "macos" if sys.platform == "darwin" else "linux",
                    "NO_ESPANSO": "0",
                    "ESPANSO_MIN": "2.4.1",
                    "PYTHON_BIN": sys.executable,
                    "ESPANSO_RELEASE_URL": "https://github.com/espanso/espanso/releases/download/v2.4.1",
                }
            )
            run(
                ["bash", "-s"],
                env,
                script='set -euo pipefail\ninfo() { echo "$*"; }\n'
                'ok() { echo "$*"; }\nwarn() { echo "$*"; }\n'
                + body
                + "\nstart_espanso_service() { :; }\ninstall_espanso\n",
            )
            version = run(["espanso", "--version"], env).strip()
        match = re.fullmatch(r"(?:espanso\s+)?(\d+\.\d+\.\d+)", version)
        assert match and tuple(map(int, match[1].split("."))) >= (2, 4, 1), version
        # Resolve the same executable as the production usage reader. Only
        # app-data locations are temporary; no fake version is supplied.
        original_local = os.environ.get("LOCALAPPDATA")
        if os.name == "nt":
            os.environ["LOCALAPPDATA"] = env["LOCALAPPDATA"]
        try:
            assert native_version().strip() == version
            config_dir = root / "espanso config"
            (config_dir / "config").mkdir(parents=True)
            settings = config_dir / "config" / "default.yml"
            settings.write_text("# preserve this setting\nshow_icon: false\n", encoding="utf-8")
            assert enable_native_stats(config_dir)
            assert settings.read_text().startswith("# preserve this setting\nshow_icon: false\n")
            entry = CommandCatalogEntry(
                ":native-canary", "Canary", "", "", "template", capability_id="runtime-canary"
            )
            snapshot = refresh_usage([entry], config_dir=config_dir, usage_path=root / "usage.json")
            assert snapshot.available, snapshot.reason
            assert snapshot.counts["template:runtime-canary"] == 0
            print(json.dumps({"runtime": version, "native_counter_available": True}))
        finally:
            if os.name == "nt":
                if original_local is None:
                    os.environ.pop("LOCALAPPDATA", None)
                else:
                    os.environ["LOCALAPPDATA"] = original_local
    finally:
        if uninstall and uninstall.exists():
            run([str(uninstall), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], env)


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Run this runtime canary on disposable GitHub Actions runners only.")
    temporary = tempfile.TemporaryDirectory(prefix="espansr-runtime-")
    try:
        verify(Path(temporary.name).resolve())
    finally:
        for attempt in range(10):
            try:
                temporary.cleanup()
                break
            except PermissionError:
                if os.name != "nt" or attempt == 9:
                    raise
                time.sleep(0.5)
    assert not Path(temporary.name).exists()
    print("Temporary runtime data removed.")


if __name__ == "__main__":
    main()
