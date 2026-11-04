"""Git-backed remote template sync for espansr.

Manages init, push, pull, and status operations against a user-provided
git remote so templates stay consistent across machines.
"""

import logging
import os
import shutil
import stat
import subprocess
import unicodedata
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

from espansr.core.atomic import atomic_write_bytes
from espansr.core.config import ConfigManager, get_config_manager

logger = logging.getLogger(__name__)

_GITIGNORE_ENTRIES = ["_versions/", "_meta/"]
_LOCAL_ONLY_BEGIN = "# espansr local-only templates BEGIN (managed; never committed)"
_LOCAL_ONLY_END = "# espansr local-only templates END"


def _escape_gitignore(path: str) -> str:
    """Escape a literal path for a ``/``-anchored gitignore pattern."""
    escaped = "".join("\\" + ch if ch in "\\*?[]" else ch for ch in path)
    return escaped[:-1] + "\\ " if escaped.endswith(" ") else escaped


def _looks_like_pathspec(name: str) -> bool:
    """True when Git would read *name* as a pattern or pathspec magic, not one file name."""
    return name.startswith(":") or any(ch in name for ch in "*?[")


def _literal(paths: List[str]) -> List[str]:
    """Pathspecs that match these exact paths, never as globs."""
    return [f":(literal){path}" for path in paths]


@dataclass(frozen=True)
class OutgoingPrivacy:
    """What a set of commits would share that espansr must not."""

    private: List[str]  # paths with a version that is, or was, a local-only prompt
    unknown: List[str]  # paths with a version whose privacy cannot be read


def _git_bytes(repo: Path, *args: str, data: Optional[bytes] = None):
    """Run git in *repo* with byte output; None when it cannot run or fails."""
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args], input=data, capture_output=True, env=env, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def _read_blobs(repo: Path, blobs: List[str]) -> Optional[Dict[str, bytes]]:
    """The contents of these blob IDs; None when Git cannot read every one."""
    if not blobs:
        return {}
    out = _git_bytes(repo, "cat-file", "--batch", data="".join(f"{b}\n" for b in blobs).encode())
    if out is None:
        return None
    contents, position = {}, 0
    while position < len(out):
        end = out.find(b"\n", position)
        header = out[position:end].split() if end >= 0 else []  # "<sha> <type> <size>"
        if len(header) != 3 or not header[2].isdigit():
            return None  # "<sha> missing" or a damaged answer: fail closed
        size = int(header[2])
        contents[header[0].decode("ascii")] = out[end + 1 : end + 1 + size]
        position = end + 1 + size + 1
    return contents if len(contents) == len(set(blobs)) else None


def _raw_entries(raw: bytes) -> List[tuple]:
    """(mode, blob, path) for each entry of ``--raw -z`` output."""
    tokens, entries, index = raw.split(b"\0"), [], 0
    while index < len(tokens) - 1:
        fields = tokens[index].split()
        if tokens[index].startswith(b":") and len(fields) >= 5:
            path = tokens[index + 1].decode("utf-8", "surrogateescape")
            entries.append((fields[1].decode("ascii"), fields[3].decode("ascii"), path))
            index += 2
        else:
            index += 1
    return entries


def _is_template_path(path: str, root: str) -> bool:
    prefix = f"{root}/" if root else ""
    parts = path[len(prefix) :].split("/")
    return (
        path.startswith(prefix)
        and path.endswith(".json")
        and not {"_versions", "_meta", ".git"}.intersection(parts)
    )


def _identities(repo: Path, private: List[str]) -> Dict[str, set]:
    """Triggers, capability IDs and prompt texts of the local-only templates now."""
    from espansr.core.templates import template_object

    found: Dict[str, set] = {"trigger": set(), "capability_id": set(), "content": set()}
    for path in private:
        try:
            data = template_object((repo / path).read_bytes()) or {}
        except OSError:
            continue
        for key, values in found.items():
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                values.add(value)
    return found


def _same_template(raw: bytes, identities: Dict[str, set]) -> bool:
    """True when *raw* is a version of a local-only template under another name."""
    from espansr.core.templates import template_object

    data = template_object(raw)
    return data is not None and any(
        isinstance(data.get(key), str) and data.get(key) in values
        for key, values in identities.items()
    )


