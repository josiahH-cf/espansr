"""Guards for the suite-wide isolation fixtures in ``tests/conftest.py``.

The suite must never reach the developer's real espansr config directory,
live template store, Espanso service, command shim, or git remote. Each test
here pins one of the autouse guarantees so a regression in the fixtures is
caught by the suite itself rather than by a mutated machine.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from espansr.core.platform import get_platform_config
from espansr.core.templates import Template, TemplateManager

ROOT = Path(__file__).resolve().parents[1]


def _run_temp_probe(tmp_path, *, explicit=False):
    """Exercise real pytest startup and teardown without its shared temp tree."""
    suite = tmp_path / "probe"
    tests = suite / "tests"
    tests.mkdir(parents=True)
    shutil.copyfile(ROOT / "tests/conftest.py", tests / "conftest.py")
    (tests / "test_temp.py").write_text(
        "from pathlib import Path\n"
        "def test_temp(tmp_path_factory, tmp_path):\n"
        "    root = Path(__file__).resolve().parents[1]\n"
        "    base = tmp_path_factory.getbasetemp()\n"
        "    assert base.is_relative_to(root)\n"
        "    (base / 'keep.txt').write_text('retained')\n"
        "    with (root / 'observed.txt').open('a') as out:\n"
        "        out.write(str(base) + '\\n')\n",
        encoding="utf-8",
    )
    # A shared temp parent that cannot contain directories makes accidental
    # fallback fail on every platform, without altering any real permissions.
    shared = tmp_path / "shared-temp-file"
    shared.write_text("preserve shared bytes", encoding="utf-8")
    scratch = suite / ".tmp_pytest"
    scratch.mkdir()
    sentinel = scratch / "unrelated.txt"
    sentinel.write_text("preserve earlier work", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in {"PYTEST_ADDOPTS", "PYTHONPATH"}}
    env.update(PYTHONPATH=str(ROOT), PYTEST_DEBUG_TEMPROOT=str(shared))
    argv = [sys.executable, "-m", "pytest", "-q", "tests"]
    if explicit:
        argv += ["--basetemp", str(suite / "chosen-temp")]
    for _ in range(1 if explicit else 2):
        result = subprocess.run(
            argv, cwd=suite, env=env, capture_output=True, text=True, timeout=60
        )
        assert result.returncode == 0, result.stdout + result.stderr
    assert shared.read_text(encoding="utf-8") == "preserve shared bytes"
    assert sentinel.read_text(encoding="utf-8") == "preserve earlier work"
    bases = [Path(p) for p in (suite / "observed.txt").read_text().splitlines()]
    assert all((p / "keep.txt").read_text() == "retained" for p in bases)
    return suite, bases


def test_plain_pytest_uses_distinct_owned_temp_roots(tmp_path):
    suite, bases = _run_temp_probe(tmp_path)
    assert len(set(bases)) == 2
    assert all(p.parent == suite / ".tmp_pytest" for p in bases)


def test_pytest_preserves_explicit_basetemp(tmp_path):
    suite, bases = _run_temp_probe(tmp_path, explicit=True)
    assert bases == [suite / "chosen-temp"]


def test_config_dir_resolves_under_tmp_path(tmp_path):
    """The platform config dir, config dir, and template store live in tmp_path."""
    from espansr.core.config import get_config_dir, get_templates_dir

    assert get_platform_config().espansr_config_dir.is_relative_to(tmp_path)
    assert get_config_dir().is_relative_to(tmp_path)
    assert get_templates_dir().is_relative_to(tmp_path)


def test_isolated_env_matches_process_environment(isolated_config_env, tmp_path):
    """The overrides handed to subprocess tests are the ones set in-process."""
    assert isolated_config_env
    for key, value in isolated_config_env.items():
        assert os.environ[key] == value
        assert Path(value).is_relative_to(tmp_path)


def test_process_singletons_start_fresh_each_test(tmp_path):
    """The global ConfigManager / TemplateManager resolve under this test's tmp_path."""
    from espansr.core.config import get_config_manager
    from espansr.core.templates import get_template_manager

    assert get_config_manager().config_path.is_relative_to(tmp_path)
    assert get_template_manager().templates_dir.is_relative_to(tmp_path)


def test_cli_auto_pull_is_disabled():
    """CLI handlers never construct a RemoteManager for their startup auto-pull."""
    import espansr.__main__ as cli

    with patch("espansr.core.remote.RemoteManager", side_effect=AssertionError("auto-pull ran")):
        cli._auto_pull_if_configured()
        assert cli.cmd_list(None) == 0


def test_wsl2_espanso_restart_is_stubbed():
    """The WSL2 restart path never spawns powershell.exe during tests."""
    from espansr.integrations import espanso

    with patch("subprocess.run", side_effect=AssertionError("real service restart")):
        espanso._restart_espanso_wsl2()


def test_command_shim_helpers_are_stubbed(tmp_path):
    """The shim helpers resolve to tmp_path so no real ~/.local/bin entry can change."""
    from espansr.core import platform as plat

    result = plat.ensure_command_shim()
    assert result.status == "unchanged"
    assert result.path.is_relative_to(tmp_path)
    assert plat.get_user_bin_dir().is_relative_to(tmp_path)
    assert plat.is_user_bin_on_path() is True


def test_template_manager_creates_versions_dir_only_on_write(tmp_path):
    """Opening a manager (and reading history) leaves no _versions/ behind."""
    store = tmp_path / "store"
    manager = TemplateManager(templates_dir=store)
    template = Template(name="Lazy", content="body")
    assert manager.save(template)

    assert manager.list_versions(template) == []
    assert manager.get_version(template, 1) is None
    assert not (store / "_versions").exists()

    assert manager.create_version(template, note="first") is not None
    assert (store / "_versions" / "lazy" / "v1.json").exists()
    assert [v.version for v in manager.list_versions(template)] == [1]
