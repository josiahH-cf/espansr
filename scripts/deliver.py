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
LOCAL_ONLY_MARK = re.compile(r'"local_only"\s*:\s*true\b')
URL_CREDENTIALS = re.compile(r"(?<=://)[^/@\s]+@")
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


def local_only_state(path: Path) -> str:
    """The rule of ``espansr.core.templates.local_only_state``, without importing espansr."""
    try:
        return local_only_state_bytes(path.read_bytes())
    except OSError:
        return "unknown"


def template_codec(raw: bytes) -> str:
    """UTF-16 after a UTF-16 byte-order mark, otherwise UTF-8 (a BOM allowed)."""
    return "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"


def template_object(raw: bytes) -> dict | None:
    """The JSON object in a template's bytes, decoded as the privacy rule decodes them."""
    try:
        data = json.loads(raw.decode(template_codec(raw)))
    except (ValueError, RecursionError):  # UnicodeDecodeError is a ValueError
        return None
    return data if isinstance(data, dict) else None


def local_only_state_bytes(raw: bytes) -> str:
    """Classify a template's bytes as private, shareable, or unknown (fails closed)."""
    codec = template_codec(raw)
    try:
        text = raw.decode(codec)
    except UnicodeDecodeError:
        # Bytes the loader cannot read are never shareable; only a mark still
        # legible in them keeps the file private rather than unknown.
        legible = raw.decode(codec, errors="replace")
        return "private" if LOCAL_ONLY_MARK.search(legible) else "unknown"
    objects: list = []

    def remember(pairs: list) -> dict:
        objects.append(pairs)
        return dict(pairs)

    try:
        data = json.loads(text, object_pairs_hook=remember)
    except (ValueError, RecursionError):
        return "private" if LOCAL_ONLY_MARK.search(text) else "unknown"
    if not isinstance(data, dict):
        return "unknown"
    values = [value for key, value in objects[-1] if key == "local_only"]
    if not values:
        return "shareable"
    if len(values) == 1 and values[0] is True:
        return "private"
    return "shareable" if len(values) == 1 and values[0] is False else "unknown"


def is_template_path(path: str) -> bool:
    parts = path.split("/")
    return (
        parts[0] == "templates"
        and path.endswith(".json")
        and not {"_versions", "_meta"}.intersection(parts)
    )


def is_local_only_template(path: Path) -> bool:
    """True when the JSON file at *path* is marked local only."""
    return path.suffix == ".json" and path.is_file() and local_only_state(path) == "private"


def is_local_only_bytes(raw: bytes) -> bool:
    return local_only_state_bytes(raw) == "private"


def private_identities(templates: Path) -> dict[str, set[str]]:
    """Triggers, capability IDs and prompt texts of every template here that is not shareable.

    Tracked or not, listed for delivery or not, as ``espansr push`` reads them.
    """
    found: dict[str, set[str]] = {"trigger": set(), "capability_id": set(), "content": set()}
    for path in sorted(templates.glob("**/*.json")) if templates.is_dir() else []:
        if {"_versions", "_meta", ".git"}.intersection(path.relative_to(templates).parts):
            continue
        if not path.is_file() or local_only_state(path) == "shareable":
            continue
        try:
            data = template_object(path.read_bytes()) or {}
        except OSError:
            continue
        for key, values in found.items():
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                values.add(value)
    return found


def masked(text: str) -> str:
    """*text* with any credentials in a URL (``https://user:token@host``) hidden."""
    return URL_CREDENTIALS.sub("***@", text)


