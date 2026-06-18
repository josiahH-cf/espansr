"""Tests for the cross-platform `espansr` command shim helper.

Covers ensure_command_shim() and is_user_bin_on_path() in
espansr.core.platform — creation, idempotence, stale-symlink refresh,
non-symlink conflict, force-overwrite, and Windows verify-only branch.
"""

import os
import stat
from pathlib import Path

import pytest


def _reset_platform_cache():
    from espansr.core.platform import get_platform, get_platform_config

    get_platform.cache_clear()
    get_platform_config.cache_clear()


@pytest.fixture(autouse=True)
def _clear_cache():
    _reset_platform_cache()
    yield
    _reset_platform_cache()


def _make_fake_venv(tmp_path: Path, name: str = "espansr") -> Path:
    """Create a fake venv layout and return the executable path."""
    bin_dir = tmp_path / "venv" / "bin"
    bin_dir.mkdir(parents=True)
    exe = bin_dir / name
    exe.write_text("#!/usr/bin/env sh\necho fake\n")
    exe.chmod(0o755)
    return exe


def _assert_shim_points_to_target(shim_path: Path, target: Path) -> None:
    """Assert a shim reaches target, whether symlink or fallback wrapper."""
    assert shim_path.exists()
    if shim_path.is_symlink():
        assert Path(os.readlink(shim_path)).resolve() == target.resolve()
        return

    text = shim_path.read_text(encoding="utf-8")
    assert text == "#!/usr/bin/env sh\n" f'exec "{target}" "$@"\n'


def test_ensure_command_shim_creates_path_visible_shim(tmp_path, monkeypatch):
    from espansr.core import platform as plat
    from espansr.core.platform import ensure_command_shim

    monkeypatch.setattr(plat, "get_platform", lambda: "linux")
    target = _make_fake_venv(tmp_path)
    user_bin = tmp_path / "home" / ".local" / "bin"

    result = ensure_command_shim(target_executable=target, user_bin=user_bin)

    assert result.status == "created"
    assert result.path == user_bin / "espansr"
    _assert_shim_points_to_target(result.path, target)


def test_ensure_command_shim_is_idempotent(tmp_path, monkeypatch):
    from espansr.core import platform as plat
    from espansr.core.platform import ensure_command_shim

    monkeypatch.setattr(plat, "get_platform", lambda: "linux")
    target = _make_fake_venv(tmp_path)
    user_bin = tmp_path / "bin"

    first = ensure_command_shim(target_executable=target, user_bin=user_bin)
    second = ensure_command_shim(target_executable=target, user_bin=user_bin)

    assert first.status == "created"
    assert second.status == "unchanged"


def test_ensure_command_shim_replaces_stale_symlink(tmp_path, monkeypatch):
    from espansr.core import platform as plat
    from espansr.core.platform import ensure_command_shim

    monkeypatch.setattr(plat, "get_platform", lambda: "linux")
    old_target = _make_fake_venv(tmp_path, name="espansr")
    new_root = tmp_path / "newvenv" / "bin"
    new_root.mkdir(parents=True)
    new_target = new_root / "espansr"
    new_target.write_text("#!/usr/bin/env sh\n")
    new_target.chmod(0o755)
    user_bin = tmp_path / "bin"

    ensure_command_shim(target_executable=old_target, user_bin=user_bin)
    result = ensure_command_shim(target_executable=new_target, user_bin=user_bin)

    assert result.status == "updated"
    _assert_shim_points_to_target(result.path, new_target)


def test_ensure_command_shim_conflict_on_regular_file(tmp_path, monkeypatch):
    from espansr.core import platform as plat
    from espansr.core.platform import ensure_command_shim

    monkeypatch.setattr(plat, "get_platform", lambda: "linux")
    target = _make_fake_venv(tmp_path)
    user_bin = tmp_path / "bin"
    user_bin.mkdir()
    blocker = user_bin / "espansr"
    blocker.write_text("user's own script\n")

    result = ensure_command_shim(target_executable=target, user_bin=user_bin)

    assert result.status == "conflict"
    assert blocker.read_text() == "user's own script\n"
    assert not blocker.is_symlink()


