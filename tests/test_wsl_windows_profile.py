"""On WSL, Windows-side paths come from the current user's exact profile folder.

Every Windows-side Espanso candidate is also a cleanup target, so a folder that
merely looks like the user's must never be used. The stand-ins below behave as
cmd.exe and wslpath did on a WSL2 host:

- ``cmd.exe /u`` writes UTF-16LE; without ``/u`` it writes the console's OEM
  code page (cp437 there, where é is byte 0x82).
- ``set NAME`` prints ``NAME=value`` lines for names starting with NAME, or
  nothing. ``echo %NAME%`` expands before cmd.exe parses the line, so an
  ``&`` in the value starts another command.
- ``wslpath -u X:\\rest`` prints the drive's mount path, exits 1 for a drive
  that is not mounted or a network path, and echoes a relative argument.

They are POSIX scripts, so these tests do not run on Windows itself.
"""

import json
import shlex
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX stand-ins for WSL tools")

_CMD = r"""
import json, re, sys

variables = json.loads(sys.argv[1])
args = sys.argv[2:]
unicode = args[:1] == ["/u"]
if unicode:
    args = args[1:]
verb, _, operand = args[1].partition(" ")  # args[0] is /c
if verb == "set":
    lines = [f"{k}={v}" for k, v in variables.items() if k.upper().startswith(operand.upper())]
else:
    expanded = re.sub(r"%(\w+)%", lambda m: variables.get(m.group(1), m.group(0)), operand)
    lines = [expanded.split("&")[0]]
text = "".join(f"{line}\r\n" for line in lines)
sys.stdout.buffer.write(text.encode("utf-16-le" if unicode else "cp437", errors="replace"))
sys.exit(0 if lines else 1)
"""

_WSLPATH = r"""
import sys

root, mounted, flag, path = sys.argv[1:]
assert flag == "-u"
drive, colon, rest = path.partition(":")
local = bool(colon) and len(drive) == 1
if path.startswith("\\\\") or (local and drive.lower() not in mounted):
    sys.exit(f"wslpath: {path}: No such file or directory")
if local:
    path = f"{root}/{drive.lower()}" + rest.replace("\\", "/")
sys.stdout.buffer.write(path.encode("utf-8") + b"\n")
"""


def _tool(directory: Path, name: str, source: str, *args: str) -> str:
    """Write an executable stand-in that runs ``source`` with this interpreter."""
    program = directory / f"{name}.py"
    program.write_text(source, encoding="utf-8")
    command = " ".join(shlex.quote(str(part)) for part in (sys.executable, program, *args))
    wrapper = directory / name
    wrapper.write_text(f'#!/bin/sh\nexec {command} "$@"\n', encoding="utf-8")
    wrapper.chmod(0o755)
    return str(wrapper)


@pytest.fixture
def windows(tmp_path, monkeypatch):
    """Return ``setup(variables, folders, mounted="c", cmd=True)`` for a fake host.

    ``folders`` are created under the fake drives (``c/Users/Bob``), each with an
    Espanso match directory holding an espansr-managed file. The returned
    namespace has the fake mount ``root`` and the Linux ``home``.
    """
    root = tmp_path / "mnt"
    home = tmp_path / "home"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    home.mkdir(exist_ok=True)  # on macOS the conftest already made it, as HOME
    monkeypatch.setattr("espansr.core.platform.get_platform", lambda: "wsl2")
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    # The standard cmd.exe location must never reach a real Windows host.
    monkeypatch.setattr("espansr.core.platform._WSL_CMD_EXE", str(tmp_path / "no-cmd.exe"))

    def setup(variables, folders, mounted="c", cmd=True):
        for folder in folders:
            match = root / folder / "AppData" / "Roaming" / "espanso" / "match"
            match.mkdir(parents=True)
            (match / "espansr.yml").write_text("matches: []\n", encoding="utf-8")
        tools = {
            "wslpath": _tool(bin_dir, "wslpath", _WSLPATH, str(root), mounted),
        }
        if cmd:
            tools["cmd.exe"] = _tool(bin_dir, "cmd.exe", _CMD, json.dumps(variables))
        monkeypatch.setattr("espansr.core.platform.shutil.which", tools.get)
        from espansr.core.platform import get_platform_config

        get_platform_config.cache_clear()

    setup.root = root
    setup.home = home
    return setup


