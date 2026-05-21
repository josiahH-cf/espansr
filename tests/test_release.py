"""Tests for release readiness: version strings, --version flag, CHANGELOG, README."""

import subprocess
import sys
from pathlib import Path

from espansr import __version__

ROOT = Path(__file__).resolve().parent.parent


class TestVersionStrings:
    """Version must be consistent in all canonical locations."""

    def test_pyproject_version(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        assert f'version = "{__version__}"' in text

    def test_init_version(self):
        assert __version__  # non-empty

    def test_version_flag(self):
        result = subprocess.run(
            [sys.executable, "-m", "espansr", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert f"espansr {__version__}" in result.stdout


class TestChangelog:
    """CHANGELOG.md must exist and cover all shipped features."""

    def test_changelog_exists(self):
        assert (ROOT / "CHANGELOG.md").is_file()

    def test_changelog_has_version_heading(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        assert f"## [{__version__}]" in text or f"## {__version__}" in text

    def test_changelog_mentions_key_features(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").lower()
        for keyword in ["template import", "variable editor", "validation", "launcher"]:
            assert keyword in text, f"CHANGELOG missing mention of: {keyword}"


class TestReadme:
    """README.md must contain CI badge, platform matrix, and dev commands."""

    def test_readme_ci_badge(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "actions/workflows/ci.yml" in text or "badge" in text.lower()

    def test_readme_platform_matrix(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for platform in ["Linux", "macOS", "Windows", "WSL2"]:
            assert platform in text, f"README missing platform: {platform}"

    def test_readme_links_to_dev_guide(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        assert "docs/DEVELOPMENT.md" in text, "README missing link to Development Guide"

    def test_readme_links_to_supporting_docs(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for path in [
            "docs/CLI.md",
            "docs/TEMPLATES.md",
            "docs/VERIFY.md",
            "docs/DEVELOPMENT.md",
        ]:
            assert path in text, f"README missing link to {path}"

    def test_readme_ends_with_install_meta_prompt(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        stripped = text.rstrip()

        assert "## Cursor Or VS Code Install Prompt" in text
        assert "install espansr from Cursor or VS Code with an open folder" in text
        assert "identify the operating system, shell, and current open folder path" in text
        assert "If the current folder is the espansr repository, use it" in text
        assert "Do not invent a PyPI, pipx, Homebrew, apt, winget" in text
        assert stripped.endswith("```")
        assert stripped.splitlines()[-1] == "```"

    def test_readme_windows_commands_are_powershell_friendly(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        assert ".\\install.ps1" in text
        assert "`./install.ps1`" not in text

    def test_readme_full_suite_installs_dev_extra_first(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")

        dev_extra = '.\\.venv\\Scripts\\python.exe -m pip install -e ".[dev]"'
        pytest_cmd = ".\\.venv\\Scripts\\python.exe -m pytest"

        assert dev_extra in text
        assert text.index(dev_extra) < text.index(pytest_cmd)

    def test_dev_guide_has_commands(self):
        text = (ROOT / "docs" / "DEVELOPMENT.md").read_text(encoding="utf-8")
        for cmd in ["pytest", "ruff check", "black"]:
            assert cmd in text, f"DEVELOPMENT.md missing dev command: {cmd}"
