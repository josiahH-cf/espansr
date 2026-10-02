"""Native CI canary: fresh install, real Git sync/reinstall, publish and copy.

Run on disposable GitHub Linux/macOS/Windows runners. All app data and the
repository are temporary; Espanso installation, services, and typing into
desktop applications are outside this canary. The installed Qt clipboard is
exercised with its offscreen backend. No production remote is contacted.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1]


def run(argv: list[str], *, cwd: Path, env: dict[str, str]) -> str:
    result = subprocess.run(
        argv, cwd=cwd, env=env, capture_output=True, text=True, errors="replace", timeout=300
    )
    if result.returncode:
        raise RuntimeError(f"{argv!r} exited {result.returncode}\n{result.stdout}\n{result.stderr}")
    return result.stdout


def probe(repo: Path) -> dict:
    """Executed by the newly installed interpreter, without pytest mocks."""
    import yaml
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

    import espansr
    from espansr.core.command_catalog import build_command_catalog
    from espansr.core.command_groups import COMMAND_GROUPS, groups_for
    from espansr.core.config import get_config, get_templates_dir
    from espansr.core.install_meta import load_install_meta
    from espansr.core.templates import get_bundled_templates_dir
    from espansr.core.workflows import load_workflow_catalog
    from espansr.integrations.espanso import get_match_dir
    from espansr.ui.commands_popup import CommandsPopupDialog

    assert Path(espansr.__file__).resolve().is_relative_to(repo), "Wrong installation imported"
    assert get_bundled_templates_dir().resolve() == repo / "templates"
    live = get_templates_dir()
    bundled = {
        p.name: json.loads(p.read_text(encoding="utf-8"))
        for p in (repo / "templates").glob("*.json")
    }
    for name, expected in bundled.items():
        assert json.loads((live / name).read_text(encoding="utf-8")) == expected, name
    assert {":clarify-features", ":rec", ":acc", ":litmus", ":unblock"} <= {
        t["trigger"] for t in bundled.values()
    }
    workflows = load_workflow_catalog()
    assert not workflows.errors, workflows.errors
    assert {"session-continuity", "fresh-model-verification"} <= {w.id for w in workflows.workflows}
    entries = build_command_catalog(workflow_catalog=workflows)
    assert len({entry.trigger for entry in entries}) == len(entries)
    assert all(groups_for(entry) for entry in entries)
    assert len(COMMAND_GROUPS) == 9
    match_dir = get_match_dir()
    matches = yaml.safe_load((match_dir / "espansr.yml").read_text(encoding="utf-8"))["matches"]
    by_trigger = {m["trigger"]: m for m in matches}
    assert len(by_trigger) == len(matches)
    for expected in bundled.values():
        match = by_trigger[expected["trigger"]]
        if not expected.get("variables"):
            assert match["replace"] == expected["content"], expected["trigger"]
        else:
            assert match["vars"], expected["trigger"]
    for filename in ("espansr-launcher.yml", "espansr-commands.yml", "espansr-sync.yml"):
        assert (match_dir / filename).is_file(), filename
    meta = load_install_meta()
    assert Path(meta.repo_dir).resolve() == repo
    app = QApplication([])
    dialog = CommandsPopupDialog(entries=entries, workflow_catalog=workflows)
    copied = 0
    for entry in entries:
        if not entry.content:
            continue
        dialog._show_capability_command(entry.capability_id)
        app.processEvents()
        assert dialog._selected_entry.trigger == entry.trigger
        dialog._detail_widget._copy_trigger_btn.click()
        assert app.clipboard().text() == entry.trigger
        dialog._detail_widget._copy_prompt_btn.click()
        assert app.clipboard().text() == entry.content, entry.trigger
        copied += 1
    # A user can navigate the guides and Processes repeatedly and continue
    # copying normally. Nothing is executed by either reference surface.
    for _ in range(2):
        dialog._view_combo.setCurrentText("Processes")
        app.processEvents()
        dialog._view_combo.setCurrentText("Browse")
        app.processEvents()
    dialog._show_capability_command("use_recommendation")
    dialog._detail_widget._copy_prompt_btn.click()
    assert app.clipboard().text() == bundled["use_recommendation.json"]["content"]
    assert app.clipboard().text().endswith(" ")
    assert dialog.windowFlags() & Qt.WindowType.WindowStaysOnTopHint == (
        Qt.WindowType.WindowStaysOnTopHint if get_config().discovery.stay_on_top else 0
    )
    dialog.deleteLater()
    return {
        "bundled_templates": len(bundled),
        "copied_prompts": copied,
        "groups": len(COMMAND_GROUPS),
        "workflows": len(workflows.workflows),
        "config_dir": str(live.parent),
    }


def verify(task: Path) -> None:
    repo = task / "checkout with spaces"
    repo.mkdir()
    for name in ("espansr", "templates"):
        shutil.copytree(SOURCE / name, repo / name, ignore=shutil.ignore_patterns("__pycache__"))
    for name in ("pyproject.toml", "README.md", "LICENSE", "install.sh", "install.ps1"):
        shutil.copy2(SOURCE / name, repo / name)
    (repo / ".gitignore").write_text(".venv/\n*.egg-info/\n__pycache__/\n", encoding="utf-8")
    user_dir = task / "user with spaces"
    user_dir.mkdir()
    env = {
        **os.environ,
        "HOME": str(user_dir),
        "USERPROFILE": str(user_dir),
        "APPDATA": str(task / "appdata"),
        "LOCALAPPDATA": str(task / "localappdata"),
        "XDG_CONFIG_HOME": str(task / "xdg-config"),
        "QT_QPA_PLATFORM": "offscreen",
        "ESPANSR_NO_ESPANSO": "1",
        "ESPANSR_XWAYLAND_APPS": "no",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": str(task / "gitconfig"),
    }
    env.pop("PYTHONPATH", None)
    config_root = (
        task / "appdata" / "espansr"
        if os.name == "nt"
        else (
            user_dir / "Library" / "Application Support" / "espansr"
            if sys.platform == "darwin"
            else task / "xdg-config" / "espansr"
        )
    )
    config_root.mkdir(parents=True)
    espanso_dir = task / "espanso-fixture"
    (espanso_dir / "config").mkdir(parents=True)
    (espanso_dir / "config" / "default.yml").write_text("show_icon: false\n", encoding="utf-8")
    config_file = config_root / "config.json"
    config_file.write_text(
        json.dumps({"espanso": {"config_path": str(espanso_dir)}}), encoding="utf-8"
    )
    remote = task / "remote.git"
    run(["git", "init", "--bare", str(remote)], cwd=task, env=env)
    run(["git", "init", "-b", "main"], cwd=repo, env=env)
    for key, value in (("user.name", "Install Canary"), ("user.email", "canary@example.invalid")):
        run(["git", "config", key, value], cwd=repo, env=env)
    run(["git", "add", "."], cwd=repo, env=env)
    run(["git", "commit", "-m", "canary baseline"], cwd=repo, env=env)
    run(["git", "remote", "add", "origin", str(remote)], cwd=repo, env=env)
    run(["git", "push", "-u", "origin", "main"], cwd=repo, env=env)
    installer = (
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repo / "install.ps1"),
            "-LocalOnly",
        ]
        if os.name == "nt"
        else ["bash", str(repo / "install.sh"), "--no-espanso", "--no-xwayland-apps"]
    )
    run(installer, cwd=repo, env=env)
    python = repo / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    probe_command = [str(python), str(Path(__file__).resolve()), "--probe", str(repo)]
    initial = json.loads(run(probe_command, cwd=task, env=env))
    print(f"Fresh install: {initial['bundled_templates']} templates; copy and discovery passed.")
    live = config_root / "templates"
    custom = {
        "name": "User note",
        "trigger": ":user-canary",
        "content": "Résumé 👋\nKeep this note. ",
    }
    (live / "user-note.json").write_text(json.dumps(custom), encoding="utf-8")
    for name in ("litmus.json", "unblock.json", "clarify_features.json"):
        template = json.loads((live / name).read_text(encoding="utf-8"))
        template["content"] = "Legacy prompt before the update.\n\n"
        (live / name).write_text(json.dumps(template), encoding="utf-8")
    config = json.loads(config_file.read_text(encoding="utf-8"))
    config["discovery"]["stay_on_top"] = False
    config["discovery"]["favorite_triggers"] = [":rec"]
    config_file.write_text(json.dumps(config), encoding="utf-8")
    # Exercise the real pull + dirty stash + rebase + commit + push + reinstall
    # path against a bare local remote, including an incoming remote change.
    peer = task / "peer"
    run(["git", "clone", "-b", "main", str(remote), str(peer)], cwd=task, env=env)
    for key, value in (("user.name", "Install Canary"), ("user.email", "canary@example.invalid")):
        run(["git", "config", key, value], cwd=peer, env=env)
    (peer / "incoming.txt").write_text("incoming update\n", encoding="utf-8")
    run(["git", "add", "incoming.txt"], cwd=peer, env=env)
    run(["git", "commit", "-m", "incoming canary"], cwd=peer, env=env)
    run(["git", "push"], cwd=peer, env=env)
    with (repo / "README.md").open("a", encoding="utf-8") as handle:
        handle.write("\nLocal sync canary.\n")
    command = repo / ".venv" / ("Scripts/espansr.exe" if os.name == "nt" else "bin/espansr")
    run([str(command), "sync"], cwd=repo, env=env)
    assert run(["git", "status", "--porcelain"], cwd=repo, env=env) == ""
    assert run(["git", "rev-parse", "HEAD"], cwd=repo, env=env) == run(
        ["git", "rev-parse", "origin/main"], cwd=repo, env=env
    )
    assert (repo / "incoming.txt").read_text(encoding="utf-8") == "incoming update\n"
    updated = json.loads(run(probe_command, cwd=task, env=env))
    assert json.loads((live / "user-note.json").read_text(encoding="utf-8")) == custom
    assert any((live / "_versions").rglob("*.json")), "Updated starters need backups"
    config = json.loads(config_file.read_text(encoding="utf-8"))
    assert config["discovery"]["stay_on_top"] is False
    assert config["discovery"]["favorite_triggers"] == [":rec"]
    assert updated["copied_prompts"] == initial["copied_prompts"] + 1
    print(
        "Sync/reinstall: pulled and pushed; starters updated; user note and preferences preserved."
    )


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--probe":
        print(json.dumps(probe(Path(sys.argv[2]).resolve())))
        return
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Run this installer canary on disposable GitHub Actions runners only.")
    # install.ps1 intentionally persists its command shim to HKCU. Restore the
    # runner's previous value before the temporary installation is removed.
    registry = None
    original_path = None
    if os.name == "nt":
        import winreg

        registry = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_ALL_ACCESS)
        try:
            original_path = winreg.QueryValueEx(registry, "Path")
        except FileNotFoundError:
            pass
    temporary = tempfile.TemporaryDirectory(prefix="espansr-install-")
    try:
        verify(Path(temporary.name).resolve())
    finally:
        if registry is not None:
            if original_path is None:
                try:
                    winreg.DeleteValue(registry, "Path")
                except FileNotFoundError:
                    pass
            else:
                winreg.SetValueEx(registry, "Path", 0, original_path[1], original_path[0])
            winreg.CloseKey(registry)
        # Windows console launchers can retain a directory handle briefly
        # after the installer exits. Retry cleanup, but never hide a leak.
        for attempt in range(10):
            try:
                temporary.cleanup()
                break
            except PermissionError:
                if os.name != "nt" or attempt == 9:
                    raise
                time.sleep(0.5)
    assert not Path(temporary.name).exists(), "Canary data was not cleaned up"
    print("Temporary installation and local remote removed.")


if __name__ == "__main__":
    main()
