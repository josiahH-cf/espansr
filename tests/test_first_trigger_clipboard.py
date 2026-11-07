"""A deterministic consumer models cold/idle clipboard publication latency.

This exercises real generated configuration, not a live Espanso expansion.
The synthetic clipboard becomes readable at 600 ms; restoration occurs after
paste. No real clipboard, service, foreground window, or private data is used.
"""

import pytest
import yaml

from espansr.integrations import espanso

OLD_DEFAULTS_LINE = "# espansr-defaults: 2026-11 (Sync and reinstall keep this block as it is)\n"
OLD_SETTINGS = {
    "host": (
        "win32_exclude_orphan_events: false\n"
        "backend: Clipboard\n"
        "preserve_clipboard: true\n"
        "restore_clipboard_delay: 2000\n"
        "show_icon: false\n"
        "show_notifications: false\n"
        "key_delay: 30\n"
        "backspace_delay: 30\n"
    ),
    "workstation": (
        "win32_exclude_orphan_events: false\n"
        "preserve_clipboard: true\n"
        "restore_clipboard_delay: 1500\n"
    ),
}


def earlier_block(mode):
    return (
        f"# espansr-managed BEGIN ({mode})\n"
        + OLD_DEFAULTS_LINE
        + OLD_SETTINGS[mode]
        + "# espansr-managed END\n"
    )


def pasted_text(settings, prompt, ready_after_ms):
    """Espanso 2.2.3 defaults to 100 ms before paste (config/default.rs).

    Use an event timeline rather than sleeping or inferring that a setting's
    presence proves a real paste. Restoration is relative to the paste event.
    """
    paste_at = settings.get("pre_paste_delay", 100)
    events = [(ready_after_ms, prompt)]
    if settings.get("preserve_clipboard", True):
        events.append((paste_at + settings.get("restore_clipboard_delay", 300), "old copy"))
    clipboard = "old copy"
    for at, content in sorted(events):
        if at <= paste_at:
            clipboard = content
    return clipboard


@pytest.mark.parametrize("mode", ["host", "workstation"])
@pytest.mark.parametrize("existing", [False, True], ids=["fresh", "earlier-marked"])
def test_first_and_idle_pastes_use_the_prompt(tmp_path, mode, existing):
    path = tmp_path / "config" / "default.yml"
    path.parent.mkdir()
    if existing:
        path.write_text(earlier_block(mode), encoding="utf-8")
        result = espanso.upgrade_previous_default_config(tmp_path, restart=False)
    else:
        result = espanso.configure_default_config(mode, tmp_path, restart=False)
    assert result.ok
    settings = yaml.safe_load(path.read_text(encoding="utf-8"))
    for state, ready_after_ms in (("cold", 600), ("warm", 20), ("idle", 600)):
        prompt = f"{state}: Résumé 👋\nSecond line. \n\n"
        assert pasted_text(settings, prompt, ready_after_ms) == prompt, state
    assert settings["preserve_clipboard"] is True
    assert settings["restore_clipboard_delay"] == (2000 if mode == "host" else 1500)
    stable = path.read_bytes()
    assert not espanso.upgrade_previous_default_config(tmp_path, restart=False).changed
    assert path.read_bytes() == stable


@pytest.mark.parametrize("mode", ["host", "workstation"])
@pytest.mark.parametrize(
    "customization",
    ["chosen", "never-restore", "tuned", "external-delay", "in-block-delay", "unknown-marker"],
)
def test_refresh_keeps_explicit_choices_and_custom_blocks(tmp_path, mode, customization):
    text = earlier_block(mode)
    if customization == "chosen":
        text = text.replace(
            OLD_DEFAULTS_LINE, OLD_DEFAULTS_LINE + "# espansr-restore-delay: 2500 ms\n"
        )
    elif customization == "never-restore":
        text = text.replace("preserve_clipboard: true", "preserve_clipboard: false")
        text = "\n".join(
            line for line in text.split("\n") if not line.startswith("restore_clipboard_delay:")
        )
    elif customization == "tuned":
        text = text.replace("false", "true", 1)
    elif customization == "external-delay":
        text = "pre_paste_delay: 1750  # my timing\n" + text
    elif customization == "in-block-delay":
        text = text.replace("# espansr-managed END", "pre_paste_delay: 1750\n# espansr-managed END")
    else:
        text = text.replace("2026-11 (", "custom-version (")
    path = tmp_path / "config" / "default.yml"
    path.parent.mkdir()
    path.write_text(text, encoding="utf-8")
    before = path.read_bytes()
    result = espanso.upgrade_previous_default_config(tmp_path, restart=False)
    assert result.outcome == "skipped"
    assert path.read_bytes() == before


@pytest.mark.parametrize("mode", ["host", "workstation"])
def test_earlier_upgrade_keeps_outside_bytes_and_reverts_originals(tmp_path, mode):
    path = tmp_path / "config" / "default.yml"
    path.parent.mkdir()
    original = (
        "# outside head\n"
        "toggle_key: OFF  # keep spelling\n"
        + earlier_block(mode).replace(
            OLD_DEFAULTS_LINE,
            OLD_DEFAULTS_LINE + "# espansr-prev: pre_paste_delay: 750  # original timing\n",
        )
        + "# outside tail\nword_separators: [' ', ',']\n"
    )
    path.write_bytes(original.replace("\n", "\r\n").encode("utf-8"))
    assert espanso.upgrade_previous_default_config(tmp_path, restart=False).changed
    after = path.read_bytes()
    assert after.startswith(b"# outside head\r\ntoggle_key: OFF  # keep spelling\r\n")
    assert b"# outside tail\r\nword_separators: [' ', ',']\r\n" in after
    assert after.count(b"\n") == after.count(b"\r\n")
    assert yaml.safe_load(after)["pre_paste_delay"] == 1000
    assert espanso.configure_default_config(mode, tmp_path, revert=True, restart=False).ok
    restored = path.read_bytes()
    previous = b"pre_paste_delay: 750  # original timing\r\n"
    assert restored.count(previous) == 1
    assert restored.replace(previous, b"") == (
        b"# outside head\r\ntoggle_key: OFF  # keep spelling\r\n"
        b"# outside tail\r\nword_separators: [' ', ',']\r\n"
    )
