"""Native-schema canaries for local expansion counts and identity changes."""

import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace

import pytest
import yaml

from espansr.core.command_catalog import CommandCatalogEntry
from espansr.core.usage import command_key, enable_native_stats, refresh_usage


def entry(identity="one", trigger=":one"):
    return CommandCatalogEntry(trigger, identity, "", "", "template", capability_id=identity)


@pytest.fixture
def native(tmp_path):
    root = tmp_path / "Espanso data with spaces"
    (root / "config").mkdir(parents=True)
    (root / "config" / "default.yml").write_text("stats:\n  enabled: true\n", encoding="utf-8")
    db = root / "stats.db"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.executescript(
            "CREATE TABLE triggers (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);"
            "CREATE TABLE expansions (id INTEGER PRIMARY KEY AUTOINCREMENT, trigger_id INTEGER, "
            "timestamp TEXT DEFAULT (datetime('now')));"
        )
    return root, tmp_path / "local-only" / "usage.json"


def expand(root, trigger, count=1):
    with closing(sqlite3.connect(root / "stats.db")) as conn, conn:
        conn.execute("INSERT OR IGNORE INTO triggers(name) VALUES (?)", (trigger,))
        trigger_id = conn.execute("SELECT id FROM triggers WHERE name=?", (trigger,)).fetchone()[0]
        conn.executemany("INSERT INTO expansions(trigger_id) VALUES (?)", [(trigger_id,)] * count)


def read(native, entries):
    root, path = native
    return refresh_usage(entries, config_dir=root, usage_path=path, version="espanso 2.4.1")


def test_all_native_history_imports_once_including_more_than_top_ten(native):
    root, path = native
    entries = [entry(str(i), f":{i}") for i in range(20)]
    for i in range(20):
        expand(root, f":{i}", i)
    first = read(native, entries)
    assert first.available
    assert first.counts == {command_key(e): i for i, e in enumerate(entries)}
    snapshot = path.read_bytes()
    assert read(native, entries) == first
    assert path.read_bytes() == snapshot
    expand(root, ":0", 3)
    assert read(native, entries).counts[command_key(entries[0])] == 3
    with closing(sqlite3.connect(root / "stats.db")) as conn, conn:
        assert conn.execute("SELECT COUNT(*) FROM expansions").fetchone()[0] == sum(range(20)) + 3


def test_trigger_rename_combines_lifetime_and_retains_old_alias(native):
    root, path = native
    original = entry()
    expand(root, original.trigger, 4)
    assert read(native, [original]).counts[command_key(original)] == 4
    renamed = replace(original, trigger=":renamed", name="New display name")
    read(native, [renamed])
    expand(root, ":renamed", 3)
    expand(root, ":one", 2)
    assert read(native, [renamed]).counts[command_key(original)] == 9
    assert json.loads(path.read_text())["commands"][command_key(original)]["triggers"] == [
        ":one",
        ":renamed",
    ]


def test_reused_trigger_does_not_give_new_command_old_history(native):
    root, _ = native
    original = entry()
    expand(root, ":one", 4)
    read(native, [original])
    expand(root, ":one", 2)
    renamed = replace(original, trigger=":new")
    new_command = entry("two", ":one")
    switched = read(native, [renamed, new_command])
    assert switched.counts[command_key(original)] == 6
    assert switched.counts[command_key(new_command)] == 0
    expand(root, ":one")
    expand(root, ":new", 3)
    result = read(native, [renamed, new_command])
    assert result.counts[command_key(original)] == 9
    assert result.counts[command_key(new_command)] == 1


def test_native_clear_keeps_checkpointed_totals_and_adds_new_expansions(native):
    root, _ = native
    command = entry()
    expand(root, ":one", 4)
    read(native, [command])
    with closing(sqlite3.connect(root / "stats.db")) as conn, conn:
        conn.execute("DELETE FROM expansions")
    assert read(native, [command]).counts[command_key(command)] == 4
    expand(root, ":one", 2)
    assert read(native, [command]).counts[command_key(command)] == 6


def test_readers_across_threads_cannot_double_count(native):
    root, _ = native
    expand(root, ":one", 15)
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: read(native, [entry()]), range(12)))
    assert all(result.available for result in results)
    assert {result.counts[command_key(entry())] for result in results} == {15}
    assert read(native, [entry()]).counts[command_key(entry())] == 15


