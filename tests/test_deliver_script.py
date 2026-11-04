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

    def __init__(self, live_dir: Path, overrides=None, status=None, matches=None):
        self.calls: list[list[str]] = []
        self.overrides = overrides or {}
        self.live_dir = live_dir
        template = json.loads((ROOT / TEMPLATE).read_text(encoding="utf-8"))
        self.matches = {template["trigger"]: template["content"]} if matches is None else matches
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
            state = {"templates_dir": str(self.live_dir), "matches": self.matches}
            return 0, json.dumps(state), ""
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
    assert f"installed copies and Espanso expansions match main: {TEMPLATE}" in summary
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


def test_verify_detects_a_stale_espanso_expansion(live_dir):
    """The store can update while the match file write fails; the trigger then expands old text."""
    runner = FakeRunner(live_dir, matches={":one-shot": "old text"})
    assert _delivery(runner).deliver() == deliver.EXIT_VERIFY


def test_commit_message_and_pr_body_reach_git_and_gh_as_utf8(live_dir, monkeypatch):
    """Windows Python writes text in the locale code page (often cp1252) unless told otherwise."""
    real = deliver.tempfile.NamedTemporaryFile

    def locale_default(mode="w+b", *args, encoding=None, **kwargs):
        if "b" not in mode and encoding is None:
            encoding = "cp1252"
        return real(mode, *args, encoding=encoding, **kwargs)

    monkeypatch.setattr(deliver.tempfile, "NamedTemporaryFile", locale_default)
    runner, read = FakeRunner(live_dir), {}

    def reading(argv, cwd=None, **kwargs):
        for flag in ("-F", "--body-file"):
            if flag in argv:  # git commit -F and gh pr create --body-file read the bytes
                read[argv[1]] = Path(argv[argv.index(flag) + 1]).read_bytes()
        return runner(argv, cwd=cwd, **kwargs)

    message = "feat: add a thing — café\n\nWhy it matters.\n"
    body = "Why it matters.\n\n\U0001f916 Generated with [Claude Code](https://claude.com/claude-code)\n"
    assert _delivery(reading, message=message, body=body).deliver() == 0
    assert read["commit"].decode("utf-8").replace("\r\n", "\n") == message
    assert read["pr"].decode("utf-8").replace("\r\n", "\n") == body


# ── Catching up with origin/main never stashes other work (real Git) ────────

