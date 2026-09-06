"""Tests for the espansr-managed block in Espanso's ``config/default.yml``.

Covers apply/idempotency/revert semantics of ``apply_remote_desktop_config``
and ``apply_workstation_config`` in ``espansr.integrations.espanso``: the file
is edited as text (one marked block, every other byte preserved), prior
values of managed keys are recorded and restored, the original is backed up
once, the legacy first-line-marker layout migrates, and a missing file is
created.
"""

from pathlib import Path
from unittest.mock import patch

import yaml

from espansr.integrations import espanso

USER_CONFIG = (
    "# Espanso config, hand-edited\n"
    "toggle_key: OFF\n"
    "search_shortcut: ALT+SPACE  # keep this comment\n"
    "\n"
    "meeting_reminder: '12:30'\n"
    "backend: Inject\n"
    "show_icon: true\n"
)


def _cfg_dir(tmp_path: Path) -> Path:
    """Create and return a fake Espanso config dir (with config/ subdir)."""
    d = tmp_path / "espanso"
    (d / "config").mkdir(parents=True)
    return d


def _default_yml(cfg_dir: Path) -> Path:
    return cfg_dir / "config" / "default.yml"


def _backup(cfg_dir: Path) -> Path:
    return cfg_dir / "config" / "default.yml.espansr-orig"


def _outside_block(text: str) -> str:
    """Return the file text with the espansr-managed block removed."""
    lines = text.splitlines(keepends=True)
    kept = []
    inside = False
    for line in lines:
        if line.startswith(espanso.MANAGED_BLOCK_BEGIN_PREFIX):
            inside = True
            continue
        if inside and line.strip() == espanso.MANAGED_BLOCK_END:
            inside = False
            continue
        if not inside:
            kept.append(line)
    return "".join(kept)


def _top_level_keys(text: str) -> list[str]:
    keys = []
    for line in text.splitlines():
        key = espanso._parse_top_level_key(line)
        if key is not None:
            keys.append(key)
    return keys


def _apply_host(cfg: Path, **kwargs) -> bool:
    with patch.object(espanso, "restart_espanso", return_value=True):
        return espanso.apply_remote_desktop_config(config_dir=cfg, **kwargs)


def _apply_workstation(cfg: Path) -> bool:
    with patch.object(espanso, "restart_espanso", return_value=True):
        return espanso.apply_workstation_config(config_dir=cfg)


# ─── apply ────────────────────────────────────────────────────────────────────


def test_apply_writes_remote_desktop_keys(tmp_path):
    cfg = _cfg_dir(tmp_path)
    assert _apply_host(cfg) is True

    text = _default_yml(cfg).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data["win32_exclude_orphan_events"] is False
    assert data["backend"] == "Clipboard"
    # With the clipboard backend, disabling the clipboard restore prevents the
    # paste-race that otherwise emits previously-copied text instead of the
    # expansion in apps that paste asynchronously.
    assert data["preserve_clipboard"] is False
    assert data["show_icon"] is False
    assert data["show_notifications"] is False
    assert data["key_delay"] == 30
    assert data["backspace_delay"] == 30
    assert espanso.REMOTE_DESKTOP_MARKER in text
    assert text.rstrip("\n").endswith(espanso.MANAGED_BLOCK_END)