def same_template(raw: bytes, identities: dict[str, set[str]]) -> bool:
    """True when *raw* is a version of one of those templates, whatever its name."""
    data = template_object(raw)
    return data is not None and any(
        isinstance(data.get(key), str) and data.get(key) in values
        for key, values in identities.items()
    )


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
        shown = masked(" ".join(argv))  # git ls-remote takes a URL that may carry a token
        self.commands.append(shown)
        print(f"$ {shown}", flush=True)
        return self.runner(list(argv), cwd=cwd, **kwargs)

    def _git(self, *args: str, **kwargs):
        return self._run(["git", *args], **kwargs)

    def _must(self, result, code: int, what: str):
        if result.returncode != 0:
            detail = (getattr(result, "stderr", "") or getattr(result, "stdout", "") or "").strip()
            raise DeliveryError(code, f"{what} failed (exit {result.returncode}): {detail}")
        return result

    def _push_urls(self, code: int) -> list[str]:
        """Every URL ``git push origin`` sends to (a pushurl, several, pushInsteadOf applied)."""
        listed = self._git("remote", "get-url", "--push", "--all", "origin")
        urls = [line.strip() for line in (listed.stdout or "").splitlines() if line.strip()]
        if listed.returncode != 0 or not urls:
            raise DeliveryError(
                code, "could not read where git push origin sends, so nothing was pushed"
            )
        return urls

    def _destination_commits(self, url: str, code: int) -> list[str]:
        """Commits and tags *url* has now, read from *url* itself, that this checkout has too.

        Never origin's remote-tracking refs: they describe the fetch URL as of
        the last fetch, so a pushurl, a second push URL, or a retargeted origin
        whose narrow fetch refspec leaves the old refs unpruned makes them
        describe another repository. Only objects this checkout has can bound
        what a push sends, so any other commit stays in the check.
        """
        listing = self._git("ls-remote", url)
        if listing.returncode != 0:
            raise DeliveryError(
                code,
                f"could not read what {masked(url)} already has, so delivery cannot check what "
                "the push would send; nothing was pushed",
            )
        oids = sorted(
            {line.split("\t", 1)[0] for line in (listing.stdout or "").splitlines() if "\t" in line}
        )
        if not oids:
            return []
        found = self._git(
            "cat-file", "--batch-check", input="".join(f"{o}\n" for o in oids).encode(), text=False
        )
        if found.returncode != 0:
            raise DeliveryError(code, f"could not compare {masked(url)} with this checkout")
        fields = (line.split() for line in (found.stdout or b"").decode().splitlines())
        return [f[0] for f in fields if len(f) == 3 and f[1] in ("commit", "tag")]

    def _local_only_history(self, revision: str = "HEAD", code: int = EXIT_PREFLIGHT) -> list[str]:
        """Templates in what pushing *revision* to origin sends that are local only or unclear.

        What a push sends is what each push URL lacks, read from that URL now
        (see ``_destination_commits``), never origin/main: a pushurl, a second
        push URL, or a stale tracking ref left by a retargeted origin would
        leave history the destination lacks unchecked. An unreadable
        destination stops delivery. Every version is read, merge commits
        included; one that cannot be classified counts, so delivery fails
        closed. So does an earlier version of a template that is not shareable
        here now (tracked or untracked, listed or not) under a name no
        shareable file has now: same trigger, capability ID or prompt text, as
        ``espansr push`` checks.
        """
        identities = private_identities(ROOT / "templates")
        carried: set[str] = set()
        for url in self._push_urls(code):
            present = self._destination_commits(url, code)
            log = self._git(
                *("log", "-z", "--raw", "-m", "--no-renames", "--no-abbrev", "--diff-filter=AMT"),
                *(["--stdin"] if present else []),
                *("--format=", revision, "--", "templates"),
                input="".join(f"^{oid}\n" for oid in present).encode() if present else None,
                text=False,
            )
            if log.returncode != 0:
                raise DeliveryError(code, "could not read unpushed commits for privacy")
            carried |= self._carried(log.stdout or b"", identities)
        return sorted(carried)

    def _carried(self, raw_log: bytes, identities: dict[str, set[str]]) -> set[str]:
        """Paths of the versions in a ``git log -z --raw`` listing that must not be sent."""
        shared_now: dict[str, bool] = {}
        tokens, carried, index = raw_log.split(b"\0"), set(), 0
        while index < len(tokens) - 1:
            fields = tokens[index].split()
            if not (tokens[index].startswith(b":") and len(fields) >= 5):
                index += 1
                continue
            mode, blob = fields[1].decode(), fields[3].decode()
            path = tokens[index + 1].decode("utf-8", "surrogateescape")
            index += 2
            if not path.endswith(".json") or mode in ("120000", "160000"):
                continue
            if is_local_only_template(ROOT / path):
                carried.add(path)
                continue
            content = self._git("cat-file", "blob", blob, text=False)
            raw = content.stdout or b""
            state = local_only_state_bytes(raw)
            if content.returncode != 0 or state == "private":
                carried.add(path)
            elif is_template_path(path) and state == "unknown":
                carried.add(path)
            elif is_template_path(path) and same_template(raw, identities):
                if path not in shared_now:
                    file = ROOT / path
                    shared_now[path] = file.is_file() and local_only_state(file) == "shareable"
                if not shared_now[path]:
                    carried.add(path)
        return carried

    def _unlisted_changes(self) -> list[str]:
        """Tracked files outside the listed paths with staged or unstaged changes.

        The index and the working tree are read separately: a file staged with
        other content and then put back in the working tree matches HEAD there.
        """
        names: set[str] = set()
        for diff_args in (("--cached",), ()):
            diff = self._git("diff", *diff_args, "--name-only", "-z", text=False)
            if diff.returncode != 0:
                raise DeliveryError(EXIT_PREFLIGHT, "could not read uncommitted changes")
            names.update((diff.stdout or b"").decode("utf-8", "surrogateescape").split("\0"))
        return sorted(name for name in names if name and name not in self.paths)

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
        private = sorted(p for p in set(self.paths) | committed if is_local_only_template(ROOT / p))
        if private:
            raise DeliveryError(
                EXIT_PREFLIGHT, f"local-only templates are never delivered: {private}"
            )
        unclear = sorted(
            p
            for p in set(self.paths) | committed
            if is_template_path(p)
            and (ROOT / p).is_file()
            and local_only_state(ROOT / p) == "unknown"
        )
        if unclear:
            raise DeliveryError(
                EXIT_PREFLIGHT,
                "cannot tell whether these templates are local only (unreadable, invalid JSON, "
                f'or "local_only" not true/false); fix them first: {unclear}',
            )
        carried = self._local_only_history()
        if carried:
            raise DeliveryError(
                EXIT_PREFLIGHT,
                f"unpushed commits carry local-only templates, never delivered: {carried}",
            )
        # Catching up must never stash and replay uncommitted work that is not
        # part of this delivery (a staged change comes back unstaged); refuse.
        based = self._git("merge-base", "--is-ancestor", "origin/main", "HEAD").returncode == 0
        if not based:
            others = self._unlisted_changes()
            if others:
                raise DeliveryError(
                    EXIT_PREFLIGHT,
                    f"{current} is behind origin/main, and catching up would stash other "
                    f"uncommitted changes in this checkout: {others}. Nothing was committed, "
                    "stashed or rebased. Bring it up to date without stashing them (on main, "
                    "git merge --ff-only origin/main), then rerun.",
                )

        if current == "main":
            self._must(self._git("switch", "-c", self.branch), EXIT_PREFLIGHT, "git switch")
        self._must(self._git("add", "--", *self.paths), EXIT_PREFLIGHT, "git add")
        # Only the listed paths: anything else already staged (another session's
        # work, or a private template staged by hand) stays out of the commit.
        listed = [f":(literal){path}" for path in self.paths]
        staged = self._git("diff", "--cached", "--name-only", "--", *listed).stdout.split()
        if staged:
            # git reads the message, like gh the body below, as UTF-8 whatever the locale.
            with tempfile.NamedTemporaryFile(
                "w", suffix=".txt", delete=False, encoding="utf-8"
            ) as handle:
                handle.write(self.message)
            try:
                self._must(
                    self._git("commit", "-F", handle.name, "--only", "--", *listed),
                    EXIT_PREFLIGHT,
                    "git commit",
                )
            finally:
                os.unlink(handle.name)

        if not based:  # nothing else was uncommitted; never stash, whatever the config says
            rebased = self._git(
                "-c", "rebase.autoStash=false", "rebase", "--no-autostash", "origin/main"
            )
            if rebased.returncode != 0:
                self._git("rebase", "--abort")
                raise DeliveryError(
                    EXIT_PREFLIGHT,
                    "rebase onto origin/main did not complete (a conflict, or changes made "
                    "meanwhile); nothing was stashed. Resolve it and rerun",
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
        # Read the outgoing commits again as they are now (committed, rebased),
        # and the branch the push sends, so nothing private is pushed whatever
        # changed since preflight.
        carried = self._local_only_history(f"refs/heads/{self.branch}", EXIT_PUBLISH)
        if carried:
            raise DeliveryError(
                EXIT_PUBLISH,
                f"unpushed commits carry local-only templates, never delivered: {carried}",
            )
        self._must(
            self._git("push", "--force-with-lease", "-u", "origin", self.branch),
            EXIT_PUBLISH,
            "git push",
        )
        existing = self._run(["gh", "pr", "view", self.branch, "--json", "number,state,url"])
        info = json.loads(existing.stdout) if existing.returncode == 0 else {}
        if info.get("state") != "OPEN":
            with tempfile.NamedTemporaryFile(
                "w", suffix=".md", delete=False, encoding="utf-8"
            ) as handle:
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
