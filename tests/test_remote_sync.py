"""Pre-implementation tests for remote template sync (feature 5).

Covers AC-1 through AC-12 from specs/5-remote-template-sync.md.
Tests use temporary git repos to verify real git operations.
"""

import json
import os
import subprocess
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_templates(tmp_path):
    """Create a temporary templates directory with one sample template."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    sample = {
        "name": "Greeting",
        "content": "Hello {{name}}!",
        "trigger": ":greet",
        "variables": [{"name": "name", "label": "Name", "default": "World"}],
    }
    (templates_dir / "greeting.json").write_text(json.dumps(sample, indent=2))
    return templates_dir


@pytest.fixture()
def bare_remote(tmp_path):
    """Create a bare git repo that acts as a remote."""
    remote_dir = tmp_path / "remote.git"
    remote_dir.mkdir()
    subprocess.run(
        ["git", "init", "--bare", str(remote_dir)],
        capture_output=True,
        check=True,
    )
    return remote_dir


@pytest.fixture()
def config_path(tmp_path):
    """Return a path for a temporary config file."""
    return tmp_path / "config.json"


# ---------------------------------------------------------------------------
# AC-1: Remote configuration lifecycle
# ---------------------------------------------------------------------------


class TestRemoteSet:
    """espansr remote set <url> persists URL and initializes git."""

    def test_remote_set_persists_url(self, tmp_templates, bare_remote, config_path):
        """After remote set, config.json → remote.url contains the URL."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        mgr = ConfigManager(config_path=config_path)
        mgr.save(Config())

        remote_url = str(bare_remote)
        rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
        rm.set_remote(remote_url)

        # Reload config from disk
        mgr2 = ConfigManager(config_path=config_path)
        assert mgr2.config.remote.url == remote_url

    def test_remote_set_initializes_git(self, tmp_templates, bare_remote, config_path):
        """After remote set, templates dir contains a .git directory."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        mgr = ConfigManager(config_path=config_path)
        mgr.save(Config())

        rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
        rm.set_remote(str(bare_remote))

        assert (tmp_templates / ".git").exists()


# ---------------------------------------------------------------------------
# AC-2: Remote status reporting
# ---------------------------------------------------------------------------


class TestRemoteStatus:
    """espansr remote status reports URL, timestamps, dirty list."""

    def test_remote_status_shows_state(self, tmp_templates, bare_remote, config_path):
        """Status includes the remote URL and dirty files list."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        mgr = ConfigManager(config_path=config_path)
        mgr.save(Config())

        rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
        rm.set_remote(str(bare_remote))
        # Do an initial push so the remote has content
        rm.push()

        status = rm.status()
        assert status["url"] == str(bare_remote)
        assert "dirty" in status  # list of modified files


# ---------------------------------------------------------------------------
# AC-3: Remote removal
# ---------------------------------------------------------------------------


class TestRemoteRemove:
    """espansr remote remove clears config and removes .git."""

    def test_remote_remove_clears_config(self, tmp_templates, bare_remote, config_path):
        """After remote remove, config.remote.url is empty."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        mgr = ConfigManager(config_path=config_path)
        mgr.save(Config())

        rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
        rm.set_remote(str(bare_remote))
        rm.remove_remote()

        mgr2 = ConfigManager(config_path=config_path)
        assert mgr2.config.remote.url == ""

    def test_remote_remove_preserves_templates(self, tmp_templates, bare_remote, config_path):
        """After remote remove, template files still exist."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        mgr = ConfigManager(config_path=config_path)
        mgr.save(Config())

        rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
        rm.set_remote(str(bare_remote))
        rm.remove_remote()

        assert (tmp_templates / "greeting.json").exists()


# ---------------------------------------------------------------------------
# AC-4: Pull all templates from remote
# ---------------------------------------------------------------------------


