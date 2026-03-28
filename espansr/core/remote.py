"""Git-backed remote template sync for espansr.

Manages init, push, pull, and status operations against a user-provided
git remote so templates stay consistent across machines.
"""

import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from espansr.core.config import ConfigManager, get_config_manager

logger = logging.getLogger(__name__)

_GITIGNORE_ENTRIES = ["_versions/", "_meta/"]


class GitNotFoundError(Exception):
    """Raised when git is not installed or not on PATH."""


class RemoteConflictError(Exception):
    """Raised when a pull encounters merge conflicts."""


class RemoteError(Exception):
    """General remote operation error."""


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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command inside the templates directory."""
        cmd = ["git", "-C", str(self.templates_dir), *args]
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
            env=env,
        )

    def _is_git_repo(self) -> bool:
        return (self.templates_dir / ".git").exists()

    def _ensure_git_user(self) -> None:
        """Set a local git user config if not already set (needed for commits)."""
        result = self._git("config", "user.name", check=False)
        if result.returncode != 0 or not result.stdout.strip():
            self._git("config", "user.name", "espansr")
            self._git("config", "user.email", "espansr@local")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check_git(self) -> None:
        """Verify git is installed. Raises GitNotFoundError if not."""
        if shutil.which("git") is None:
            raise GitNotFoundError(
                "git is required for remote sync. "
                "Install git and ensure it is on your PATH."
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
            shutil.rmtree(git_dir)

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

    def pull(self) -> bool:
        """Pull latest templates from remote (rebase strategy).

        Returns True on success.
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
            return True

        # Check if we have local commits
        local_ref = self._git("rev-parse", "HEAD", check=False)
        if local_ref.returncode != 0:
            # No local commits — just checkout the remote branch
            self._git(
                "checkout", "-B", remote_branch,
                f"origin/{remote_branch}", check=False,
            )
            self._git(
                "branch", f"--set-upstream-to=origin/{remote_branch}",
                remote_branch, check=False,
            )
        else:
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
                raise RemoteError(f"Pull failed: {stderr or stdout}")

        # Update timestamp
        config = self._config_manager.config
        config.remote.last_pull = datetime.now().isoformat()
        self._config_manager.save(config)
        return True

    def pull_templates(self, template_files: List[str]) -> bool:
        """Selectively fetch specific template files from remote.

        Args:
            template_files: List of filenames (e.g. ["greeting.json"]).
        """
        self.check_git()
        if not self._is_git_repo():
            raise RemoteError("Templates directory is not a git repository.")

        # Fetch latest
        self._git("fetch", "origin", check=True)

        # Determine remote branch
        remote_branch = self._detect_remote_branch() or "main"

        # Checkout specific files from remote
        for fname in template_files:
            result = self._git("checkout", f"origin/{remote_branch}", "--", fname, check=False)
            if result.returncode != 0:
                logger.warning("Could not pull %s: %s", fname, result.stderr.strip())

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

        # Stage everything
        self._git("add", ".")

        # Check if there's anything to commit
        status_result = self._git("status", "--porcelain", check=False)
        staged = [
            line for line in status_result.stdout.strip().splitlines()
            if line.strip()
        ]

        if staged:
            if message is None:
                message = f"espansr: sync {len(staged)} template(s)"
            self._git("commit", "-m", message)

        # Push — determine branch name
        branch_result = self._git("rev-parse", "--abbrev-ref", "HEAD", check=False)
        branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"
        if not branch or branch == "HEAD":
            branch = "main"

        push_result = self._git("push", "-u", "origin", branch, check=False)
        if push_result.returncode != 0:
            stderr = push_result.stderr.strip()
            if "rejected" in stderr or "non-fast-forward" in stderr:
                raise RemoteError(
                    "Push rejected — remote has changes. Run 'espansr pull' first."
                )
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

        # Stage .gitignore too if it exists
        gitignore = self.templates_dir / ".gitignore"
        if gitignore.exists():
            self._git("add", ".gitignore")

        # Stage only the specified files
        for fname in template_files:
            fpath = self.templates_dir / fname
            if fpath.exists():
                self._git("add", fname)

        # Check if anything is staged
        diff_result = self._git("diff", "--cached", "--name-only", check=False)
        if not diff_result.stdout.strip():
            logger.info("Nothing to push for specified templates.")
            return True

        if message is None:
            message = f"espansr: sync {', '.join(template_files)}"
        self._git("commit", "-m", message)

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
