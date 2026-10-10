"""scripts/deliver.py: the single unattended delivery route.

Every external command goes through an injected runner, so these tests drive
the real orchestration without touching git remotes, GitHub, or Espanso.
"""

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("deliver", ROOT / "scripts" / "deliver.py")
deliver = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(deliver)

TEMPLATE = "templates/one_shot.json"
MESSAGE = "feat: add a thing\n\nWhy it matters.\n\nCo-Authored-By: Someone <x@example.com>\n"
PASSING = json.dumps([{"name": "ci (3.12)", "bucket": "pass"}])


class FakeRunner:
    """Scripted stand-in for subprocess: records argv, answers by substring."""

    def __init__(self, live_dir: Path, overrides=None, status=None):
        self.calls: list[list[str]] = []
        self.overrides = overrides or {}
        self.live_dir = live_dir
        self.pr_created = False
        self.status = status if status is not None else f" M {TEMPLATE}\n M unrelated.txt\n"

    def __call__(self, argv, cwd=None, **kwargs):
        self.calls.append(list(argv))
        key = " ".join(argv)
        for pattern, (rc, out) in self.overrides.items():
            if pattern in key:
                return subprocess.CompletedProcess(argv, rc, stdout=out, stderr="")
        if key.startswith("gh pr create"):
            self.pr_created = True
        return subprocess.CompletedProcess(argv, *self._default(key))

    def _default(self, key):
        if key == "git rev-parse --abbrev-ref HEAD":
            return 0, "main\n", ""
        if key.startswith("git status --porcelain"):
            return 0, self.status, ""
        if key.startswith("git diff --cached --name-only"):
            return 0, f"{TEMPLATE}\n", ""
        if key.startswith("gh pr view"):
            if not self.pr_created:
                return 1, "", "no pull requests found"
            info = {"number": 7, "state": "OPEN", "url": "https://github.com/o/r/pull/7"}
            return 0, json.dumps(info), ""
        if key.startswith("gh pr checks") and "--json" in key:
            return 0, PASSING, ""
        if key.endswith("-m espansr doctor"):
            return 0, "[ok]   Validation: all templates valid\n" + deliver.INDEPENDENT_LINE, ""
        if "get_templates_dir" in key:
            return 0, f"{self.live_dir}\n", ""
        if key.startswith("git rev-parse --short"):
            return 0, "abc1234\n", ""
        return 0, "", ""

    def index(self, fragment: str) -> int:
        for position, argv in enumerate(self.calls):
            if fragment in " ".join(argv):
                return position
        raise AssertionError(f"never ran: {fragment}")

    def ran(self, fragment: str) -> bool:
        return any(fragment in " ".join(argv) for argv in self.calls)


@pytest.fixture()
def live_dir(tmp_path):
    live = tmp_path / "live"
    live.mkdir()
    shutil.copy(ROOT / TEMPLATE, live / Path(TEMPLATE).name)
    return live


def _delivery(runner, **overrides):
    options = {
        "branch": "agent/feat-a-thing",
        "message": MESSAGE,
        "body": None,
        "paths": [TEMPLATE],
        "runner": runner,
        "python": "py",
        "is_windows": True,
        "sleep": lambda _: None,
    }
    options.update(overrides)
    return deliver.Delivery(**options)


def test_delivers_through_every_stage_in_order(live_dir, capsys):
    runner = FakeRunner(live_dir)
    assert _delivery(runner).deliver() == 0

    order = [
        "git fetch --prune origin",
        "git switch -c agent/feat-a-thing",
        f"git add -- {TEMPLATE}",
        "git commit -F",
        "git worktree add --detach",
        "py -m pytest -q",
        "py -m black --check .",
        "git push --force-with-lease -u origin agent/feat-a-thing",
        "gh pr create --base main --head agent/feat-a-thing --title feat: add a thing",
        "gh pr checks 7 --watch --fail-fast",
        "gh pr merge 7 --squash --subject feat: add a thing (#7)",
        "git switch main",
        "git pull --ff-only origin main",
        "py -m espansr refresh",
        "py -m espansr doctor",
    ]
    positions = [runner.index(step) for step in order]
    assert positions == sorted(positions)
    summary = capsys.readouterr().out
    assert "DELIVERY SUMMARY" in summary
    assert f"installed copies match main: {TEMPLATE}" in summary
    assert deliver.INDEPENDENT_LINE in summary


def test_commits_only_the_listed_paths(live_dir):
    runner = FakeRunner(live_dir)
    assert _delivery(runner).deliver() == 0
    added = [argv for argv in runner.calls if argv[:2] == ["git", "add"]]
    assert added == [["git", "add", "--", TEMPLATE]]
    assert not runner.ran("unrelated.txt")


def test_reinstall_is_refresh_never_publish(live_dir):
    runner = FakeRunner(live_dir)
    assert _delivery(runner).deliver() == 0
    assert runner.ran("-m espansr refresh")
    assert not runner.ran("publish")


def test_rejects_a_branch_name_outside_the_convention(live_dir):
    runner = FakeRunner(live_dir)
    assert _delivery(runner, branch="my-branch").deliver() == deliver.EXIT_PREFLIGHT
    assert runner.calls == []


def test_refuses_a_listed_path_without_changes(live_dir):
    runner = FakeRunner(live_dir, status=" M unrelated.txt\n")
    assert _delivery(runner).deliver() == deliver.EXIT_PREFLIGHT
    assert not runner.ran("git commit")


def test_failed_local_check_stops_before_push(live_dir):
    runner = FakeRunner(live_dir, overrides={"-m pytest": (1, "1 failed")})
    assert _delivery(runner).deliver() == deliver.EXIT_CHECKS
    assert not runner.ran("git push")
    assert runner.ran("git worktree remove --force")


def test_failed_ci_stops_before_merge(live_dir):
    failing = json.dumps([{"name": "ci-windows", "bucket": "fail"}])
    runner = FakeRunner(
        live_dir,
        overrides={"--watch": (1, ""), "gh pr checks 7 --json": (0, failing)},
    )
    assert _delivery(runner).deliver() == deliver.EXIT_CI
    assert not runner.ran("gh pr merge")
    assert not runner.ran("espansr refresh")


def test_verify_requires_espanso_running_independently_on_windows(live_dir):
    runner = FakeRunner(live_dir, overrides={"-m espansr doctor": (0, "[ok]   all good\n")})
    assert _delivery(runner).deliver() == deliver.EXIT_VERIFY


def test_verify_detects_an_installed_copy_that_differs_from_main(live_dir):
    (live_dir / Path(TEMPLATE).name).write_text('{"content": "stale"}', encoding="utf-8")
    runner = FakeRunner(live_dir)
    assert _delivery(runner).deliver() == deliver.EXIT_VERIFY


def test_failed_reinstall_stops_with_its_own_exit_code(live_dir):
    runner = FakeRunner(live_dir, overrides={"-m espansr refresh": (1, "")})
    assert _delivery(runner).deliver() == deliver.EXIT_INSTALL
    assert not runner.ran("espansr doctor")