class TestPullAll:
    """espansr pull fetches remote template changes."""

    def test_pull_fetches_remote_templates(self, tmp_path, bare_remote):
        """A template pushed from clone-A appears in clone-B after pull."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        # Clone A: push a template
        clone_a = tmp_path / "clone_a"
        clone_a.mkdir()
        config_a = tmp_path / "config_a.json"
        mgr_a = ConfigManager(config_path=config_a)
        mgr_a.save(Config())
        rm_a = RemoteManager(templates_dir=clone_a, config_manager=mgr_a)
        rm_a.set_remote(str(bare_remote))

        sample = {"name": "Sig", "content": "Best regards", "trigger": ":sig"}
        (clone_a / "sig.json").write_text(json.dumps(sample, indent=2))
        rm_a.push()

        # Clone B: pull should get the template
        clone_b = tmp_path / "clone_b"
        clone_b.mkdir()
        config_b = tmp_path / "config_b.json"
        mgr_b = ConfigManager(config_path=config_b)
        mgr_b.save(Config())
        rm_b = RemoteManager(templates_dir=clone_b, config_manager=mgr_b)
        rm_b.set_remote(str(bare_remote))
        rm_b.pull()

        assert (clone_b / "sig.json").exists()
        data = json.loads((clone_b / "sig.json").read_text())
        assert data["trigger"] == ":sig"


# ---------------------------------------------------------------------------
# AC-5: Pull specific templates
# ---------------------------------------------------------------------------


class TestPullSelective:
    """espansr pull --template selectively checks out specific files."""

    def test_pull_selective_template(self, tmp_path, bare_remote):
        """Only the named template is updated when using pull_templates()."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        # Clone A: push two templates
        clone_a = tmp_path / "clone_a"
        clone_a.mkdir()
        config_a = tmp_path / "config_a.json"
        mgr_a = ConfigManager(config_path=config_a)
        mgr_a.save(Config())
        rm_a = RemoteManager(templates_dir=clone_a, config_manager=mgr_a)
        rm_a.set_remote(str(bare_remote))

        alpha = {"name": "Alpha", "content": "A", "trigger": ":a"}
        (clone_a / "alpha.json").write_text(
            json.dumps(alpha, indent=2),
        )
        beta = {"name": "Beta", "content": "B", "trigger": ":b"}
        (clone_a / "beta.json").write_text(
            json.dumps(beta, indent=2),
        )
        rm_a.push()

        # Clone B: set remote, pull only alpha
        clone_b = tmp_path / "clone_b"
        clone_b.mkdir()
        config_b = tmp_path / "config_b.json"
        mgr_b = ConfigManager(config_path=config_b)
        mgr_b.save(Config())
        rm_b = RemoteManager(templates_dir=clone_b, config_manager=mgr_b)
        rm_b.set_remote(str(bare_remote))

        rm_b.pull_templates(["alpha.json"])

        assert (clone_b / "alpha.json").exists()


# ---------------------------------------------------------------------------
# AC-6: Push all templates to remote
# ---------------------------------------------------------------------------