def test_ensure_command_shim_force_overwrites_regular_file(tmp_path, monkeypatch):
    from espansr.core import platform as plat
    from espansr.core.platform import ensure_command_shim

    monkeypatch.setattr(plat, "get_platform", lambda: "linux")
    target = _make_fake_venv(tmp_path)
    user_bin = tmp_path / "bin"
    user_bin.mkdir()
    blocker = user_bin / "espansr"
    blocker.write_text("blocker\n")

    result = ensure_command_shim(target_executable=target, user_bin=user_bin, force=True)

    assert result.status == "created"
    _assert_shim_points_to_target(user_bin / "espansr", target)


def test_ensure_command_shim_unavailable_when_target_missing(tmp_path, monkeypatch):
    from espansr.core import platform as plat
    from espansr.core.platform import ensure_command_shim

    monkeypatch.setattr(plat, "get_platform", lambda: "linux")
    # No target supplied and the running venv has no `espansr` we should find
    # in tmp_path; force discovery into an empty dir.
    fake_venv_bin = tmp_path / "empty_venv" / "bin"
    fake_venv_bin.mkdir(parents=True)
    monkeypatch.setattr(plat, "get_venv_bin_dir", lambda: fake_venv_bin)
    user_bin = tmp_path / "bin"

    result = ensure_command_shim(user_bin=user_bin)

    assert result.status == "unavailable"


def test_is_user_bin_on_path_detects_entry(tmp_path, monkeypatch):
    from espansr.core import platform as plat
    from espansr.core.platform import is_user_bin_on_path

    monkeypatch.setattr(plat, "get_platform", lambda: "linux")
    user_bin = tmp_path / "bin"
    user_bin.mkdir()

    env_with = {"PATH": f"/usr/bin:{user_bin}:/bin"}
    env_without = {"PATH": "/usr/bin:/bin"}

    assert is_user_bin_on_path(user_bin, env=env_with) is True
    assert is_user_bin_on_path(user_bin, env=env_without) is False


def test_ensure_command_shim_windows_verify_only(tmp_path, monkeypatch):
    from espansr.core import platform as plat
    from espansr.core.platform import ensure_command_shim

    monkeypatch.setattr(plat, "get_platform", lambda: "windows")
    venv_bin = tmp_path / "venv" / "Scripts"
    venv_bin.mkdir(parents=True)
    target = venv_bin / "espansr.exe"
    target.write_text("")
    monkeypatch.setattr(plat, "get_venv_bin_dir", lambda: venv_bin)

    # Not on PATH → skipped.
    monkeypatch.setenv("PATH", "C:\\Windows;C:\\Windows\\System32")
    result = ensure_command_shim()
    assert result.status == "skipped"

    # On PATH → unchanged (verify-only, no mutation).
    monkeypatch.setenv("PATH", f"C:\\Windows;{venv_bin}")
    result = ensure_command_shim()
    assert result.status == "unchanged"


def test_ensure_command_shim_wrapper_fallback(tmp_path, monkeypatch):
    """When symlink creation raises OSError, fall back to a wrapper script."""
    from espansr.core import platform as plat
    from espansr.core.platform import ensure_command_shim

    monkeypatch.setattr(plat, "get_platform", lambda: "linux")
    target = _make_fake_venv(tmp_path)
    user_bin = tmp_path / "bin"

    original_symlink_to = Path.symlink_to

    def fail_symlink(self, *_args, **_kwargs):
        raise OSError("symlinks unsupported")

    monkeypatch.setattr(Path, "symlink_to", fail_symlink)
    try:
        result = ensure_command_shim(target_executable=target, user_bin=user_bin)
    finally:
        monkeypatch.setattr(Path, "symlink_to", original_symlink_to)

    assert result.status == "created"
    shim = user_bin / "espansr"
    assert shim.exists()
    assert not shim.is_symlink()
    assert str(target) in shim.read_text()
    mode = shim.stat().st_mode
    if os.name != "nt":
        assert mode & stat.S_IXUSR