def test_separate_processes_share_one_atomic_checkpoint(native):
    root, path = native
    expand(root, ":one", 18)
    code = (
        "import json,sys; from pathlib import Path; "
        "from espansr.core.command_catalog import CommandCatalogEntry; "
        "from espansr.core.usage import refresh_usage; "
        "entry=CommandCatalogEntry(':one','One','','','template',capability_id='one'); "
        "result=refresh_usage([entry],config_dir=Path(sys.argv[1]),"
        "usage_path=Path(sys.argv[2]),version='espanso 2.4.1'); "
        "assert result.available; print(json.dumps(result.counts))"
    )
    processes = [
        subprocess.Popen(
            [sys.executable, "-c", code, str(root), str(path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(4)
    ]
    for process in processes:
        output, errors = process.communicate(timeout=20)
        assert process.returncode == 0, errors
        assert json.loads(output) == {"template:one": 18}
    assert read(native, [entry()]).counts["template:one"] == 18


def test_replaced_native_database_keeps_lifetime_count(native):
    root, _ = native
    expand(root, ":one", 4)
    read(native, [entry()])
    (root / "stats.db").rename(root / "old-stats.db")
    with closing(sqlite3.connect(root / "stats.db")) as conn, conn:
        conn.executescript(
            "CREATE TABLE triggers (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);"
            "CREATE TABLE expansions (id INTEGER PRIMARY KEY AUTOINCREMENT, trigger_id INTEGER);"
        )
    expand(root, ":one", 2)
    assert read(native, [entry()]).counts["template:one"] == 6


@pytest.mark.parametrize("version", ["espanso 2.3.0", "espanso 2.2.2", "", "not a version"])
def test_older_or_unknown_runtime_is_unavailable_without_writes(native, version):
    root, path = native
    before = (root / "config" / "default.yml").read_bytes()
    assert not refresh_usage([entry()], config_dir=root, usage_path=path, version=version).available
    assert not enable_native_stats(root, version=version)
    assert not path.exists()
    assert (root / "config" / "default.yml").read_bytes() == before


def test_corrupt_local_json_is_preserved_and_does_not_break_prompt_use(native):
    _, path = native
    path.parent.mkdir()
    path.write_bytes(b"{broken data")
    assert not read(native, [entry()]).available
    assert path.read_bytes() == b"{broken data"


def test_missing_database_reports_zero_without_creating_native_database(native):
    root, _ = native
    (root / "stats.db").unlink()
    assert read(native, [entry()]).counts == {command_key(entry()): 0}
    assert not (root / "stats.db").exists()


@pytest.mark.parametrize(
    "text",
    [
        "# Keep this comment\ntoggle_key: OFF\n",
        "# Keep this comment\nstats:\n  enabled: false # retain comment\nbackend: Clipboard\n",
        "# Keep this comment\nstats: {enabled: false, extra: 7}\n",
        "# Keep this comment\nstats:\n  extra: 7\nbackend: Clipboard\n",
        "# Keep this comment\nstats: {}\n",
        "# Keep this comment\nstats: null\n",
    ],
)
def test_enable_stats_preserves_comments_other_values_and_is_idempotent(tmp_path, text):
    path = tmp_path / "config" / "default.yml"
    path.parent.mkdir()
    path.write_bytes(text.replace("\n", "\r\n").encode())
    before = path.read_bytes()
    assert enable_native_stats(tmp_path, version="espanso 2.4.1")
    after = path.read_bytes()
    assert after.startswith(b"# Keep this comment\r\n")
    assert b"\n" not in after.replace(b"\r\n", b"")
    assert yaml.safe_load(after)["stats"]["enabled"] is True
    for key, value in yaml.safe_load(before).items():
        if key != "stats":
            assert yaml.safe_load(after)[key] == value
    if "retain comment" in text:
        assert b"# retain comment" in after
    assert path.with_name("default.yml.espansr-orig").read_bytes() == before
    assert not enable_native_stats(tmp_path, version="espanso 2.4.1")
    assert path.read_bytes() == after


def test_bad_native_schema_is_unavailable_without_erasing_local_totals(native):
    root, path = native
    expand(root, ":one", 2)
    read(native, [entry()])
    before = path.read_bytes()
    with closing(sqlite3.connect(root / "stats.db")) as conn, conn:
        conn.execute("DROP TABLE expansions")
    assert not read(native, [entry()]).available
    assert path.read_bytes() == before
