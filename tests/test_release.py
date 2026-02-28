"""Tests for v1.0 release readiness: version strings, --version flag, CHANGELOG, README."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestVersionStrings:
    """Version must be 1.0.0 in all canonical locations."""

    def test_pyproject_version(self):
        text = (ROOT / "pyproject.toml").read_text()
        assert 'version = "1.0.0"' in text

    def test_init_version(self):
        from espansr import __version__

        assert __version__ == "1.0.0"

    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, "-m", "espansr", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "espansr 1.0.0" in result.stdout


class TestChangelog:
    """CHANGELOG.md must exist and cover all shipped features."""

    def test_changelog_exists(self):
        assert (ROOT / "CHANGELOG.md").is_file()

    def test_changelog_has_version_heading(self):
        text = (ROOT / "CHANGELOG.md").read_text()
        assert "## [1.0.0]" in text or "## 1.0.0" in text

    def test_changelog_mentions_key_features(self):
        text = (ROOT / "CHANGELOG.md").read_text().lower()
        for keyword in ["template import", "variable editor", "validation", "launcher"]:
            assert keyword in text, f"CHANGELOG missing mention of: {keyword}"


class TestReadme:
    """README.md must contain CI badge, platform matrix, and dev commands."""

    def test_readme_ci_badge(self):
        text = (ROOT / "README.md").read_text()
        assert "actions/workflows/ci.yml" in text or "badge" in text.lower()

    def test_readme_platform_matrix(self):
        text = (ROOT / "README.md").read_text()
        for platform in ["Linux", "macOS", "Windows", "WSL2"]:
            assert platform in text, f"README missing platform: {platform}"

    def test_readme_dev_section(self):
        text = (ROOT / "README.md").read_text()
        for cmd in ["pytest", "ruff check", "black"]:
            assert cmd in text, f"README missing dev command: {cmd}"
