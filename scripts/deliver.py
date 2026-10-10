#!/usr/bin/env python
"""Deliver one change unattended: commit, check, PR, CI, merge, reinstall, verify.

This is the project's single delivery route, so every model and client runs
the same steps the same way. Only the listed paths are committed, so edits
from other sessions in the same checkout are never swept in, and the local
checks run in a temporary worktree of exactly the commit being pushed.

Usage::

    python scripts/deliver.py --branch agent/feat-short-name \\
        --message-file msg.txt [--body-file pr.md] --path FILE [--path FILE ...]

Run it from the repository root on ``main`` (the branch is created) or on the
named branch (rerun after a fix). The first line of the message file is the
commit subject and the pull request title; the merge subject adds ``(#N)``.

Exit codes: 0 delivered; 2 preflight; 3 local checks; 4 push or pull request;
5 CI; 6 merge; 7 reinstall; 8 verification.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
BRANCH_PATTERN = re.compile(r"^(agent|user)/(feat|bug|refactor|chore|docs)-[a-z0-9][a-z0-9-]*$")
INDEPENDENT_LINE = "Espanso process: running independently"
# Run with the project's Python: where templates are installed, and what each
# espansr trigger expands to in Espanso's generated match file.
INSTALLED_STATE_SCRIPT = (
    "import json, yaml\n"
    "from espansr.core.config import get_templates_dir\n"
    "from espansr.integrations.espanso import get_match_dir\n"
    "data = yaml.safe_load((get_match_dir() / 'espansr.yml').read_text(encoding='utf-8'))\n"
    "matches = {m.get('trigger'): m.get('replace') for m in (data or {}).get('matches', [])}\n"
    "print(json.dumps({'templates_dir': str(get_templates_dir()), 'matches': matches}))\n"
)

EXIT_PREFLIGHT, EXIT_CHECKS, EXIT_PUBLISH, EXIT_CI, EXIT_MERGE, EXIT_INSTALL, EXIT_VERIFY = (
    2,
    3,
    4,
    5,
    6,
    7,
    8,
)

Runner = Callable[..., subprocess.CompletedProcess]


class DeliveryError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code


def run(argv: Sequence[str], *, cwd: Path = ROOT, **kwargs) -> subprocess.CompletedProcess:
    """Default runner: text output captured unless the caller redirects it."""
    kwargs.setdefault("capture_output", "stdout" not in kwargs)
    kwargs.setdefault("text", True)
    kwargs.setdefault("check", False)
    return subprocess.run(list(argv), cwd=str(cwd), **kwargs)


def project_python() -> str:
    """The repository virtualenv's Python (it carries CI's tool versions)."""
    for candidate in (ROOT / ".venv" / "Scripts" / "python.exe", ROOT / ".venv" / "bin" / "python"):
        if candidate.is_file():
            return str(candidate)
    return sys.executable


class Delivery:
    def __init__(
        self,
        *,
        branch: str,
        message: str,
        body: str | None,
        paths: list[str],
        install: bool = True,
        checks_timeout: float = 45 * 60,
        runner: Runner = run,
        python: str | None = None,
        is_windows: bool = os.name == "nt",
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.branch = branch
        self.message = message.strip() + "\n"
        self.subject = self.message.splitlines()[0].strip()
        self.commit_body = "\n".join(self.message.splitlines()[1:]).strip()
        self.body = (body or self.commit_body or self.subject).strip() + "\n"
        self.paths = [p.replace("\\", "/") for p in paths]
        self.install = install
        self.checks_timeout = checks_timeout
        self.runner = runner
        self.python = python or project_python()
        self.is_windows = is_windows
        self.sleep = sleep
        self.commands: list[str] = []
        self.pr_number: int | None = None
        self.pr_url = ""

    # ── helpers ──────────────────────────────────────────────────────────────

    def _run(self, argv: Sequence[str], *, cwd: Path = ROOT, **kwargs):
        self.commands.append(" ".join(argv))
        print(f"$ {' '.join(argv)}", flush=True)
        return self.runner(list(argv), cwd=cwd, **kwargs)

    def _git(self, *args: str, **kwargs):
        return self._run(["git", *args], **kwargs)

    def _must(self, result, code: int, what: str):
        if result.returncode != 0:
            detail = (getattr(result, "stderr", "") or getattr(result, "stdout", "") or "").strip()
            raise DeliveryError(code, f"{what} failed (exit {result.returncode}): {detail}")
        return result

    # ── stages ───────────────────────────────────────────────────────────────

    def preflight(self) -> None:
        if not BRANCH_PATTERN.match(self.branch):
            raise DeliveryError(
                EXIT_PREFLIGHT,
                f"branch {self.branch!r} must look like agent/<type>-<short-name>, type one of "
                "feat, bug, refactor, chore, docs",
            )
        if not self.paths:
            raise DeliveryError(EXIT_PREFLIGHT, "list at least one --path to commit")
        current = self._must(
            self._git("rev-parse", "--abbrev-ref", "HEAD"), EXIT_PREFLIGHT, "git rev-parse"
        ).stdout.strip()
        if current not in ("main", self.branch):
            raise DeliveryError(
                EXIT_PREFLIGHT, f"run from main or {self.branch}; currently on {current}"
            )
        self._must(self._git("fetch", "--prune", "origin"), EXIT_PREFLIGHT, "git fetch")

        status = self._git("status", "--porcelain", "--untracked-files=all").stdout
        changed = {line[3:].strip().strip('"').split(" -> ")[-1] for line in status.splitlines()}
        committed = set()
        if current == self.branch:
            committed = set(self._git("diff", "--name-only", "origin/main...HEAD").stdout.split())
        missing = [p for p in self.paths if p not in changed and p not in committed]
        if missing:
            raise DeliveryError(EXIT_PREFLIGHT, f"listed paths have no changes: {missing}")

        if current == "main":
            self._must(self._git("switch", "-c", self.branch), EXIT_PREFLIGHT, "git switch")
        self._must(self._git("add", "--", *self.paths), EXIT_PREFLIGHT, "git add")
        staged = self._git("diff", "--cached", "--name-only").stdout.split()
        if staged:
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as handle:
                handle.write(self.message)
            try:
                self._must(self._git("commit", "-F", handle.name), EXIT_PREFLIGHT, "git commit")
            finally:
                os.unlink(handle.name)

        based = self._git("merge-base", "--is-ancestor", "origin/main", "HEAD")
        if based.returncode != 0:
            rebased = self._git("rebase", "--autostash", "origin/main")
            if rebased.returncode != 0:
                self._git("rebase", "--abort")
                raise DeliveryError(
                    EXIT_PREFLIGHT, "rebase onto origin/main conflicted; resolve it and rerun"
                )

    def local_checks(self) -> None:
        worktree = Path(tempfile.mkdtemp(prefix="esp-deliver-"))
        worktree.rmdir()
        self._must(
            self._git("worktree", "add", "--detach", str(worktree), "HEAD"),
            EXIT_CHECKS,
            "git worktree add",
        )
        env = {**os.environ, "PYTHONPATH": str(worktree)}
        try:
            for argv in (
                [self.python, "-m", "pytest", "-q"],
                [self.python, "-m", "ruff", "check", "."],
                [self.python, "-m", "black", "--check", "."],
                [self.python, "scripts/sync_discovery.py", "--check"],
            ):
                result = self._run(argv, cwd=worktree, env=env)
                if result.returncode != 0:
                    tail = "\n".join((result.stdout + result.stderr).splitlines()[-30:])
                    raise DeliveryError(EXIT_CHECKS, f"{' '.join(argv[1:])} failed:\n{tail}")
        finally:
            self._git("worktree", "remove", "--force", str(worktree))

    def publish(self) -> None:
        self._must(
            self._git("push", "--force-with-lease", "-u", "origin", self.branch),
            EXIT_PUBLISH,
            "git push",
        )
        existing = self._run(["gh", "pr", "view", self.branch, "--json", "number,state,url"])
        info = json.loads(existing.stdout) if existing.returncode == 0 else {}
        if info.get("state") != "OPEN":
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
                handle.write(self.body)
            try:
                self._must(
                    self._run(
                        [
                            "gh",
                            "pr",
                            "create",
                            "--base",
                            "main",
                            "--head",
                            self.branch,
                            "--title",
                            self.subject,
                            "--body-file",
                            handle.name,
                        ]
                    ),
                    EXIT_PUBLISH,
                    "gh pr create",
                )
            finally:
                os.unlink(handle.name)
            info = json.loads(
                self._must(
                    self._run(["gh", "pr", "view", self.branch, "--json", "number,state,url"]),
                    EXIT_PUBLISH,
                    "gh pr view",
                ).stdout
            )
        self.pr_number = int(info["number"])
        self.pr_url = info.get("url", "")

    def wait_for_ci(self) -> None:
        number = str(self.pr_number)
        deadline = time.monotonic() + 5 * 60
        while True:
            listed = self._run(["gh", "pr", "checks", number, "--json", "name,bucket"])
            checks = json.loads(listed.stdout or "[]") if listed.stdout.strip() else []
            if checks:
                break
            if time.monotonic() > deadline:
                raise DeliveryError(EXIT_CI, "no CI checks were reported for the pull request")
            self.sleep(15)
        try:
            watched = self._run(
                ["gh", "pr", "checks", number, "--watch", "--fail-fast", "--interval", "30"],
                timeout=self.checks_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise DeliveryError(EXIT_CI, "CI did not finish before the timeout") from exc
        final = json.loads(
            self._run(["gh", "pr", "checks", number, "--json", "name,bucket"]).stdout or "[]"
        )
        failed = [c["name"] for c in final if c.get("bucket") in ("fail", "cancel")]
        pending = [c["name"] for c in final if c.get("bucket") == "pending"]
        if watched.returncode != 0 or failed or pending:
            raise DeliveryError(
                EXIT_CI, f"CI did not pass: failed={failed or 'none'} pending={pending or 'none'}"
            )

    def merge(self) -> None:
        number = str(self.pr_number)
        self._must(
            self._run(
                [
                    "gh",
                    "pr",
                    "merge",
                    number,
                    "--squash",
                    "--subject",
                    f"{self.subject} (#{number})",
                    "--body",
                    self.commit_body,
                ]
            ),
            EXIT_MERGE,
            "gh pr merge",
        )
        self._must(self._git("switch", "main"), EXIT_MERGE, "git switch main")
        self._must(self._git("pull", "--ff-only", "origin", "main"), EXIT_MERGE, "git pull")
        self._git("push", "origin", "--delete", self.branch)
        self._git("branch", "-D", self.branch)

    def reinstall(self) -> None:
        log = Path(tempfile.gettempdir()) / "espansr-deliver-refresh.log"
        # The installer restarts Espanso; never hand it a pipe the daemon could inherit.
        with open(log, "w", encoding="utf-8") as handle:
            result = self._run(
                [self.python, "-m", "espansr", "refresh"],
                stdin=subprocess.DEVNULL,
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
        tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-12:])
        print(tail)
        if result.returncode != 0:
            raise DeliveryError(EXIT_INSTALL, f"espansr refresh failed; log: {log}")

    def verify(self) -> list[str]:
        evidence = []
        doctor = self._run([self.python, "-m", "espansr", "doctor"], stdin=subprocess.DEVNULL)
        output = doctor.stdout + doctor.stderr
        if doctor.returncode != 0:
            raise DeliveryError(EXIT_VERIFY, f"espansr doctor reported a failure:\n{output}")
        if self.is_windows and INDEPENDENT_LINE not in output:
            raise DeliveryError(EXIT_VERIFY, f"Espanso is not running independently:\n{output}")
        evidence.append(
            "espansr doctor: no failures" + (f"; {INDEPENDENT_LINE}" if self.is_windows else "")
        )

        templates = [p for p in self.paths if p.startswith("templates/") and p.endswith(".json")]
        if templates:
            installed = json.loads(
                self._must(
                    self._run([self.python, "-c", INSTALLED_STATE_SCRIPT]),
                    EXIT_VERIFY,
                    "reading the installed templates and Espanso matches",
                ).stdout
            )
            live_dir = Path(installed["templates_dir"])
            matches = installed["matches"]
            matched = []
            for rel in templates:
                source = ROOT / rel
                if not source.is_file():
                    continue  # a removed template has no installed copy to compare
                expected = json.loads(source.read_text(encoding="utf-8"))
                copy = live_dir / source.name
                if not copy.is_file() or json.loads(copy.read_text(encoding="utf-8")) != expected:
                    raise DeliveryError(EXIT_VERIFY, f"installed copy differs from main: {rel}")
                trigger = expected.get("trigger")
                if trigger and (
                    trigger not in matches
                    or (not expected.get("variables") and matches[trigger] != expected["content"])
                ):
                    raise DeliveryError(
                        EXIT_VERIFY, f"Espanso's {trigger} expansion differs from main: {rel}"
                    )
                matched.append(rel)
            if matched:
                evidence.append(
                    f"installed copies and Espanso expansions match main: {', '.join(matched)}"
                )
        return evidence

    def deliver(self) -> int:
        try:
            self.preflight()
            self.local_checks()
            self.publish()
            self.wait_for_ci()
            self.merge()
            if self.install:
                self.reinstall()
            evidence = self.verify() if self.install else ["reinstall skipped (--no-install)"]
        except DeliveryError as exc:
            print(f"\nDELIVERY STOPPED (exit {exc.code}): {exc}", flush=True)
            return exc.code
        merged = self._git("rev-parse", "--short", "HEAD").stdout.strip()
        print("\nDELIVERY SUMMARY")
        print(f"  pull request: {self.pr_url or '#' + str(self.pr_number)}")
        print(f"  merged to main: {merged}")
        for line in evidence:
            print(f"  {line}")
        print("  commands run:")
        for command in self.commands:
            print(f"    {command}")
        return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branch", required=True)
    parser.add_argument("--message-file", required=True, type=Path)
    parser.add_argument("--body-file", type=Path)
    parser.add_argument("--path", dest="paths", action="append", default=[])
    parser.add_argument("--no-install", action="store_true", help="only when the user says so")
    parser.add_argument("--checks-timeout-minutes", type=float, default=45)
    args = parser.parse_args(argv)
    # Installer output can hold characters a Windows console code page lacks;
    # replace them rather than crash after the merge.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    if not shutil.which("gh"):
        print("DELIVERY STOPPED (exit 2): the GitHub CLI (gh) is not on PATH")
        return EXIT_PREFLIGHT
    delivery = Delivery(
        branch=args.branch,
        message=args.message_file.read_text(encoding="utf-8"),
        body=args.body_file.read_text(encoding="utf-8") if args.body_file else None,
        paths=args.paths,
        install=not args.no_install,
        checks_timeout=args.checks_timeout_minutes * 60,
    )
    return delivery.deliver()


if __name__ == "__main__":
    sys.exit(main())
