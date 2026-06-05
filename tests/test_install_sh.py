"""Regression tests for the Linux/macOS/WSL shell installer."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _installer_text() -> str:
    return (ROOT / "install.sh").read_text(encoding="utf-8")


def test_shell_installer_records_install_metadata_for_refresh():
    text = _installer_text()

    assert (
        '"$VENV_CMD" record-install --installer install.sh '
        '--repo-dir "$SCRIPT_DIR" --venv-dir "$VENV_DIR"' in text
    )
    assert "espansr refresh" in text


def test_shell_installer_does_not_advertise_unsupported_no_desktop_flag():
    text = _installer_text()

    assert "--no-desktop" not in text


def test_shell_installer_fails_when_setup_fails():
    text = _installer_text()

    assert 'if "$VENV_CMD" setup; then' in text
    assert (
        'die "Post-install setup failed. Resolve the message above and rerun ./install.sh"' in text
    )
    assert "Setup completed with warnings" not in text


def test_shell_installer_recreates_incomplete_existing_venv():
    text = _installer_text()

    assert '[[ -f "$VENV_DIR/pyvenv.cfg" && -x "$VENV_PYTHON" ]]' in text
    assert "Existing venv is incomplete - recreating $VENV_DIR" in text
    assert 'rm -rf "$VENV_DIR"' in text


def test_shell_installer_checks_debian_dependencies_only_when_tools_exist():
    text = _installer_text()

    assert "command -v dpkg" in text
    assert "command -v apt-get" in text
    assert "Skipping automatic PyQt6 system package check" in text
    assert "Checking Debian/Ubuntu system packages for PyQt6" in text


def test_shell_installer_prints_missing_espanso_next_steps():
    text = _installer_text()

    assert "espansr wsl-install-espanso" in text
    assert "Install and start Espanso from https://espanso.org" in text
    assert "espansr setup" in text
    assert "espansr doctor" in text


def test_shell_installer_prints_list_output_when_smoke_test_fails():
    text = _installer_text()

    assert 'LIST_OUTPUT="$("$VENV_CMD" list 2>&1)"' in text
    assert "Smoke test failed: 'espansr list' exited non-zero" in text


def test_shell_installer_keeps_alias_for_backcompat():
    text = _installer_text()

    # Existing alias-based exposure must be preserved so users who already
    # have it sourced in their interactive shells see no behavior change.
    assert "setup_shell_alias()" in text
    assert "alias espansr=" in text
    assert "setup_shell_alias\n" in text


def test_shell_installer_checks_local_bin_on_path():
    text = _installer_text()

    assert 'USER_BIN="$HOME/.local/bin"' in text
    assert '":$PATH:" != *":$USER_BIN:"*' in text
    assert 'export PATH=\\"\\$HOME/.local/bin:\\$PATH\\"' in text


def test_shell_installer_runs_non_interactive_resolution_smoke():
    text = _installer_text()

    # Proves the shim is reachable in a shell that does NOT source rc files —
    # the exact failure mode RDP/RustDesk-spawned shells exhibit.
    assert "Verifying non-interactive command resolution" in text
    assert 'env -i HOME="$HOME" PATH="$USER_BIN:' in text
    assert "command -v espansr" in text
    assert "Non-interactive: 'espansr' resolves via PATH" in text


# ─── Espanso runtime auto-install ─────────────────────────────────────────────


def test_shell_installer_supports_no_espanso_optout():
    text = _installer_text()

    assert "--no-espanso" in text
    assert "ESPANSR_NO_ESPANSO" in text
    assert "NO_ESPANSO=1" in text


def test_shell_installer_defines_espanso_install_helpers():
    text = _installer_text()

    assert "install_espanso_linux()" in text
    assert "install_espanso_macos()" in text
    assert "install_espanso()" in text
    assert "start_espanso_service()" in text


def test_shell_installer_skips_espanso_install_when_already_present():
    text = _installer_text()

    assert "command -v espanso" in text
    assert "Espanso already on PATH" in text


def test_shell_installer_skips_espanso_install_on_wsl2():
    text = _installer_text()

    assert "WSL2: Espanso must be installed on Windows" in text
    assert "espansr wsl-install-espanso" in text


def test_shell_installer_downloads_appimage_for_linux():
    text = _installer_text()

    # X11 AppImage is the universal Linux fallback. The URL is composed from
    # a base + asset variable, so check the parts.
    assert "https://github.com/espanso/espanso/releases/latest/download/" in text
    assert "Espanso-X11.AppImage" in text


def test_shell_installer_prefers_debian_package_when_apt_available():
    text = _installer_text()

    # Always prefer the X11 .deb on apt distros: Espanso's Wayland build
    # is KDE-only and hangs on GNOME/other compositors, while the X11 build
    # runs reliably under XWayland.
    assert 'install_espanso_deb "x11"' in text
    assert "command -v dpkg" in text
    assert "Espanso installed via Debian package" in text


def test_shell_installer_handles_libfuse_for_appimage():
    text = _installer_text()

    # Either libfuse2 or its t64 successor must be considered.
    assert "libfuse2" in text
    assert "libfuse2t64" in text
    # Fallback to extract-and-run when FUSE is unavailable.
    assert "--appimage-extract-and-run" in text


def test_shell_installer_uses_homebrew_on_macos():
    text = _installer_text()

    assert "brew install espanso" in text
    assert "brew tap espanso/espanso" in text
    assert "https://brew.sh" in text


def test_shell_installer_registers_and_starts_espanso_service():
    text = _installer_text()

    # macOS still uses espanso's built-in launchd registration.
    assert "service register" in text
    assert "service start" in text
    # Linux writes a corrected systemd-user unit because espanso v2.3.0's
    # generated unit uses `ExecStart=espanso launcher` which never starts
    # the daemon.
    assert ".config/systemd/user" in text
    assert "espanso.service" in text
    assert "ExecStart=$espanso_bin daemon" in text
    assert "systemctl --user enable --now espanso" in text


def test_shell_installer_calls_install_espanso_before_setup():
    """Espanso must be installed before `espansr setup` so the first setup
    publishes the launcher/commands popup/templates into the live config dir.
    """
    text = _installer_text()

    install_idx = text.find("install_espanso || warn")
    setup_idx = text.find('"$VENV_CMD" setup')
    assert install_idx != -1
    assert setup_idx != -1
    assert install_idx < setup_idx


def test_shell_installer_supports_xwayland_app_flags():
    text = _installer_text()

    assert "--no-xwayland-apps" in text
    assert "--yes-xwayland-apps" in text
    assert "ESPANSR_XWAYLAND_APPS" in text


def test_shell_installer_defines_xwayland_app_helpers():
    text = _installer_text()

    assert "detect_xwayland_apps()" in text
    assert "apply_xwayland_override_chrome()" in text
    assert "apply_xwayland_override_vscode()" in text
    assert "apply_xwayland_override_obsidian()" in text
    assert "apply_xwayland_override_terminal()" in text
    assert "apply_xwayland_apps_overrides()" in text
    assert "write_xwayland_revert_script()" in text


def test_shell_installer_only_prompts_on_linux_wayland():
    text = _installer_text()

    # Helper guards: skip silently on non-Linux, skip silently on non-Wayland.
    assert '[[ "$PLATFORM" != "linux" ]] && return 0' in text
    assert '[[ "$session_type" != "wayland" ]] && return 0' in text


def test_shell_installer_xwayland_prompt_lists_supported_apps():
    text = _installer_text()

    # The detect helper recognises exactly the four supported app .desktop files.
    assert "/usr/share/applications/google-chrome.desktop" in text
    assert "/usr/share/applications/code.desktop" in text
    assert "/usr/share/applications/obsidian.desktop" in text
    assert "/usr/share/applications/org.gnome.Terminal.desktop" in text


def test_shell_installer_writes_revert_script_and_symlink():
    text = _installer_text()

    # Generated script lives under user-owned XDG dirs and gets a stable
    # PATH-visible name so users can find and run it easily.
    assert ".local/share/espansr/revert-xwayland-apps.sh" in text
    assert ".local/bin/espansr-revert-xwayland-apps" in text
    # The revert script removes only files that carry the espansr marker.
    assert "espansr-xwayland-override" in text
    assert "grep -q 'espansr-xwayland-override'" in text


def test_shell_installer_terminal_override_uses_systemd_user_dropin():
    text = _installer_text()

    # gnome-terminal-server is D-Bus activated; env on the .desktop is a no-op.
    # The override must go into the systemd-user unit drop-in directory.
    assert "gnome-terminal-server.service.d" in text
    assert "Environment=GDK_BACKEND=x11" in text


def test_shell_installer_vscode_override_includes_cli_wrapper():
    text = _installer_text()

    # GUI override alone misses `code .` from a terminal; ensure the CLI
    # wrapper at ~/.local/bin/code is created (shadows /usr/bin/code via PATH).
    assert '"$HOME/.local/bin/code"' in text
    assert "/usr/share/code/bin/code --ozone-platform=x11" in text


def test_shell_installer_final_banner_points_to_revert():
    text = _installer_text()

    # When overrides are applied the success banner surfaces the revert path
    # so users always know how to undo without searching docs.
    assert "XWAYLAND_OVERRIDES_APPLIED == 1" in text
    assert "To revert any time:" in text or "to revert any time:" in text.lower()