def test_begin_line_carries_reapply_and_revert_hint(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _apply_host(cfg)
    text = _default_yml(cfg).read_text(encoding="utf-8")
    begin = next(line for line in text.splitlines() if line.startswith("# espansr-managed BEGIN"))
    assert begin.startswith("# espansr-managed BEGIN (host)")
    assert "espansr configure-remote-desktop --revert" in begin


def test_apply_creates_missing_file_with_only_the_block(tmp_path):
    cfg = _cfg_dir(tmp_path)
    assert not _default_yml(cfg).exists()
    assert _apply_workstation(cfg) is True

    text = _default_yml(cfg).read_text(encoding="utf-8")
    assert text.startswith(espanso.WORKSTATION_MARKER)
    assert _outside_block(text) == ""
    assert yaml.safe_load(text) == espanso._WORKSTATION_KEYS
    assert not _backup(cfg).exists()  # nothing to back up


def test_apply_preserves_everything_outside_the_block_byte_for_byte(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(USER_CONFIG, encoding="utf-8")
    _apply_host(cfg)

    text = _default_yml(cfg).read_text(encoding="utf-8")
    # The two user lines espansr manages moved into the block; everything else
    # (comments, blank line, `OFF`, the quoted time) is untouched.
    expected_outside = USER_CONFIG.replace("backend: Inject\n", "").replace("show_icon: true\n", "")
    assert _outside_block(text) == expected_outside
    assert "toggle_key: OFF\n" in text
    assert "meeting_reminder: '12:30'\n" in text
    assert "# keep this comment" in text
    assert "# espansr-prev: backend: Inject\n" in text
    assert "# espansr-prev: show_icon: true\n" in text


def test_apply_leaves_no_duplicate_top_level_keys(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(USER_CONFIG, encoding="utf-8")
    _apply_host(cfg)

    keys = _top_level_keys(_default_yml(cfg).read_text(encoding="utf-8"))
    assert len(keys) == len(set(keys)), keys
    data = yaml.safe_load(_default_yml(cfg).read_text(encoding="utf-8"))
    assert data["backend"] == "Clipboard"
    assert data["show_icon"] is False


def test_apply_result_still_parses_as_yaml_mapping(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(USER_CONFIG, encoding="utf-8")
    _apply_host(cfg)
    data = yaml.safe_load(_default_yml(cfg).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert data["search_shortcut"] == "ALT+SPACE"
    assert data["meeting_reminder"] == "12:30"


def test_apply_is_idempotent(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(USER_CONFIG, encoding="utf-8")
    _apply_host(cfg)
    first = _default_yml(cfg).read_text(encoding="utf-8")
    _apply_host(cfg)
    second = _default_yml(cfg).read_text(encoding="utf-8")
    assert first == second
    assert first.count(espanso.MANAGED_BLOCK_END) == 1


def test_apply_preserves_crlf_line_endings(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_bytes(b"toggle_key: OFF\r\nbackend: Inject\r\n")
    _apply_host(cfg)
    raw = _default_yml(cfg).read_bytes()
    assert b"toggle_key: OFF\r\n" in raw
    assert b"# espansr-prev: backend: Inject\r\n" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")


def test_apply_adds_missing_trailing_newline_before_block(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text("toggle_key: OFF", encoding="utf-8")
    _apply_host(cfg)
    text = _default_yml(cfg).read_text(encoding="utf-8")
    assert text.startswith("toggle_key: OFF\n# espansr-managed BEGIN (host)")


def test_apply_returns_false_without_espanso(tmp_path):
    with patch.object(espanso, "get_espanso_config_dir", return_value=None):
        assert espanso.apply_remote_desktop_config() is False
        assert espanso.apply_workstation_config() is False


# ─── backup ───────────────────────────────────────────────────────────────────


def test_original_backed_up_exactly_once(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(USER_CONFIG, encoding="utf-8")

    _apply_host(cfg)
    assert _backup(cfg).read_text(encoding="utf-8") == USER_CONFIG

    # Later modifications (re-apply, mode switch, hand edits) never overwrite it.
    _apply_workstation(cfg)
    _apply_host(cfg)
    assert _backup(cfg).read_text(encoding="utf-8") == USER_CONFIG

    _apply_host(cfg, revert=True)
    _default_yml(cfg).write_text("toggle_key: ALT\n", encoding="utf-8")
    _apply_host(cfg)
    assert _backup(cfg).read_text(encoding="utf-8") == USER_CONFIG


def test_invalid_yaml_is_preserved_and_backed_up(tmp_path):
    cfg = _cfg_dir(tmp_path)
    # A bare scalar is valid YAML but not a mapping Espanso could use; espansr
    # keeps it verbatim (plus its backup) instead of replacing the file.
    _default_yml(cfg).write_text("just a plain scalar, not a mapping\n", encoding="utf-8")
    assert _apply_host(cfg) is True

    text = _default_yml(cfg).read_text(encoding="utf-8")
    assert text.startswith("just a plain scalar, not a mapping\n# espansr-managed BEGIN")
    assert _backup(cfg).read_text(encoding="utf-8") == "just a plain scalar, not a mapping\n"


# ─── revert ───────────────────────────────────────────────────────────────────


def test_revert_restores_prior_values_and_removes_managed_keys(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(USER_CONFIG, encoding="utf-8")
    _apply_host(cfg)
    assert _apply_host(cfg, revert=True) is True

    text = _default_yml(cfg).read_text(encoding="utf-8")
    assert "espansr" not in text
    assert sorted(text.splitlines()) == sorted(USER_CONFIG.splitlines())
    data = yaml.safe_load(text)
    assert data["backend"] == "Inject"
    assert data["show_icon"] is True
    for key in espanso._REMOTE_DESKTOP_KEYS:
        if key not in ("backend", "show_icon"):
            assert key not in data


def test_revert_removes_workstation_keys(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text("toggle_key: ALT\n", encoding="utf-8")
    _apply_workstation(cfg)
    assert _apply_host(cfg, revert=True) is True

    text = _default_yml(cfg).read_text(encoding="utf-8")
    assert text == "toggle_key: ALT\n"
    for key in espanso._WORKSTATION_KEYS:
        assert key not in text


def test_revert_deletes_file_when_espansr_created_it(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _apply_host(cfg)
    _apply_host(cfg, revert=True)
    assert not _default_yml(cfg).exists()


def test_revert_is_a_noop_without_managed_block(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(USER_CONFIG, encoding="utf-8")
    assert _apply_host(cfg, revert=True) is True
    assert _default_yml(cfg).read_text(encoding="utf-8") == USER_CONFIG
    assert not _backup(cfg).exists()


def test_revert_without_file_succeeds(tmp_path):
    cfg = _cfg_dir(tmp_path)
    assert _apply_host(cfg, revert=True) is True


def test_revert_discards_edits_made_inside_the_block(tmp_path):
    """The block is espansr's; a value edited inside it is replaced by the
    recorded original on revert, never merged."""
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text("backend: Inject\n", encoding="utf-8")
    _apply_host(cfg)
    path = _default_yml(cfg)
    path.write_text(
        path.read_text(encoding="utf-8").replace("backend: Clipboard", "backend: Auto"),
        encoding="utf-8",
    )
    _apply_host(cfg, revert=True)
    assert path.read_text(encoding="utf-8") == "backend: Inject\n"


# ─── switching modes ──────────────────────────────────────────────────────────


def test_workstation_replaces_host_block_and_restores_unmanaged_originals(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(USER_CONFIG, encoding="utf-8")
    _apply_host(cfg)
    _apply_workstation(cfg)

    text = _default_yml(cfg).read_text(encoding="utf-8")
    assert text.count(espanso.MANAGED_BLOCK_BEGIN_PREFIX) == 1
    assert espanso.WORKSTATION_MARKER in text
    assert espanso.REMOTE_DESKTOP_MARKER not in text
    data = yaml.safe_load(text)
    assert data["toggle_key"] is False  # PyYAML's reading of the untouched `OFF`
    assert "toggle_key: OFF\n" in text
    assert data["preserve_clipboard"] is True
    assert data["restore_clipboard_delay"] == 1500
    assert data["win32_exclude_orphan_events"] is False
    # backend is not a workstation key: the user's original line is back in the body.
    assert data["backend"] == "Inject"
    assert "# espansr-prev: backend" not in text
    keys = _top_level_keys(text)
    assert len(keys) == len(set(keys))


def test_apply_workstation_config_preserves_clipboard(tmp_path):
    cfg = _cfg_dir(tmp_path)
    assert _apply_workstation(cfg) is True

    text = _default_yml(cfg).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert data["preserve_clipboard"] is True
    assert data["restore_clipboard_delay"] == 1500
    assert data["win32_exclude_orphan_events"] is False
    assert espanso.WORKSTATION_MARKER in text


# ─── legacy layout migration ──────────────────────────────────────────────────

LEGACY_WORKSTATION = (
    "# espansr-workstation — managed by espansr; "
    "reapply with: espansr configure-remote-desktop --local\n"
    "toggle_key: ALT\n"
    "win32_exclude_orphan_events: false\n"
    "preserve_clipboard: true\n"
    "restore_clipboard_delay: 1500\n"
)
LEGACY_HOST = (
    "# espansr-remote-desktop — managed by espansr; "
    "revert with: espansr configure-remote-desktop --revert\n"
    "toggle_key: ALT\n"
    "win32_exclude_orphan_events: false\n"
    "backend: Inject\n"
    "preserve_clipboard: false\n"
    "show_icon: false\n"
    "show_notifications: false\n"
    "key_delay: 30\n"
    "backspace_delay: 30\n"
)


def test_legacy_layout_is_detected(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(LEGACY_WORKSTATION, encoding="utf-8")
    assert espanso.get_managed_default_config_mode(config_dir=cfg) == "workstation"
    assert espanso.default_config_has_remote_desktop_marker(config_dir=cfg) is False
    _default_yml(cfg).write_text(LEGACY_HOST, encoding="utf-8")
    assert espanso.get_managed_default_config_mode(config_dir=cfg) == "host"
    assert espanso.default_config_has_remote_desktop_marker(config_dir=cfg) is True


def test_legacy_layout_migrates_to_block_on_apply(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(LEGACY_WORKSTATION, encoding="utf-8")
    _apply_host(cfg)

    text = _default_yml(cfg).read_text(encoding="utf-8")
    assert "espansr-workstation" not in text
    assert text.startswith("toggle_key: ALT\n# espansr-managed BEGIN (host)")
    keys = _top_level_keys(text)
    assert len(keys) == len(set(keys)), keys
    data = yaml.safe_load(text)
    assert data["toggle_key"] == "ALT"
    assert data["preserve_clipboard"] is False
    assert data["backend"] == "Clipboard"
    assert "restore_clipboard_delay" not in data
    # A legacy file already carried an espansr marker, so it is not an original.
    assert not _backup(cfg).exists()


def test_legacy_layout_reverts_both_modes(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(LEGACY_WORKSTATION, encoding="utf-8")
    assert _apply_host(cfg, revert=True) is True
    assert _default_yml(cfg).read_text(encoding="utf-8") == "toggle_key: ALT\n"

    _default_yml(cfg).write_text(LEGACY_HOST, encoding="utf-8")
    assert _apply_host(cfg, revert=True) is True
    # The old layout recorded nothing, so a value the user changed after the
    # old apply (backend: Inject) is kept; espansr's own values are removed.
    assert _default_yml(cfg).read_text(encoding="utf-8") == "toggle_key: ALT\nbackend: Inject\n"


# ─── detection helpers ────────────────────────────────────────────────────────


def test_default_config_marker_detection(tmp_path):
    cfg = _cfg_dir(tmp_path)
    assert espanso.get_managed_default_config_mode(config_dir=cfg) is None
    assert espanso.default_config_has_remote_desktop_marker(config_dir=cfg) is False
    _apply_workstation(cfg)
    assert espanso.get_managed_default_config_mode(config_dir=cfg) == "workstation"
    assert espanso.default_config_has_remote_desktop_marker(config_dir=cfg) is False
    _apply_host(cfg)
    assert espanso.get_managed_default_config_mode(config_dir=cfg) == "host"
    assert espanso.default_config_has_remote_desktop_marker(config_dir=cfg) is True
    _apply_host(cfg, revert=True)
    assert espanso.get_managed_default_config_mode(config_dir=cfg) is None


def test_detection_ignores_unmanaged_file(tmp_path):
    cfg = _cfg_dir(tmp_path)
    _default_yml(cfg).write_text(USER_CONFIG, encoding="utf-8")
    assert espanso.get_managed_default_config_mode(config_dir=cfg) is None
    assert espanso.default_config_has_remote_desktop_marker(config_dir=cfg) is False


def test_apply_triggers_restart_when_requested(tmp_path):
    cfg = _cfg_dir(tmp_path)
    with patch.object(espanso, "restart_espanso", return_value=True) as restart:
        espanso.apply_remote_desktop_config(config_dir=cfg)
        espanso.apply_remote_desktop_config(config_dir=cfg, restart=False)
    assert restart.call_count == 1