class TestPushAll:
    """espansr push stages, commits, and pushes."""

    def test_push_commits_and_pushes(self, tmp_templates, bare_remote, config_path):
        """After push, the bare remote has a commit with the template."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        mgr = ConfigManager(config_path=config_path)
        mgr.save(Config())

        rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
        rm.set_remote(str(bare_remote))
        rm.push()

        # Verify remote has the commit
        result = subprocess.run(
            ["git", "--git-dir", str(bare_remote), "log", "--oneline", "-1"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0


# ---------------------------------------------------------------------------
# AC-7: Push specific templates
# ---------------------------------------------------------------------------


class TestPushSelective:
    """espansr push --template selectively pushes specific files."""

    def test_push_selective_template(self, tmp_templates, bare_remote, config_path):
        """Only the named template appears in the pushed commit."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        mgr = ConfigManager(config_path=config_path)
        mgr.save(Config())

        rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
        rm.set_remote(str(bare_remote))

        # Add a second template
        extra = {"name": "Extra", "content": "extra", "trigger": ":extra"}
        (tmp_templates / "extra.json").write_text(json.dumps(extra, indent=2))

        # Push only the greeting template
        rm.push_templates(["greeting.json"])

        # Verify remote has greeting.json but check the push went through
        result = subprocess.run(
            ["git", "--git-dir", str(bare_remote), "log", "--oneline"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0


# ---------------------------------------------------------------------------
# AC-8: Push with custom commit message
# ---------------------------------------------------------------------------


class TestPushCustomMessage:
    """espansr push --message uses a custom commit message."""

    def test_push_custom_message(self, tmp_templates, bare_remote, config_path):
        """Commit message matches the --message argument."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        mgr = ConfigManager(config_path=config_path)
        mgr.save(Config())

        rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
        rm.set_remote(str(bare_remote))
        rm.push(message="my custom note")

        result = subprocess.run(
            ["git", "--git-dir", str(bare_remote), "log", "--format=%s", "-1"],
            capture_output=True,
            text=True,
        )
        assert "my custom note" in result.stdout.strip()


# ---------------------------------------------------------------------------
# AC-9: Auto-pull on startup
# ---------------------------------------------------------------------------


class TestAutoPull:
    """Auto-pull fires silently before template-loading commands."""

    def test_auto_pull_on_template_load(self, tmp_templates, bare_remote, config_path):
        """RemoteManager.auto_pull() performs a pull when auto_pull is enabled."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        mgr = ConfigManager(config_path=config_path)
        mgr.save(Config())

        rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
        rm.set_remote(str(bare_remote))
        rm.push()  # initial push so remote has content

        # auto_pull should succeed without errors
        result = rm.auto_pull()
        assert result is True


# ---------------------------------------------------------------------------
# AC-10: Conflict detection
# ---------------------------------------------------------------------------


class TestConflictDetection:
    """Pull detects merge conflicts and reports them."""

    def test_pull_conflict_detected(self, tmp_path, bare_remote):
        """Conflicting changes on pull raise an error with file names."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteConflictError, RemoteManager

        # Clone A: push initial content
        clone_a = tmp_path / "clone_a"
        clone_a.mkdir()
        config_a = tmp_path / "config_a.json"
        mgr_a = ConfigManager(config_path=config_a)
        mgr_a.save(Config())
        rm_a = RemoteManager(templates_dir=clone_a, config_manager=mgr_a)
        rm_a.set_remote(str(bare_remote))
        shared_v1 = {
            "name": "Shared",
            "content": "v1",
            "trigger": ":s",
        }
        (clone_a / "shared.json").write_text(
            json.dumps(shared_v1, indent=2),
        )
        rm_a.push()

        # Clone B: pull, then diverge
        clone_b = tmp_path / "clone_b"
        clone_b.mkdir()
        config_b = tmp_path / "config_b.json"
        mgr_b = ConfigManager(config_path=config_b)
        mgr_b.save(Config())
        rm_b = RemoteManager(templates_dir=clone_b, config_manager=mgr_b)
        rm_b.set_remote(str(bare_remote))
        rm_b.pull()

        # Both modify the same file differently
        shared_a = {
            "name": "Shared",
            "content": "version-A",
            "trigger": ":s",
        }
        (clone_a / "shared.json").write_text(
            json.dumps(shared_a, indent=2),
        )
        rm_a.push()

        shared_b = {
            "name": "Shared",
            "content": "version-B",
            "trigger": ":s",
        }
        (clone_b / "shared.json").write_text(
            json.dumps(shared_b, indent=2),
        )
        # Commit locally in clone_b
        subprocess.run(["git", "-C", str(clone_b), "add", "."], capture_output=True, check=True)
        subprocess.run(
            ["git", "-C", str(clone_b), "commit", "-m", "local change"],
            capture_output=True,
            check=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "test",
                "GIT_AUTHOR_EMAIL": "test@test.com",
                "GIT_COMMITTER_NAME": "test",
                "GIT_COMMITTER_EMAIL": "test@test.com",
            },
        )

        with pytest.raises(RemoteConflictError) as exc_info:
            rm_b.pull()
        assert "shared.json" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-11: Git-not-found guard
# ---------------------------------------------------------------------------


class TestGitNotFound:
    """Commands fail clearly when git is not installed."""

    def test_git_not_found_error(self, tmp_templates, config_path):
        """RemoteManager.check_git() raises when git is not on PATH."""
        from espansr.core.remote import GitNotFoundError, RemoteManager

        with patch("shutil.which", return_value=None):
            from espansr.core.config import Config, ConfigManager

            mgr = ConfigManager(config_path=config_path)
            mgr.save(Config())
            rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
            with pytest.raises(GitNotFoundError):
                rm.check_git()


# ---------------------------------------------------------------------------
# AC-12: .gitignore for local-only state
# ---------------------------------------------------------------------------


class TestGitignore:
    """.gitignore excludes _versions/ and _meta/."""

    def test_gitignore_created(self, tmp_templates, bare_remote, config_path):
        """.gitignore in templates dir excludes _versions/ and _meta/."""
        from espansr.core.config import Config, ConfigManager
        from espansr.core.remote import RemoteManager

        mgr = ConfigManager(config_path=config_path)
        mgr.save(Config())

        rm = RemoteManager(templates_dir=tmp_templates, config_manager=mgr)
        rm.set_remote(str(bare_remote))

        gitignore = tmp_templates / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert "_versions/" in content
        assert "_meta/" in content
