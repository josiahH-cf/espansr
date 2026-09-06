"""Guards for the suite-wide isolation fixtures in ``tests/conftest.py``.

The suite must never reach the developer's real espansr config directory,
live template store, Espanso service, command shim, or git remote. Each test
here pins one of the autouse guarantees so a regression in the fixtures is
caught by the suite itself rather than by a mutated machine.
"""

import os
from pathlib import Path
from unittest.mock import patch

from espansr.core.platform import get_platform_config
from espansr.core.templates import Template, TemplateManager


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