def _windows_side(paths, home):
    return [path for path in paths if not path.is_relative_to(home)]


def test_a_non_ascii_user_with_a_suffixed_profile_gets_exactly_that_profile(windows):
    """José signs in to a domain, so Windows named his profile José.CORP; Bob shares the PC."""
    windows(
        {"USERNAME": "José", "USERPROFILE": "C:\\Users\\José.CORP"},
        ["c/Users/José.CORP", "c/Users/Bob"],
    )
    from espansr.integrations.espanso import (
        _get_candidate_paths,
        clean_stale_espanso_files,
        get_espanso_config_dir,
    )
    from espansr.integrations.orchestratr import _wsl2_orchestratr_base

    profile = windows.root / "c" / "Users" / "José.CORP"
    assert _windows_side(_get_candidate_paths(), windows.home) == [
        profile / "AppData" / "Roaming" / "espanso",
        profile / ".config" / "espanso",
        profile / ".espanso",
    ]
    assert get_espanso_config_dir() == profile / "AppData" / "Roaming" / "espanso"
    assert _wsl2_orchestratr_base() == profile / "AppData" / "Roaming" / "orchestratr"

    clean_stale_espanso_files()
    bob = windows.root / "c" / "Users" / "Bob" / "AppData" / "Roaming" / "espanso" / "match"
    assert (bob / "espansr.yml").read_text(encoding="utf-8") == "matches: []\n"


@pytest.mark.parametrize(
    ("variables", "folders", "mounted", "profile"),
    [
        # A renamed account keeps its folder; robert is someone else.
        pytest.param(
            {"USERNAME": "robert", "USERPROFILE": "C:\\Users\\bob"},
            ["c/Users/bob", "c/Users/robert"],
            "c",
            "c/Users/bob",
            id="renamed-account",
        ),
        # The profile lives on D:; C:\Users\jdoe belongs to an old account.
        pytest.param(
            {"USERNAME": "jdoe", "USERPROFILE": "D:\\Users\\jdoe"},
            ["c/Users/jdoe", "d/Users/jdoe"],
            "cd",
            "d/Users/jdoe",
            id="profile-on-another-drive",
        ),
        # echo %USERPROFILE% would print C:\Users\R, someone else's folder.
        pytest.param(
            {"USERNAME": "R&D", "USERPROFILE": "C:\\Users\\R&D"},
            ["c/Users/R&D", "c/Users/R"],
            "c",
            "c/Users/R&D",
            id="ampersand-in-name",
        ),
    ],
)
def test_a_folder_named_after_the_user_is_not_assumed_to_be_theirs(
    windows, variables, folders, mounted, profile
):
    windows(variables, folders, mounted)
    from espansr.integrations.espanso import _get_candidate_paths

    windows_side = _windows_side(_get_candidate_paths(), windows.home)
    assert windows_side[:1] == [windows.root / profile / "AppData" / "Roaming" / "espanso"]
    assert all(path.is_relative_to(windows.root / profile) for path in windows_side)