def outgoing_privacy(
    repo: Path,
    revisions: List[str],
    local_only: List[str],
    root: str = "",
    *,
    excluded: Sequence[str] = (),
) -> Optional[OutgoingPrivacy]:
    """Check every version the commits ``revisions`` select, merges included.

    A version is private when its path is local only now, when it was itself
    marked local only (since renamed, removed or restored), or when it is an
    earlier version of a local-only template under a name no shared file has
    now (same trigger, capability ID or prompt text). Deleting a path shares
    nothing. ``excluded`` names commits a destination already has; Git reads
    them on standard input, so no list is too long for a command line.
    Returns None when Git cannot say, so callers push nothing.
    """
    from espansr.core.templates import local_only_state, local_only_state_bytes

    log = _git_bytes(
        repo,
        *("log", "-z", "--raw", "-m", "--no-renames", "--no-abbrev", "--diff-filter=AMT"),
        *(["--stdin"] if excluded else []),
        *("--format=", *revisions, "--", *([root] if root else [])),
        data="".join(f"^{oid}\n" for oid in excluded).encode() if excluded else None,
    )
    if log is None:
        return None
    entries = _raw_entries(log)  # (mode, blob, path) for every version the commits record

    # macOS may store a name decomposed while Git reports it composed.
    current = {unicodedata.normalize("NFC", path) for path in local_only}
    private = {path for _, _, path in entries if unicodedata.normalize("NFC", path) in current}
    candidates = [
        (blob, path)
        for mode, blob, path in entries
        if path not in private
        and mode not in ("120000", "160000")  # a symlink or submodule holds no template text
        and _is_template_path(path, root)
    ]
    contents = _read_blobs(repo, sorted({blob for blob, _ in candidates}))
    if contents is None:
        return None
    identities = _identities(repo, local_only)
    unknown: set = set()
    shared_now: Dict[str, bool] = {}
    for blob, path in candidates:
        state = local_only_state_bytes(contents[blob])
        if state == "private":
            private.add(path)
        elif state == "unknown":
            unknown.add(path)
        else:
            if path not in shared_now:
                file = repo / path
                shared_now[path] = file.is_file() and local_only_state(file) == "shareable"
            if not shared_now[path] and _same_template(contents[blob], identities):
                private.add(path)
    return OutgoingPrivacy(sorted(private), sorted(unknown - private))


def push_urls(repo: Path, remote: str) -> List[str]:
    """Every URL ``git push`` sends to for *remote* (pushurl and insteadOf applied)."""
    out = _git_bytes(repo, "remote", "get-url", "--push", "--all", remote)
    return [line for line in (out or b"").decode("utf-8", "replace").splitlines() if line]


def destination_commits(repo: Path, url: str) -> Optional[List[str]]:
    """Commits and tags a push to *url* need not send, because *url* has them; None when unreadable.

    The refs are read from *url* itself, never from remote-tracking refs: those
    can describe another repository (a pushurl, a URL changed since the last
    fetch) or refs the destination has since deleted, when a narrow fetch
    refspec keeps them out of pruning. Only objects this repository has can
    bound what a push sends.
    """
    listing = _git_bytes(repo, "ls-remote", url)
    if listing is None:
        return None
    oids = sorted(
        {line.split(b"\t", 1)[0].decode() for line in listing.splitlines() if b"\t" in line}
    )
    if not oids:
        return []
    found = _git_bytes(
        repo, "cat-file", "--batch-check", data="".join(f"{o}\n" for o in oids).encode()
    )
    if found is None:
        return None
    kept = (line.split() for line in found.splitlines())
    return [
        fields[0].decode()
        for fields in kept
        if len(fields) == 3 and fields[1] in (b"commit", b"tag")
    ]


def local_only_in_history(
    repo: Path, revisions: List[str], local_only: List[str], root: str = ""
) -> Optional[List[str]]:
    """Paths :func:`outgoing_privacy` reports, private or unknown; None when Git cannot say."""
    found = outgoing_privacy(repo, revisions, local_only, root)
    return None if found is None else sorted(set(found.private) | set(found.unknown))


def staged_privacy(repo: Path, local_only: List[str], root: str = "") -> Optional[List[str]]:
    """Staged paths whose next commit would share a local-only prompt.

    A staged version counts when its path is local only now or when the
    staged bytes are marked local only or cannot be classified, however they
    came to be staged. Returns None when Git cannot say.
    """
    from espansr.core.templates import local_only_state_bytes

    raw = _git_bytes(
        repo, "diff", "--cached", "--raw", "-z", "--no-renames", "--no-abbrev", "--diff-filter=AMT"
    )
    if raw is None:
        return None
    current = {unicodedata.normalize("NFC", path) for path in local_only}
    held = set()
    candidates = []
    for mode, blob, path in _raw_entries(raw):
        if unicodedata.normalize("NFC", path) in current:
            held.add(path)
        elif mode not in ("120000", "160000") and _is_template_path(path, root):
            candidates.append((blob, path))
    contents = _read_blobs(repo, sorted({blob for blob, _ in candidates}))
    if contents is None:
        return None
    held |= {
        path for blob, path in candidates if local_only_state_bytes(contents[blob]) != "shareable"
    }
    return sorted(held)