FOREIGN = ".codex/config.toml"  # another tool's edit in the same checkout


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture()
def checkout(tmp_path, monkeypatch):
    """A checkout of origin/main with a foreign tracked file, and a second clone to move origin."""
    for key in ("GIT_AUTHOR_NAME", "GIT_COMMITTER_NAME"):
        monkeypatch.setenv(key, "espansr test")
    for key in ("GIT_AUTHOR_EMAIL", "GIT_COMMITTER_EMAIL"):
        monkeypatch.setenv(key, "test@example.invalid")
    bare, repo, other = tmp_path / "origin.git", tmp_path / "repo", tmp_path / "other"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(bare))
    _git(tmp_path, "init", "-q", "-b", "main", str(repo))
    (repo / "templates").mkdir()
    (repo / "templates" / "shared.json").write_text(
        json.dumps({"name": "Shared", "content": "v1", "trigger": ":shared"}), encoding="utf-8"
    )
    (repo / ".codex").mkdir()
    (repo / FOREIGN).write_text('model = "a"\n', encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-q", "-u", "origin", "main")
    _git(tmp_path, "clone", "-q", str(bare), str(other))
    (repo / "templates" / "shared.json").write_text(
        json.dumps({"name": "Shared", "content": "v2", "trigger": ":shared"}), encoding="utf-8"
    )
    monkeypatch.setattr(deliver, "ROOT", repo)
    return repo, other


def _move_origin(other: Path) -> None:
    (other / "README.md").write_text("upstream moved on\n", encoding="utf-8")
    _git(other, "add", "-A")
    _git(other, "commit", "-q", "-m", "upstream")
    _git(other, "push", "-q", "origin", "main")


def _real_delivery(repo: Path):
    def in_repo(argv, cwd=None, **kwargs):
        return deliver.run(argv, cwd=repo, **kwargs)

    return deliver.Delivery(
        branch="agent/feat-shared",
        message="feat: shared v2\n",
        body=None,
        paths=["templates/shared.json"],
        runner=in_repo,
    )


def _dirty_foreign(repo: Path, shape: str) -> None:
    """unstaged: the working tree differs; staged: index and working tree do;
    staged-back: other content is staged, then the working tree is put back to HEAD."""
    path = repo / FOREIGN
    original = path.read_bytes()
    path.write_text('model = "b"  # theirs\n', encoding="utf-8")
    if shape != "unstaged":
        _git(repo, "add", FOREIGN)
    if shape == "staged-back":
        path.write_bytes(original)


def _foreign_state(repo: Path) -> tuple[str, bytes]:
    """The foreign file's index entry (mode, blob, stage) and working-tree bytes."""
    return _git(repo, "ls-files", "-s", "--", FOREIGN), (repo / FOREIGN).read_bytes()


def _stashing(commands: list[str]) -> list[str]:
    return [c for c in commands if " rebase " in f" {c} " or " stash" in c]


@pytest.mark.parametrize("shape", ["unstaged", "staged", "staged-back"])
def test_catching_up_refuses_instead_of_stashing_other_uncommitted_work(checkout, shape):
    repo, other = checkout
    _move_origin(other)
    _dirty_foreign(repo, shape)
    before = _git(repo, "rev-parse", "HEAD"), _foreign_state(repo)
    delivery = _real_delivery(repo)

    with pytest.raises(deliver.DeliveryError, match=r"behind origin/main.*\.codex/config\.toml"):
        delivery.preflight()

    assert _stashing(delivery.commands) == []
    assert (_git(repo, "rev-parse", "HEAD"), _foreign_state(repo)) == before
    assert _git(repo, "branch", "--show-current") == "main"
    assert _git(repo, "stash", "list") == ""


@pytest.mark.parametrize("shape", ["unstaged", "staged-back"])
def test_other_uncommitted_work_stays_as_it_is_when_already_up_to_date(checkout, shape):
    repo, _ = checkout
    _dirty_foreign(repo, shape)
    before = _foreign_state(repo)

    _real_delivery(repo).preflight()

    assert _git(repo, "show", "--name-only", "--format=", "HEAD") == "templates/shared.json"
    assert _foreign_state(repo) == before


def test_a_change_made_while_catching_up_is_never_stashed_even_with_autostash_set(checkout):
    """Another session stages a change between the check and the rebase."""
    repo, other = checkout
    _move_origin(other)
    _git(repo, "config", "rebase.autoStash", "true")  # what the rebase would inherit
    delivery = _real_delivery(repo)
    run, seen = delivery.runner, []

    def meanwhile(argv, cwd=None, **kwargs):
        if "rebase" in argv and "--abort" not in argv:
            _dirty_foreign(repo, "staged-back")
            seen.append(_foreign_state(repo))
        return run(argv, cwd=cwd, **kwargs)

    delivery.runner = meanwhile
    with pytest.raises(deliver.DeliveryError, match="nothing was stashed"):
        delivery.preflight()

    assert len(seen) == 1 and _foreign_state(repo) == seen[0]
    assert _git(repo, "stash", "list") == ""


def test_a_delivery_with_nothing_else_uncommitted_still_catches_up(checkout):
    repo, other = checkout
    _move_origin(other)

    _real_delivery(repo).preflight()

    assert _git(repo, "merge-base", "--is-ancestor", "origin/main", "HEAD") == ""
    assert _git(repo, "log", "-1", "--format=%s") == "feat: shared v2"
    assert (repo / "README.md").is_file()
