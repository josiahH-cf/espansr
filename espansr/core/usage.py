"""Local lifetime counts derived from Espanso's native expansion records.

Nothing runs on expansion or copy. Readers sample the native SQLite database
and atomically checkpoint totals outside the template store. Trigger ownership
is remembered by stable command ID so renames retain the command's count.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import time
from contextlib import closing, contextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from espansr.core.atomic import atomic_copy, atomic_write_json


@dataclass(frozen=True)
class UsageSnapshot:
    available: bool = False
    reason: str = "Espanso 2.4+ is required for local usage counts."
    counts: dict[str, int] = field(default_factory=dict)


def command_key(entry) -> str:
    return f"{entry.source}:{entry.capability_id}"


@lru_cache(maxsize=8)
def _version_for(executable: str, wsl: bool) -> str:
    if wsl:
        argv = [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "$statsExe=Join-Path $env:LOCALAPPDATA 'Programs/Espanso/espansod.exe'; "
            "if(Test-Path -LiteralPath $statsExe){ & $statsExe --version } "
            "else { espanso --version }",
        ]
    else:
        argv = [executable, "--version"]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=2,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0,
        )
        return result.stdout if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def native_version() -> str:
    from espansr.core.platform import is_wsl2
    from espansr.integrations.espanso import _find_espanso_executable

    wsl = is_wsl2()
    executable = "powershell.exe" if wsl else _find_espanso_executable()
    return _version_for(executable, wsl) if executable else ""


def _supported(version: str) -> bool:
    match = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", version)
    return bool(match and tuple(map(int, match.groups())) >= (2, 4, 0))


def enable_native_stats(config_dir: Path, *, version: str | None = None) -> bool:
    """Enable supported native statistics, preserving other YAML text and comments.

    Invalid/ambiguous configurations are left alone. This optional enhancement
    must never prevent installing, publishing or copying prompts.
    """
    if not _supported(native_version() if version is None else version):
        return False
    path = config_dir / "config" / "default.yml"
    try:
        from espansr.core.atomic import atomic_write_bytes

        original = path.read_bytes() if path.exists() else b""
        text = original.decode("utf-8")
        newline = "\r\n" if "\r\n" in text else "\n"
        root = yaml.compose(text)
        if root is not None and not isinstance(root, yaml.MappingNode):
            return False
        stats = [v for k, v in root.value if k.value == "stats"] if root else []
        if len(stats) > 1:
            return False
        if not stats:
            updated = text + newline + "# espansr: local expansion counts" + newline
            updated += "stats:" + newline + "  enabled: true" + newline
        else:
            node = stats[0]
            if isinstance(node, yaml.MappingNode):
                enabled = [v for k, v in node.value if k.value == "enabled"]
                if len(enabled) > 1:
                    return False
                if enabled:
                    value = enabled[0]
                    if value.tag.endswith(":bool") and value.value.lower() in ("true", "yes", "on"):
                        return False
                    updated = text[: value.start_mark.index] + "true" + text[value.end_mark.index :]
                elif node.flow_style:
                    index = node.end_mark.index - 1
                    addition = (", " if node.value else "") + "enabled: true"
                    updated = text[:index] + addition + text[index:]
                else:
                    indent = node.value[0][0].start_mark.column if node.value else 2
                    index = node.end_mark.index
                    prefix = "" if text[:index].endswith(("\n", "\r")) else newline
                    updated = text[:index] + prefix + " " * indent + "enabled: true" + newline
                    updated += text[index:]
            elif node.tag.endswith(":null"):
                updated = (
                    text[: node.start_mark.index] + "{enabled: true}" + text[node.end_mark.index :]
                )
            else:
                return False
        data = yaml.safe_load(updated)
        if data["stats"]["enabled"] is not True:
            return False
        if path.exists():
            backup = path.with_name(path.name + ".espansr-orig")
            if not backup.exists():
                atomic_copy(path, backup)
        atomic_write_bytes(path, updated.encode("utf-8"))
        return True
    except (OSError, UnicodeError, yaml.YAMLError, TypeError, KeyError):
        return False


@contextmanager
def _locked(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            def acquire():
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)

            def release():
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)

        else:
            import fcntl

            def acquire():
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)

            def release():
                fcntl.flock(handle, fcntl.LOCK_UN)

        for attempt in range(11):
            try:
                acquire()
                break
            except OSError:
                if attempt == 10:
                    raise
                time.sleep(0.05)
        try:
            yield
        finally:
            release()


def refresh_usage(
    entries,
    *,
    config_dir: Path | None = None,
    usage_path: Path | None = None,
    version: str | None = None,
    reconcile: bool = True,
) -> UsageSnapshot:
    """Read actual expansions and checkpoint counts; errors stay non-fatal.

    Version/path arguments allow bounded tests against the native schema.
    They are never sourced from synchronized templates.
    """
    if not _supported(native_version() if version is None else version):
        return UsageSnapshot()
    from espansr.core.config import get_config_dir
    from espansr.integrations.espanso import get_espanso_config_dir

    config_dir = config_dir if config_dir is not None else get_espanso_config_dir()
    if config_dir is None:
        return UsageSnapshot(reason="Espanso's local configuration could not be found.")
    path = usage_path if usage_path is not None else get_config_dir() / "usage.json"
    try:
        settings = config_dir / "config" / "default.yml"
        config = yaml.safe_load(settings.read_text(encoding="utf-8")) if settings.exists() else {}
        if not isinstance(config, dict) or (config.get("stats") or {}).get("enabled") is not True:
            return UsageSnapshot(reason="Statistics are disabled; run espansr setup to enable.")
        with _locked(path.with_suffix(".lock")):
            bind = reconcile or not path.exists()
            state = (
                json.loads(path.read_text(encoding="utf-8"))
                if path.exists()
                else {
                    "schema_version": 1,
                    "source": {},
                    "commands": {},
                    "owners": {},
                }
            )
            if state.get("schema_version") != 1:
                raise ValueError("Unsupported local usage schema")
            commands = state["commands"]
            owners = state["owners"]
            bindings = {entry.trigger: command_key(entry) for entry in entries if entry.trigger}
            # Register first-seen bindings before importing existing native history.
            if bind:
                for trigger, key in bindings.items():
                    owners.setdefault(trigger, key)
            db = config_dir / "stats.db"
            if db.exists():
                info = db.stat()
                identity = f"{db.resolve()}:{info.st_dev}:{info.st_ino}"
                previous = state["source"]
                cursor = previous.get("cursor", 0) if previous.get("identity") == identity else 0
                with closing(
                    sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True, timeout=0.15)
                ) as conn:
                    conn.execute("BEGIN")
                    newest = conn.execute("SELECT COALESCE(MAX(id), 0) FROM expansions").fetchone()[
                        0
                    ]
                    if newest < cursor:
                        cursor = 0  # Native clear/prune never removes accumulated totals.
                    rows = conn.execute(
                        "SELECT t.name, COUNT(*) FROM expansions e "
                        "JOIN triggers t ON t.id=e.trigger_id WHERE e.id>? AND e.id<=? "
                        "GROUP BY t.name",
                        (cursor, newest),
                    ).fetchall()
                for trigger, increment in rows:
                    key = owners.get(trigger)
                    if key:
                        record = commands.setdefault(key, {"count": 0, "triggers": []})
                        record["count"] += increment
                state["source"] = {"identity": identity, "cursor": newest}
            # Preserve old aliases. A reused trigger moves to its new command
            # only after pending native events have been credited to its old owner.
            if bind:
                owners.update(bindings)
            for entry in entries:
                key = command_key(entry)
                record = commands.setdefault(key, {"count": 0, "triggers": []})
                record["name"] = entry.name
                record["trigger"] = entry.trigger
                if bind and entry.trigger and entry.trigger not in record["triggers"]:
                    record["triggers"].append(entry.trigger)
            if not path.exists() or json.loads(path.read_text(encoding="utf-8")) != state:
                atomic_write_json(path, state)
            return UsageSnapshot(
                True,
                "Actual local Espanso expansions; copying does not count.",
                {key: record["count"] for key, record in commands.items()},
            )
    except (
        OSError,
        sqlite3.Error,
        ValueError,
        TypeError,
        KeyError,
        AttributeError,
        yaml.YAMLError,
    ):
        return UsageSnapshot(reason="Local usage is temporarily unavailable; prompts still work.")