@pytest.mark.parametrize(
    ("variables", "folders", "mounted", "cmd"),
    [
        pytest.param({"USERNAME": "Alice"}, ["c/Users/Alice"], "c", True, id="userprofile-unset"),
        pytest.param(
            {"USERNAME": "jdoe", "USERPROFILE": "E:\\Users\\jdoe"},
            ["c/Users/jdoe"],
            "c",
            True,
            id="drive-not-mounted",
        ),
        pytest.param(
            {"USERNAME": "jdoe", "USERPROFILE": "\\\\server\\profiles\\jdoe"},
            ["c/Users/jdoe"],
            "c",
            True,
            id="network-profile",
        ),
        # The only profile folder is still not assumed to be the user's.
        pytest.param({}, ["c/Users/Alice"], "c", False, id="no-cmd-one-profile-folder"),
    ],
)
def test_no_windows_folder_is_used_when_the_profile_cannot_be_established(
    windows, variables, folders, mounted, cmd
):
    windows(variables, folders, mounted, cmd)
    from espansr.integrations.espanso import _get_candidate_paths
    from espansr.integrations.orchestratr import _wsl2_orchestratr_base

    assert _windows_side(_get_candidate_paths(), windows.home) == []
    assert _wsl2_orchestratr_base() is None


def test_the_windows_user_name_arrives_exactly(windows):
    windows({"USERNAME": "José", "USERNAMEX": "other"}, [])
    from espansr.core.platform import get_windows_username

    assert get_windows_username() == "José"


# ── A custom automount root (wsl.conf root = /windows/) ─────────────────────
# The stand-in mounts drives under tmp, not /mnt, exactly as such a root does.


def _launch(match_dir: Path, name: str) -> dict:
    """The shell params of the one trigger in a generated match file."""
    data = yaml.safe_load((match_dir / name).read_text(encoding="utf-8"))
    return data["matches"][0]["vars"][0]["params"]


def test_a_profile_under_a_custom_mount_root_gets_windows_launchers(windows):
    windows(
        {"USERNAME": "Alice", "USERPROFILE": "C:\\Users\\Alice"},
        ["c/Users/Alice", "c/Users/Bob"],
    )
    from espansr.integrations.espanso import (
        generate_launcher_file,
        generate_sync_file,
        get_match_dir,
    )

    match_dir = windows.root / "c" / "Users" / "Alice" / "AppData" / "Roaming" / "espanso" / "match"
    assert get_match_dir() == match_dir
    assert generate_launcher_file() and generate_sync_file()

    for name in ("espansr-launcher.yml", "espansr-sync.yml"):
        params = _launch(match_dir, name)
        assert params["shell"] == "powershell", name
        assert "wsl.exe" in params["cmd"] and "nohup" not in params["cmd"], name
    bob = windows.root / "c" / "Users" / "Bob" / "AppData" / "Roaming" / "espanso" / "match"
    assert sorted(path.name for path in bob.iterdir()) == ["espansr.yml"]


def test_without_an_established_profile_a_linux_config_keeps_linux_launchers(windows):
    windows({"USERNAME": "Alice"}, ["c/Users/Alice"])
    linux = windows.home / ".config" / "espanso" / "match"
    linux.mkdir(parents=True)
    from espansr.integrations.espanso import generate_launcher_file, get_match_dir

    assert get_match_dir() == linux
    assert generate_launcher_file()

    params = _launch(linux, "espansr-launcher.yml")
    assert "shell" not in params and params["cmd"].startswith("nohup ")
    alice = windows.root / "c" / "Users" / "Alice" / "AppData" / "Roaming" / "espanso" / "match"
    assert sorted(path.name for path in alice.iterdir()) == ["espansr.yml"]


def test_a_saved_linux_config_path_moves_to_the_profile_under_a_custom_mount_root(windows):
    windows({"USERNAME": "Alice", "USERPROFILE": "C:\\Users\\Alice"}, ["c/Users/Alice"])
    linux = windows.home / ".config" / "espanso"
    (linux / "match").mkdir(parents=True)
    from espansr.core.config import get_config, save_config
    from espansr.integrations.espanso import get_espanso_config_dir

    config = get_config()
    config.espanso.config_path = str(linux)
    save_config(config)

    profile = windows.root / "c" / "Users" / "Alice"
    assert get_espanso_config_dir() == profile / "AppData" / "Roaming" / "espanso"