def _splice_exclude(raw: bytes, entries: List[str]) -> bytes:
    """Replace only espansr's block in an exclude file; every other byte is kept.

    The block goes last, so its patterns win. Appended after content without a
    final newline, it brings its own line break and leaves the file without
    one, so removing it later restores the original bytes exactly. Raises
    ValueError when the block's markers are unbalanced.
    """
    begin, end = _LOCAL_ONLY_BEGIN.encode(), _LOCAL_ONLY_END.encode()
    kept: List[bytes] = []
    inside, start = False, 0
    while start < len(raw):
        stop = raw.find(b"\n", start)
        stop = len(raw) if stop < 0 else stop + 1
        line = raw[start:stop]
        start = stop
        body = line.rstrip(b"\n")
        body = body[:-1] if body.endswith(b"\r") else body
        if body == begin:
            if inside:
                raise ValueError("espansr's block starts twice")
            inside = True
        elif body == end:
            if not inside:
                raise ValueError("espansr's block ends without starting")
            inside = False
            if not line.endswith(b"\n") and kept and kept[-1].endswith(b"\n"):
                kept[-1] = kept[-1][:-1]  # the line break this block brought
        elif not inside:
            kept.append(line)
    if inside:
        raise ValueError("espansr's block never ends")
    content = b"".join(kept)
    if not entries:
        return content
    lines = b"".join(e.encode("utf-8", "surrogateescape") + b"\n" for e in entries)
    if content and not content.endswith(b"\n"):
        return content + b"\n" + begin + b"\n" + lines + end
    return content + begin + b"\n" + lines + end + b"\n"


def _force_remove_readonly(func, path, exc_info):
    """Clear read-only bit and retry — handles git object files on Windows."""
    os.chmod(path, stat.S_IWRITE)
    func(path)


class GitNotFoundError(Exception):
    """Raised when git is not installed or not on PATH."""


class GitTimeoutError(Exception):
    """Raised when a git operation exceeds its timeout."""


class RemoteConflictError(Exception):
    """Raised when a pull encounters merge conflicts."""


class RemoteError(Exception):
    """General remote operation error."""


@dataclass(frozen=True)
class RemotePullOutcome:
    """Detailed result from pulling remote templates."""

    status: str  # "changed", "up_to_date", or "empty_remote"
    changed_files: List[str] = field(default_factory=list)
    branch: Optional[str] = None


class RemoteManager:
    """Manages git-backed remote sync for the templates directory."""

    def __init__(
        self,
        templates_dir: Optional[Path] = None,
        config_manager: Optional[ConfigManager] = None,
    ):
        if templates_dir is not None:
            self.templates_dir = templates_dir
        else:
            from espansr.core.config import get_templates_dir

            self.templates_dir = get_templates_dir()
        self._config_manager = config_manager or get_config_manager()
        # Names the last push_templates() or pull_templates() call left out
        # because they are local only (or their privacy is unknown).
        self.skipped_local_only: List[str] = []
        # What the last pull_templates() call replaced, and what it could not.
        self.pulled: List[str] = []
        self.not_pulled: List[Tuple[str, str]] = []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _git(
        self,
        *args: str,
        check: bool = True,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess:
        """Run a git command inside the templates directory.

        Raises GitTimeoutError if the command does not complete within *timeout* seconds.
        """
        cmd = ["git", "-C", str(self.templates_dir), *args]
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=check,
                env=env,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            raise GitTimeoutError(
                f"git {' '.join(args)} timed out after {timeout}s — "
                "check your network connection or remote URL"
            )

    def _is_git_repo(self) -> bool:
        return (self.templates_dir / ".git").exists()

    def _ensure_git_user(self) -> None:
        """Set a local git user config if not already set (needed for commits)."""
        result = self._git("config", "user.name", check=False)
        if result.returncode != 0 or not result.stdout.strip():
            self._git("config", "user.name", "espansr")
            self._git("config", "user.email", "espansr@local")

    def _git_path(self, name: str) -> Path:
        """Where Git keeps ``name`` for this store; ``.git`` may be a file (worktree)."""
        result = self._git("rev-parse", "--git-path", name, check=False)
        path = result.stdout.strip() if result.returncode == 0 else ""
        if not path:
            raise RemoteError(f"Git could not say where this store keeps {name}.")
        return self.templates_dir / path

    def _privacy(self) -> Tuple[List[str], List[str]]:
        """Repository paths of private templates and of ones whose privacy is unknown."""
        from espansr.core.templates import scan_template_privacy

        scan = scan_template_privacy(self.templates_dir)

        def relative(paths: List[Path]) -> List[str]:
            return [path.relative_to(self.templates_dir).as_posix() for path in paths]

        return relative(scan.private), relative(scan.unknown)

    def _local_only_files(self) -> List[str]:
        """Repository-relative paths of local-only templates, as Git spells them."""
        return self._privacy()[0]

    @staticmethod
    def _refuse_unknown_privacy(unknown: List[str], action: str = "pushing") -> None:
        """Stop before anything is staged while espansr cannot tell what is private."""
        if unknown:
            raise RemoteError(
                f"Not {action}: espansr cannot tell whether "
                + ", ".join(unknown)
                + (" is" if len(unknown) == 1 else " are")
                + ' local only: it cannot be read, is not valid template JSON, or its "local_only"'
                " is not true or false. Nothing was staged or sent, and a template kept out of Git"
                " stays out. Fix the file (saving it from espansr's editor writes a valid"
                " setting), then try again."
            )

    def _keep_local_only_unshared(self, local_only: List[str]) -> None:
        """Keep local-only templates out of every commit.

        Their names go in the store's ``info/exclude`` (found through Git, so a
        linked worktree works), which Git never commits or pushes, so they stay
        unshared even through a manual ``git add``. Only espansr's own block of
        that file changes, byte for byte. A file shared before it was marked
        local only stops being tracked: the next push removes it from the
        remote, while the file here is untouched.
        """
        unlisted = [path for path in local_only if "\n" in path or "\r" in path]
        if unlisted:
            raise RemoteError(
                "Not pushing: Git cannot exclude a file whose name contains a line break: "
                + ", ".join(repr(path) for path in unlisted)
                + ". Rename it, then push again."
            )
        exclude = self._git_path("info/exclude")
        try:
            before = exclude.read_bytes() if exclude.exists() else b""
            after = _splice_exclude(before, ["/" + _escape_gitignore(p) for p in local_only])
            if after != before:
                atomic_write_bytes(exclude, after)
        except (OSError, ValueError) as exc:
            raise RemoteError(
                f"Not pushing: could not update {exclude} ({exc}). Nothing was staged or sent."
            ) from exc
        if local_only:
            tracked = self._git("ls-files", "-z", "--", *_literal(local_only), check=False)
            names = [name for name in tracked.stdout.split("\0") if name]
            if names:
                # -f: a version staged before the template was marked goes too.
                self._git("rm", "--cached", "--quiet", "-f", "--", *_literal(names))

    def _refuse_staged_local_only(self, local_only: List[str]) -> None:
        """Unstage and refuse when the next commit would still share a local-only prompt."""
        leaked = staged_privacy(self.templates_dir, local_only)
        if leaked is None:
            raise RemoteError("Not pushing: could not check staged changes for local-only files.")
        if leaked:
            self._git("reset", "--quiet", "--", *_literal(leaked), check=False)
            raise RemoteError("Refusing to push local-only templates: " + ", ".join(leaked))

    def _refuse_local_only_history(
        self, local_only: List[str], *, before_staging: bool = False
    ) -> None:
        """Refuse a push whose unpushed commits would still carry a local-only prompt.

        Unpushed means what each URL the push goes to lacks, read from that URL
        now (see destination_commits): after set_remote() origin's tracking refs
        still describe the previous repository. A fetch first brings origin's
        newest commits here, so commits it already has are recognized. Before
        staging, a destination that cannot be read is left to the check that runs
        right before the push, which refuses.
        """
        if self._current_head() is None:
            return  # nothing committed yet, so nothing to send
        private, unknown = set(), set()
        fetched = self._git("remote", "get-url", "origin", check=False).stdout.strip()
        urls = push_urls(self.templates_dir, "origin") or [""]
        if fetched in urls:
            self._git("fetch", "--quiet", "origin", check=False)
        present: Optional[List[str]] = []
        for url in urls:
            present = destination_commits(self.templates_dir, url) if url else []
            if present is None:
                if before_staging:
                    return
                raise RemoteError(
                    f"Not pushing: could not read what {url} already has, so espansr cannot "
                    "check what the push would send. Nothing was sent and your files are "
                    "unchanged."
                )
            part = outgoing_privacy(self.templates_dir, ["HEAD"], local_only, excluded=present)
            if part is None:
                raise RemoteError(
                    "Not pushing: could not check unpushed commits for local-only templates."
                )
            private.update(part.private)
            unknown.update(part.unknown)
        found = OutgoingPrivacy(sorted(private), sorted(unknown - private))
        if found.private or found.unknown:
            branch = self._detect_remote_branch()
            tip = branch and self._git("rev-parse", f"origin/{branch}", check=False).stdout.strip()
            # Resetting to origin's branch helps only when the one destination still has it.
            undo = (
                f'run: git -C "{self.templates_dir}" reset --soft origin/{branch} '
                "(it keeps every file), then push again."
                if tip and urls == [fetched] and tip in (present or [])
                else "take them out of those commits, then push again."
            )
            problems = []
            if found.private:
                problems.append("contain local-only templates: " + ", ".join(found.private))
            if found.unknown:
                problems.append(
                    "hold versions espansr cannot classify (not valid template JSON, or"
                    ' "local_only" is not true or false): ' + ", ".join(found.unknown)
                )
            raise RemoteError(
                "Not pushing: unpushed commits "
                + "; they also ".join(problems)
                + ". Nothing was sent and your files are unchanged. To fix it, "
                + undo
            )

    def _refuse_incoming_local_only(
        self, remote_ref: str, local_only: List[str], before_head: Optional[str]
    ) -> None:
        """Refuse a pull that would bring the remote's own file onto a local-only path."""
        if not local_only:
            return
        base = None
        if before_head is not None:
            merge_base = self._git("merge-base", "HEAD", remote_ref, check=False)
            base = merge_base.stdout.strip() if merge_base.returncode == 0 else None
        if base:
            incoming = self._git(
                "diff", "--name-only", "--no-renames", "--diff-filter=AM", "-z", base, remote_ref
            )
        else:
            incoming = self._git("ls-tree", "-r", "--name-only", "-z", remote_ref)
        clashes = sorted(set(incoming.stdout.split("\0")) & set(local_only))
        if clashes:
            raise RemoteConflictError(
                "Not pulling: the remote has its own version of "
                + ", ".join(clashes)
                + ", which is local only on this machine. Your copy is unchanged. Rename it "
                "(for example add -mine to the file name) or turn off Local only, then pull again."
            )

    @contextmanager
    def _keeping_local_only(self, local_only: List[str]) -> Iterator[None]:
        """Give local-only templates back, byte for byte, after Git rewrites the tree.

        Git treats ignored files as disposable: a rebase that replays the commit
        which stopped sharing a template deletes the file, and an aborted rebase
        can remove it too. A copy waits in ``.git`` until the files are back.
        """
        saved = {}
        for path in local_only:
            source = self.templates_dir / path
            try:
                saved[path] = (source.read_bytes(), stat.S_IMODE(source.stat().st_mode))
            except OSError as exc:
                raise RemoteError(
                    f"Not pulling: {path} may be local only and cannot be read to keep it safe"
                    f" ({exc}). Nothing was changed."
                ) from exc
        backup = self._git_path("espansr-local-only")
        if backup.exists():
            kept = backup.with_name(f"espansr-local-only-{datetime.now():%Y%m%d%H%M%S}")
            backup.rename(kept)
            logger.warning("Kept local-only copies from an interrupted pull in %s", kept)
        for path, (data, _) in saved.items():
            atomic_write_bytes(backup / path, data)
        try:
            yield
        finally:
            for path, (data, mode) in saved.items():
                target = self.templates_dir / path
                if not target.is_file() or target.read_bytes() != data:
                    atomic_write_bytes(target, data, mode=mode)
            shutil.rmtree(backup, ignore_errors=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_git(self) -> None:
        """Verify git is installed. Raises GitNotFoundError if not."""
        if shutil.which("git") is None:
            raise GitNotFoundError(
                "git is required for remote sync. " "Install git and ensure it is on your PATH."
            )

    def ensure_gitignore(self) -> None:
        """Create or update .gitignore in templates dir."""
        gitignore_path = self.templates_dir / ".gitignore"
        existing_lines: List[str] = []
        if gitignore_path.exists():
            existing_lines = gitignore_path.read_text().splitlines()

        changed = False
        for entry in _GITIGNORE_ENTRIES:
            if entry not in existing_lines:
                existing_lines.append(entry)
                changed = True

        if changed or not gitignore_path.exists():
            gitignore_path.write_text("\n".join(existing_lines) + "\n")

    def init_repo(self) -> None:
        """Initialize the templates directory as a git repo if needed."""
        self.check_git()
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        if not self._is_git_repo():
            subprocess.run(
                ["git", "init", str(self.templates_dir)],
                capture_output=True,
                text=True,
                check=True,
            )
        self._ensure_git_user()
        self.ensure_gitignore()

        # Make initial commit if repo has no commits yet
        head_check = self._git("rev-parse", "HEAD", check=False)
        if head_check.returncode != 0:
            self._git("add", ".gitignore")
            self._git("commit", "-m", "espansr: initial commit")

    def set_remote(self, url: str) -> None:
        """Configure the git remote and persist URL in config."""
        self.check_git()
        self.init_repo()

        # Set or update origin
        result = self._git("remote", "get-url", "origin", check=False)
        if result.returncode == 0:
            self._git("remote", "set-url", "origin", url)
        else:
            self._git("remote", "add", "origin", url)

        # Persist in config
        config = self._config_manager.config
        config.remote.url = url
        self._config_manager.save(config)

    def remove_remote(self) -> None:
        """Disconnect from remote: clear config and remove .git."""
        config = self._config_manager.config
        config.remote.url = ""
        config.remote.last_pull = ""
        config.remote.last_push = ""
        self._config_manager.save(config)

        git_dir = self.templates_dir / ".git"
        if git_dir.exists():
            shutil.rmtree(git_dir, onerror=_force_remove_readonly)

        gitignore = self.templates_dir / ".gitignore"
        if gitignore.exists():
            gitignore.unlink()

    def status(self) -> Dict:
        """Return remote sync status as a dict."""
        config = self._config_manager.config
        result: Dict = {
            "url": config.remote.url,
            "last_pull": config.remote.last_pull,
            "last_push": config.remote.last_push,
            "dirty": [],
        }

        if self._is_git_repo():
            diff_result = self._git("status", "--porcelain", check=False)
            if diff_result.returncode == 0:
                result["dirty"] = [
                    line.strip().split(maxsplit=1)[-1]
                    for line in diff_result.stdout.strip().splitlines()
                    if line.strip()
                ]

        return result

    def _detect_remote_branch(self) -> Optional[str]:
        """Detect the default branch on origin."""
        for branch in ("main", "master"):
            check = self._git("rev-parse", "--verify", f"origin/{branch}", check=False)
            if check.returncode == 0:
                return branch
        return None

    def _current_head(self) -> Optional[str]:
        """Return the current HEAD SHA, or None when there is no local commit."""
        result = self._git("rev-parse", "HEAD", check=False)
        if result.returncode != 0:
            return None
        head = result.stdout.strip()
        return head or None

    def _changed_files_between(
        self,
        before_head: Optional[str],
        after_head: Optional[str],
    ) -> List[str]:
        """Return files changed between two revisions, preserving git order."""
        if after_head is None:
            return []

        if before_head is None:
            result = self._git("ls-tree", "-r", "--name-only", after_head, check=False)
        elif before_head != after_head:
            result = self._git("diff", "--name-only", before_head, after_head, "--", check=False)
        else:
            return []

        if result.returncode != 0:
            return []

        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def pull(self) -> bool:
        """Pull latest templates from remote (rebase strategy).

        Returns True on success.
        Raises RemoteConflictError on merge conflicts.
        Raises RemoteError on other failures.
        """
        self.pull_with_result()
        return True

    def pull_with_result(self) -> RemotePullOutcome:
        """Pull latest templates from remote and report whether files changed.

        Returns:
            RemotePullOutcome with status "changed", "up_to_date", or
            "empty_remote".

        Raises RemoteConflictError on merge conflicts.
        Raises RemoteError on other failures.
        """
        self.check_git()
        if not self._is_git_repo():
            raise RemoteError(
                "Templates directory is not a git repository. "
                "Run 'espansr remote set <url>' first."
            )

        # Fetch first
        fetch_result = self._git("fetch", "origin", check=False)
        if fetch_result.returncode != 0:
            raise RemoteError(f"Failed to fetch from remote: {fetch_result.stderr.strip()}")

        remote_branch = self._detect_remote_branch()
        if remote_branch is None:
            # Remote is empty, nothing to pull
            return RemotePullOutcome(status="empty_remote")

        # Check if we have local commits
        before_head = self._current_head()
        private, unknown = self._privacy()
        local_only = private + unknown  # a file whose privacy is unknown is kept like a private one
        self._refuse_incoming_local_only(f"origin/{remote_branch}", local_only, before_head)
        with self._keeping_local_only(local_only):
            self._pull_into_tree(remote_branch, before_head, local_only)

        after_head = self._current_head()
        changed_files = self._changed_files_between(before_head, after_head)

        # Update timestamp
        config = self._config_manager.config
        config.remote.last_pull = datetime.now().isoformat()
        self._config_manager.save(config)

        if changed_files:
            return RemotePullOutcome(
                status="changed",
                changed_files=changed_files,
                branch=remote_branch,
            )
        return RemotePullOutcome(status="up_to_date", branch=remote_branch)

    def _tracked_local_only_hint(self, local_only: List[str]) -> str:
        """Why a pull stops while Git still tracks a template that is now local only."""
        if not local_only:
            return ""
        tracked = self._git("ls-files", "-z", "--", *_literal(local_only), check=False)
        names = [name for name in tracked.stdout.split("\0") if name]
        if not names:
            return ""
        return (
            f"\n{', '.join(names)} is local only here, but this store still tracks it, so Git "
            "counts your private copy as an unsaved change. Your copy is unchanged. To pull, run "
            "'espansr push' first (it stops sharing the file and removes the remote's copy), "
            "or turn off Local only."
        )

    def _pull_into_tree(
        self, remote_branch: str, before_head: Optional[str], local_only: List[str] = ()
    ) -> None:
        """Check out or rebase onto ``origin/<remote_branch>``."""
        if before_head is None:
            # No local commits — just checkout the remote branch
            self._git(
                "checkout",
                "-B",
                remote_branch,
                f"origin/{remote_branch}",
                check=False,
            )
            self._git(
                "branch",
                f"--set-upstream-to=origin/{remote_branch}",
                remote_branch,
                check=False,
            )
            return
        # Ensure tracking is set up
        self._git("branch", f"--set-upstream-to=origin/{remote_branch}", check=False)
        # Rebase local changes on top of remote
        rebase_result = self._git("pull", "--rebase", "origin", remote_branch, check=False)
        if rebase_result.returncode != 0:
            stderr = rebase_result.stderr.strip()
            stdout = rebase_result.stdout.strip()
            # Check for conflicts
            conflict_check = self._git("diff", "--name-only", "--diff-filter=U", check=False)
            conflicted = conflict_check.stdout.strip()
            if conflicted:
                # Abort the rebase to leave repo in clean state
                self._git("rebase", "--abort", check=False)
                raise RemoteConflictError(
                    f"Merge conflicts detected in: {conflicted}\n"
                    "Resolve conflicts manually or use 'espansr remote remove' and re-set."
                )
            raise RemoteError(
                f"Pull failed: {stderr or stdout}" + self._tracked_local_only_hint(list(local_only))
            )

    def _store_path(self, name: str) -> Optional[str]:
        """``name`` as one path inside the store, as Git spells it; None when it is not.

        Relative names are taken from the store; ``.`` and ``..`` are resolved
        first, so a name can never reach a file other than the one it spells.
        """
        root = Path(os.path.normpath(self.templates_dir))
        candidate = Path(name)
        if not candidate.is_absolute():
            candidate = root / candidate
        try:
            relative = Path(os.path.normpath(candidate)).relative_to(root)
        except ValueError:
            return None
        if not relative.parts or relative.parts[0] == ".git":
            return None
        return relative.as_posix()

    def pull_templates(self, template_files: List[str]) -> bool:
        """Selectively fetch specific template files from remote.

        Each name is one file in the store: a path relative to it, as Git
        spells it, or an absolute path inside it. A folder, a path outside the
        store, or a Git pattern or pathspec (``personal/*.json``,
        ``:(glob)...``) that names no file is refused before anything changes;
        names are never expanded. A template that is local only here, or whose privacy
        espansr cannot tell, is never replaced: it goes in
        ``skipped_local_only``. ``pulled`` lists what was replaced and
        ``not_pulled`` the rest, with the reason.

        Args:
            template_files: List of filenames (e.g. ["greeting.json"]).
        """
        from espansr.core.templates import local_only_state

        self.check_git()
        if not self._is_git_repo():
            raise RemoteError("Templates directory is not a git repository.")
        self.pulled, self.skipped_local_only, self.not_pulled = [], [], []
        targets = []
        for name in template_files:
            path = self._store_path(name)
            if path is None:
                raise RemoteError(
                    f"Not pulling: {name!r} is not a file inside {self.templates_dir}. "
                    "Nothing was changed."
                )
            targets.append(path)

        # Fetch latest
        self._git("fetch", "origin", check=True)

        # Determine remote branch
        remote_branch = self._detect_remote_branch() or "main"
        ref = f"origin/{remote_branch}"
        kinds = {
            path: self._git("cat-file", "-t", f"{ref}:{path}", check=False).stdout.strip()
            for path in targets
        }
        folders = [p for p in targets if kinds[p] == "tree" or (self.templates_dir / p).is_dir()]
        if folders:
            raise RemoteError(
                "Not pulling: "
                + ", ".join(folders)
                + " is a folder; name the template files in it. Nothing was changed."
            )
        patterns = [
            name
            for name, path in zip(template_files, targets)
            if _looks_like_pathspec(name)
            and kinds[path] != "blob"
            and not (self.templates_dir / path).exists()
        ]
        if patterns:
            raise RemoteError(
                "Not pulling: "
                + ", ".join(patterns)
                + " is a pattern, not a template file name; espansr pulls exact files only, "
                "so name each one. Nothing was changed."
            )

        # Checkout each exact file from remote; never over a local-only template
        for path in targets:
            local = self.templates_dir / path
            if (
                path.endswith(".json")
                and local.is_file()
                and local_only_state(local) != "shareable"
            ):
                logger.warning("Skipping %s: it is local only here and is never replaced.", path)
                self.skipped_local_only.append(path)
                continue
            if kinds[path] != "blob":
                self.not_pulled.append((path, "the remote does not have it"))
                continue
            result = self._git("checkout", ref, "--", *_literal([path]), check=False)
            if result.returncode != 0:
                logger.warning("Could not pull %s: %s", path, result.stderr.strip())
                self.not_pulled.append((path, result.stderr.strip() or "git checkout failed"))
                continue
            self.pulled.append(path)

        config = self._config_manager.config
        config.remote.last_pull = datetime.now().isoformat()
        self._config_manager.save(config)
        return True

    def push(self, message: Optional[str] = None) -> bool:
        """Stage all changes, commit, and push.

        Args:
            message: Custom commit message. Auto-generated if None.
        """
        self.check_git()
        if not self._is_git_repo():
            raise RemoteError("Templates directory is not a git repository.")

        self._ensure_git_user()
        self.ensure_gitignore()
        local_only, unknown = self._privacy()
        self._refuse_unknown_privacy(unknown)
        self._refuse_local_only_history(local_only, before_staging=True)
        self._keep_local_only_unshared(local_only)

        # Stage everything except local-only templates
        self._git("add", ".")
        self._refuse_staged_local_only(local_only)

        # Check if there's anything to commit
        status_result = self._git("status", "--porcelain", check=False)
        staged = [line for line in status_result.stdout.strip().splitlines() if line.strip()]

        if staged:
            if message is None:
                message = f"espansr: sync {len(staged)} template(s)"
            self._git("commit", "-m", message)
        self._refuse_local_only_history(local_only)

        # Push — determine branch name
        branch_result = self._git("rev-parse", "--abbrev-ref", "HEAD", check=False)
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"
        if not branch or branch == "HEAD":
            branch = "main"

        push_result = self._git("push", "-u", "origin", branch, check=False)
        if push_result.returncode != 0:
            stderr = push_result.stderr.strip()
            if "rejected" in stderr or "non-fast-forward" in stderr:
                raise RemoteError("Push rejected — remote has changes. Run 'espansr pull' first.")
            raise RemoteError(f"Push failed: {stderr}")

        config = self._config_manager.config
        config.remote.last_push = datetime.now().isoformat()
        self._config_manager.save(config)
        return True

    def push_templates(self, template_files: List[str], message: Optional[str] = None) -> bool:
        """Stage and push only specific template files.

        Args:
            template_files: List of filenames to push.
            message: Custom commit message.
        """
        self.check_git()
        if not self._is_git_repo():
            raise RemoteError("Templates directory is not a git repository.")

        self._ensure_git_user()
        self.ensure_gitignore()
        local_only, unknown = self._privacy()
        self._refuse_unknown_privacy(unknown)
        self._refuse_local_only_history(local_only, before_staging=True)

        # Stage .gitignore too if it exists
        gitignore = self.templates_dir / ".gitignore"
        if gitignore.exists():
            self._git("add", ".gitignore")

        # Stage only the specified files; a local-only template is never one
        sent = []  # the commit message names only these, never a skipped local-only file
        self.skipped_local_only = []
        for fname in template_files:
            fpath = self.templates_dir / fname
            if fpath.exists() and Path(fname).as_posix() in local_only:
                logger.warning("Skipping local-only template %s; it is never pushed.", fname)
                self.skipped_local_only.append(fname)
                continue
            if fpath.exists():
                self._git("add", fname)
            sent.append(fname)
        self._refuse_staged_local_only(local_only)

        # Commit only the named files (and .gitignore); other staged work stays staged
        diff_result = self._git("diff", "--cached", "--name-only", "-z", check=False)
        named = {Path(name).as_posix() for name in sent} | {".gitignore"}
        selected = [path for path in diff_result.stdout.split("\0") if path in named]
        if not selected:
            logger.info("Nothing to push for specified templates.")
            return True

        if message is None:
            message = f"espansr: sync {', '.join(sent)}"
        self._git("commit", "-m", message, "--only", "--", *_literal(selected))
        self._refuse_local_only_history(local_only)

        branch_result = self._git("rev-parse", "--abbrev-ref", "HEAD", check=False)
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"
        if not branch or branch == "HEAD":
            branch = "main"

        push_result = self._git("push", "-u", "origin", branch, check=False)
        if push_result.returncode != 0:
            raise RemoteError(f"Push failed: {push_result.stderr.strip()}")

        config = self._config_manager.config
        config.remote.last_push = datetime.now().isoformat()
        self._config_manager.save(config)
        return True

    def auto_pull(self) -> bool:
        """Silently pull if a remote is configured and auto_pull is enabled.

        Returns True if pull succeeded or was skipped (no remote configured).
        Returns False if pull failed (failure is logged as a warning).
        """
        config = self._config_manager.config
        if not config.remote.url or not config.remote.auto_pull:
            return True

        if not self._is_git_repo():
            return True

        try:
            self.check_git()
            self.pull()
            return True
        except (GitNotFoundError, RemoteError, RemoteConflictError) as exc:
            logger.warning("Auto-pull failed: %s", exc)
            return False
