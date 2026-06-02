#!/usr/bin/env bash
# install.sh — espansr installer
#
# Supports: Linux, WSL2, macOS
#
# Usage: ./install.sh [--no-espanso] [--no-xwayland-apps | --yes-xwayland-apps]
#
#   --no-espanso         Skip automatic Espanso runtime install (Linux/macOS).
#                        Same effect as setting ESPANSR_NO_ESPANSO=1.
#   --no-xwayland-apps   Skip the GNOME/Wayland app override prompt.
#                        Same effect as setting ESPANSR_XWAYLAND_APPS=no.
#   --yes-xwayland-apps  Apply the GNOME/Wayland app overrides without prompting.
#                        Same effect as setting ESPANSR_XWAYLAND_APPS=yes.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_MIN="3.11"

# ─── Argument parsing ─────────────────────────────────────────────────────────
NO_ESPANSO=0
if [[ "${ESPANSR_NO_ESPANSO:-}" == "1" ]]; then
    NO_ESPANSO=1
fi
XWAYLAND_APPS_MODE="${ESPANSR_XWAYLAND_APPS:-auto}"
for arg in "$@"; do
    case "$arg" in
        --no-espanso)
            NO_ESPANSO=1
            ;;
        --no-xwayland-apps)
            XWAYLAND_APPS_MODE="no"
            ;;
        --yes-xwayland-apps)
            XWAYLAND_APPS_MODE="yes"
            ;;
        -h|--help)
            grep '^#' "$0" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

# ─── Color helpers ────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()      { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERR ]${NC} $*" >&2; }
die()     { error "$*"; exit 1; }

# ─── Platform detection ───────────────────────────────────────────────────────
detect_platform() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif grep -qi "microsoft\|wsl" /proc/version 2>/dev/null; then
        echo "wsl2"
    else
        echo "linux"
    fi
}

PLATFORM="$(detect_platform)"
info "Platform: $PLATFORM"

if [[ "$PLATFORM" == "wsl2" ]]; then
    info "WSL2 install target: WSL environment"
    info "Windows PowerShell and WSL keep separate PATH, venv, and shell setup."
    info "For a native Windows-hosted install, run .\\install.ps1 in Windows PowerShell instead."
fi

# ─── Python version check ─────────────────────────────────────────────────────
check_python() {
    local python_bin
    for candidate in python3.12 python3.11 python3; do
        if command -v "$candidate" &>/dev/null; then
            local ver
            ver="$("$candidate" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
            local major minor
            IFS='.' read -r major minor <<<"$ver"
            local req_major req_minor
            IFS='.' read -r req_major req_minor <<<"$PYTHON_MIN"
            if (( major > req_major || (major == req_major && minor >= req_minor) )); then
                echo "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON_BIN="$(check_python)" || die "Python $PYTHON_MIN+ is required. Install it and re-run."
ok "Python: $("$PYTHON_BIN" --version)"

# ─── System dependencies (Linux/WSL2) ─────────────────────────────────────────
install_system_deps() {
    if [[ "$PLATFORM" == "macos" ]]; then
        info "macOS: using Python wheels for PyQt6; install and start Espanso separately."
        return 0
    fi

    if ! command -v dpkg &>/dev/null || ! command -v apt-get &>/dev/null; then
        warn "Skipping automatic PyQt6 system package check (dpkg/apt-get not available)."
        warn "If the GUI fails to start, install your distribution's Qt/XCB runtime packages."
        return 0
    fi

    info "Checking Debian/Ubuntu system packages for PyQt6..."
    local missing=()

    # PyQt6 on Linux needs xcb platform libs
    for pkg in libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
                libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxkbcommon-x11-0; do
        if ! dpkg -s "$pkg" &>/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done

    # Espanso AppImage needs libfuse2. Newer Debian/Ubuntu (24.04+) renamed it
    # to libfuse2t64 — check whichever is available and skip if neither exists
    # (e.g. minimal containers); install_espanso() will fall back to extract mode.
    if (( NO_ESPANSO == 0 )); then
        if ! dpkg -s libfuse2 &>/dev/null 2>&1 && ! dpkg -s libfuse2t64 &>/dev/null 2>&1; then
            if apt-cache show libfuse2t64 &>/dev/null 2>&1; then
                missing+=("libfuse2t64")
            elif apt-cache show libfuse2 &>/dev/null 2>&1; then
                missing+=("libfuse2")
            fi
        fi
    fi

    if (( ${#missing[@]} > 0 )); then
        warn "Missing packages: ${missing[*]}"
        if command -v apt-get &>/dev/null; then
            info "Installing missing packages (requires sudo)…"
            sudo apt-get install -y -q "${missing[@]}" || warn "Could not install system packages - GUI may not work"
        else
            warn "Cannot auto-install. Please install: ${missing[*]}"
        fi
    else
        ok "System packages present"
    fi
}

install_system_deps

# ─── Espanso runtime install (Linux/macOS only) ──────────────────────────────
#
# espansr manages templates; Espanso is the daemon that actually expands
# triggers. Without Espanso installed and running, triggers like ":meta"
# never fire. This block installs Espanso automatically on first run so the
# end-to-end flow works after a single `bash install.sh`. WSL2 is delegated
# to the existing `espansr wsl-install-espanso` wrapper because Espanso must
# run on the Windows host, not inside WSL.

ESPANSO_INSTALLED_THIS_RUN=0

install_espanso_linux() {
    # Espanso's Wayland build (kdotool-based) only works on KDE/KWin and
    # hangs on GNOME Wayland and other compositors. The X11 build runs under
    # XWayland and works reliably across desktops, so install it everywhere
    # on Linux. On apt distros prefer the .deb; fall back to the X11 AppImage.
    if command -v dpkg &>/dev/null && command -v apt-get &>/dev/null; then
        if install_espanso_deb "x11"; then
            return 0
        fi
        warn "Falling back to AppImage install"
    fi
    install_espanso_appimage_x11
}

install_espanso_deb() {
    local session="$1"
    local asset="espanso-debian-${session}-amd64.deb"
    local url="https://github.com/espanso/espanso/releases/latest/download/$asset"
    local tmp
    tmp="$(mktemp --suffix=.deb 2>/dev/null || mktemp)"

    info "Downloading $asset…"
    if ! curl -fSL --retry 2 --connect-timeout 15 "$url" -o "$tmp" 2>/dev/null; then
        warn "Download failed: $url"
        rm -f "$tmp"
        return 1
    fi

    info "Installing $asset (requires sudo)…"
    if sudo apt-get install -y -q "$tmp" 2>&1 | tail -5; then
        ok "Espanso installed via Debian package"
        rm -f "$tmp"
        return 0
    fi
    warn "apt-get install of $asset failed"
    rm -f "$tmp"
    return 1
}

install_espanso_appimage_x11() {
    local user_bin="$HOME/.local/bin"
    local dest="$user_bin/espanso"
    local asset="Espanso-X11.AppImage"
    local url="https://github.com/espanso/espanso/releases/latest/download/$asset"

    mkdir -p "$user_bin"
    info "Fetching $url"
    if ! curl -fSL --retry 2 --connect-timeout 15 "$url" -o "$dest.tmp" 2>/dev/null; then
        warn "Download failed: $url"
        rm -f "$dest.tmp"
        info "Install Espanso manually from https://espanso.org/install/linux/, then rerun ./install.sh"
        return 1
    fi
    mv "$dest.tmp" "$dest"
    chmod +x "$dest"
    ok "Espanso AppImage installed at $dest"

    # AppImage needs FUSE; on hosts without libfuse2, fall back to
    # --appimage-extract-and-run via a wrapper.
    if ! "$dest" --version &>/dev/null; then
        warn "Espanso AppImage cannot run directly (FUSE may be unavailable); falling back to extract-and-run"
        local appimage="$user_bin/.espanso.AppImage"
        mv "$dest" "$appimage"
        cat > "$dest" <<EOF
#!/usr/bin/env bash
exec "$appimage" --appimage-extract-and-run "\$@"
EOF
        chmod +x "$dest"
        if ! "$dest" --version &>/dev/null; then
            warn "Espanso still cannot run; manual install may be required"
            return 1
        fi
        ok "Espanso fallback wrapper configured (extract-and-run mode)"
    fi

    return 0
}

install_espanso_macos() {
    if ! command -v brew &>/dev/null; then
        warn "Homebrew not found. espansr does not auto-install brew."
        info "Install Homebrew from https://brew.sh, then run:"
        echo "  brew tap espanso/espanso && brew install espanso"
        echo "  espanso service register && espanso service start"
        echo "  bash install.sh   # rerun once Espanso is installed"
        return 1
    fi

    if brew list espanso &>/dev/null 2>&1; then
        ok "Espanso already installed via Homebrew"
        return 0
    fi

    info "Installing Espanso via Homebrew…"
    if ! brew tap espanso/espanso &>/dev/null; then
        warn "Could not tap espanso/espanso (continuing — formula may already be available)"
    fi
    if brew install espanso; then
        ok "Espanso installed via Homebrew"
        return 0
    fi
    warn "brew install espanso failed"
    info "Install manually: brew tap espanso/espanso && brew install espanso"
    return 1
}

start_espanso_service() {
    local espanso_bin="${1:-espanso}"

    # Clean up any leftover espanso processes from a prior run (the v2.3.0
    # launcher / tray helper holds runtime locks and blocks fresh starts).
    pkill -f 'espanso ' 2>/dev/null || true
    sleep 1
    rm -f "$HOME/.cache/espanso/"*.lock "$HOME/.cache/espanso/"*.sock 2>/dev/null || true

    local config_dir="$HOME/.config/espanso"
    if [[ "$PLATFORM" == "macos" ]]; then
        config_dir="$HOME/Library/Application Support/espanso"
    fi
    mkdir -p "$config_dir/config" "$config_dir/match"
    if [[ ! -f "$config_dir/config/default.yml" ]]; then
        # show_icon: false avoids the GNOME-no-tray hang; the daemon still
        # runs and triggers still expand.
        cat > "$config_dir/config/default.yml" <<'YAML'
# Espanso default config — created by espansr installer
show_icon: false
show_notifications: false
YAML
        ok "Seeded default Espanso config at $config_dir/config/default.yml"
    fi

    if [[ "$PLATFORM" == "macos" ]]; then
        # macOS: launchd is managed by espanso itself.
        info "Registering Espanso service…"
        "$espanso_bin" service register &>/dev/null || true
        info "Starting Espanso service…"
        if "$espanso_bin" service start &>/dev/null; then
            ok "Espanso service started"
        else
            warn "Espanso service start failed; run 'espanso service start' manually"
        fi
    else
        # Linux: espanso v2.3.0's `service register` writes a systemd unit
        # with ExecStart=espanso launcher, which only starts the tray helper
        # and never spawns the daemon/worker. Write the correct unit
        # ourselves so the daemon comes up reliably.
        local unit_dir="$HOME/.config/systemd/user"
        local unit="$unit_dir/espanso.service"
        mkdir -p "$unit_dir"
        cat > "$unit" <<EOF
[Unit]
Description=espanso
After=graphical-session.target

[Service]
ExecStart=$espanso_bin daemon
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
EOF
        ok "Wrote systemd-user unit: $unit"
        info "Enabling and starting espanso.service…"
        systemctl --user daemon-reload &>/dev/null || true
        if systemctl --user enable --now espanso &>/dev/null; then
            sleep 3
            if systemctl --user is-active espanso &>/dev/null; then
                ok "Espanso daemon active (systemctl --user status espanso)"
            else
                warn "Espanso unit enabled but not active; check 'journalctl --user -u espanso'"
            fi
        else
            warn "systemctl --user enable failed; run manually: systemctl --user enable --now espanso"
        fi
    fi

    # Wait briefly for the config dir to materialize so the next `espansr setup`
    # picks it up and publishes the launcher/commands popup/templates.
    local i
    for i in {1..15}; do
        if [[ -d "$config_dir" ]]; then
            ok "Espanso config dir present: $config_dir"
            return 0
        fi
        sleep 1
    done
    warn "Espanso config dir did not appear within 15s: $config_dir"
    return 1
}

install_espanso() {
    if (( NO_ESPANSO == 1 )); then
        info "Skipping Espanso runtime install (--no-espanso)"
        return 0
    fi

    if [[ "$PLATFORM" == "wsl2" ]]; then
        info "WSL2: Espanso must be installed on Windows; skipping POSIX install."
        info "Run from WSL: espansr wsl-install-espanso"
        return 0
    fi

    if command -v espanso &>/dev/null; then
        ok "Espanso already on PATH ($(command -v espanso))"
        return 0
    fi

    case "$PLATFORM" in
        linux)
            install_espanso_linux || return 1
            ;;
        macos)
            install_espanso_macos || return 1
            ;;
        *)
            warn "Unsupported platform for Espanso auto-install: $PLATFORM"
            return 1
            ;;
    esac

    ESPANSO_INSTALLED_THIS_RUN=1
    start_espanso_service "$(command -v espanso || echo "$HOME/.local/bin/espanso")" || true
    return 0
}

install_espanso || warn "Espanso runtime install did not complete; you can install it later from https://espanso.org and rerun this installer."

# ─── XWayland app override helpers ────────────────────────────────────────────
# On GNOME/Wayland sessions Espanso cannot capture keystrokes inside native
# Wayland apps. These helpers force a small set of common apps under
# XWayland by writing user-owned overrides that survive package updates.
# All overrides are removed cleanly by the generated revert script.
XWAYLAND_REVERT_SCRIPT="$HOME/.local/share/espansr/revert-xwayland-apps.sh"
XWAYLAND_REVERT_BIN="$HOME/.local/bin/espansr-revert-xwayland-apps"
XWAYLAND_OVERRIDES_APPLIED=0

_xwayland_marker() {
    echo "# espansr-xwayland-override — remove via $XWAYLAND_REVERT_BIN"
}

detect_xwayland_apps() {
    local detected=()
    [[ -f /usr/share/applications/google-chrome.desktop ]] && detected+=("chrome")
    [[ -f /usr/share/applications/code.desktop ]] && detected+=("vscode")
    [[ -f /usr/share/applications/obsidian.desktop ]] && detected+=("obsidian")
    [[ -f /usr/share/applications/org.gnome.Terminal.desktop ]] && detected+=("terminal")
    printf '%s\n' "${detected[@]}"
}

write_xwayland_revert_script() {
    mkdir -p "$(dirname "$XWAYLAND_REVERT_SCRIPT")" "$(dirname "$XWAYLAND_REVERT_BIN")"
    cat > "$XWAYLAND_REVERT_SCRIPT" <<'REVERT_SCRIPT'
#!/usr/bin/env bash
# Revert XWayland overrides applied by espansr install.sh.
# Each removal is independent and idempotent. Existing app windows keep
# their current backend until they are closed and relaunched.
set -u
removed=0
remove_if_marked() {
    local f="$1"
    if [[ -f "$f" ]] && grep -q 'espansr-xwayland-override' "$f"; then
        rm -f "$f" && echo "removed: $f" && removed=$((removed+1))
    fi
}
remove_if_marked "$HOME/.local/share/applications/google-chrome.desktop"
remove_if_marked "$HOME/.local/share/applications/code.desktop"
remove_if_marked "$HOME/.local/share/applications/code-url-handler.desktop"
remove_if_marked "$HOME/.local/share/applications/obsidian.desktop"
remove_if_marked "$HOME/.local/bin/code"
override="$HOME/.config/systemd/user/gnome-terminal-server.service.d/override.conf"
if [[ -f "$override" ]] && grep -q 'espansr-xwayland-override' "$override"; then
    rm -f "$override"
    rmdir "$(dirname "$override")" 2>/dev/null || true
    systemctl --user daemon-reload &>/dev/null || true
    systemctl --user stop gnome-terminal-server.service &>/dev/null || true
    pkill -f gnome-terminal-server 2>/dev/null || true
    echo "removed: $override (next gnome-terminal launch returns to Wayland)"
    removed=$((removed+1))
fi
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$HOME/.local/share/applications" &>/dev/null || true
fi
echo
if (( removed == 0 )); then
    echo "No espansr XWayland overrides found. Nothing to do."
else
    echo "Reverted $removed override(s). Close and relaunch affected apps to return them to Wayland."
fi
REVERT_SCRIPT
    chmod +x "$XWAYLAND_REVERT_SCRIPT"
    ln -sf "$XWAYLAND_REVERT_SCRIPT" "$XWAYLAND_REVERT_BIN"
}

apply_xwayland_override_chrome() {
    local src=/usr/share/applications/google-chrome.desktop
    local dst="$HOME/.local/share/applications/google-chrome.desktop"
    mkdir -p "$(dirname "$dst")"
    {
        _xwayland_marker
        sed -E 's|^Exec=(/usr/bin/google-chrome-stable)([^\n]*)|Exec=\1 --ozone-platform=x11\2|' "$src"
    } > "$dst"
    ok "Chrome: override at $dst"
}

apply_xwayland_override_vscode() {
    local src1=/usr/share/applications/code.desktop
    local dst1="$HOME/.local/share/applications/code.desktop"
    local src2=/usr/share/applications/code-url-handler.desktop
    local dst2="$HOME/.local/share/applications/code-url-handler.desktop"
    mkdir -p "$(dirname "$dst1")"
    {
        _xwayland_marker
        sed -E 's|^Exec=(/usr/share/code/code)([^\n]*)|Exec=\1 --ozone-platform=x11\2|' "$src1"
    } > "$dst1"
    if [[ -f "$src2" ]]; then
        {
            _xwayland_marker
            sed -E 's|^Exec=(/usr/share/code/code)([^\n]*)|Exec=\1 --ozone-platform=x11\2|' "$src2"
        } > "$dst2"
    fi
    mkdir -p "$HOME/.local/bin"
    cat > "$HOME/.local/bin/code" <<EOF
#!/usr/bin/env bash
$(_xwayland_marker)
exec /usr/share/code/bin/code --ozone-platform=x11 "\$@"
EOF
    chmod +x "$HOME/.local/bin/code"
    ok "VS Code: overrides at $dst1, $dst2, and ~/.local/bin/code"
}

apply_xwayland_override_obsidian() {
    local src=/usr/share/applications/obsidian.desktop
    local dst="$HOME/.local/share/applications/obsidian.desktop"
    mkdir -p "$(dirname "$dst")"
    {
        _xwayland_marker
        sed -E 's|^Exec=(/opt/Obsidian/obsidian)([^\n]*)|Exec=\1 --ozone-platform=x11\2|' "$src"
    } > "$dst"
    ok "Obsidian: override at $dst"
}

apply_xwayland_override_terminal() {
    # gnome-terminal is D-Bus activated; env on the .desktop client is a no-op.
    # Pin GDK_BACKEND on the long-lived gnome-terminal-server systemd-user unit.
    local dir="$HOME/.config/systemd/user/gnome-terminal-server.service.d"
    local override="$dir/override.conf"
    mkdir -p "$dir"
    cat > "$override" <<EOF
$(_xwayland_marker)
[Service]
Environment=GDK_BACKEND=x11
EOF
    systemctl --user daemon-reload &>/dev/null || true
    systemctl --user stop gnome-terminal-server.service &>/dev/null || true
    pkill -f gnome-terminal-server 2>/dev/null || true
    ok "gnome-terminal: server override at $override"
}

apply_xwayland_apps_overrides() {
    # Only applies on a Linux Wayland session. Silent no-op elsewhere.
    [[ "$PLATFORM" != "linux" ]] && return 0
    local session_type="${XDG_SESSION_TYPE:-}"
    if [[ -z "$session_type" && -n "${WAYLAND_DISPLAY:-}" ]]; then
        session_type="wayland"
    fi
    [[ "$session_type" != "wayland" ]] && return 0

    if [[ "$XWAYLAND_APPS_MODE" == "no" ]]; then
        info "XWayland app overrides: skipped (--no-xwayland-apps / ESPANSR_XWAYLAND_APPS=no)"
        return 0
    fi

    local detected=()
    local app
    while IFS= read -r app; do
        [[ -n "$app" ]] && detected+=("$app")
    done < <(detect_xwayland_apps)
    if (( ${#detected[@]} == 0 )); then
        return 0
    fi

    echo
    info "GNOME/Wayland session detected."
    info "Espanso cannot capture keystrokes inside native-Wayland apps."
    info "Detected supported apps that can be forced under XWayland so triggers fire inside them:"
    printf '  - %s\n' "${detected[@]}"

    local answer="$XWAYLAND_APPS_MODE"
    if [[ "$answer" == "auto" ]]; then
        if [[ -t 0 ]]; then
            read -r -p "Apply X11 override to these apps? [Y/n] " answer
            answer="${answer:-y}"
        else
            info "Non-interactive shell — skipping. Re-run with --yes-xwayland-apps to apply."
            return 0
        fi
    fi
    case "${answer,,}" in
        y|yes|all|true|1) ;;
        *)
            info "XWayland app overrides: declined."
            return 0
            ;;
    esac

    write_xwayland_revert_script
    for app in "${detected[@]}"; do
        case "$app" in
            chrome)   apply_xwayland_override_chrome ;;
            vscode)   apply_xwayland_override_vscode ;;
            obsidian) apply_xwayland_override_obsidian ;;
            terminal) apply_xwayland_override_terminal ;;
        esac
    done
    command -v update-desktop-database &>/dev/null \
        && update-desktop-database "$HOME/.local/share/applications" &>/dev/null || true
    XWAYLAND_OVERRIDES_APPLIED=1
    ok "XWayland overrides applied for: ${detected[*]}"
    info "Revert any time with:"
    echo "  $XWAYLAND_REVERT_BIN"
    echo "  (or: bash $XWAYLAND_REVERT_SCRIPT)"
}

# Ensure the just-installed Espanso (and the espansr shim, if it pre-exists) is
# visible to subsequent steps in this script process.
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ;;
    *) export PATH="$HOME/.local/bin:$PATH" ;;
esac

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

# ─── Virtual environment ──────────────────────────────────────────────────────
if [[ -d "$VENV_DIR" ]]; then
    if [[ -f "$VENV_DIR/pyvenv.cfg" && -x "$VENV_PYTHON" ]]; then
        info "Using existing venv: $VENV_DIR"
    else
        warn "Existing venv is incomplete - recreating $VENV_DIR"
        rm -rf "$VENV_DIR"
        info "Creating virtual environment at $VENV_DIR…"
        "$PYTHON_BIN" -m venv "$VENV_DIR"
        ok "Venv created"
    fi
else
    info "Creating virtual environment at $VENV_DIR…"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    ok "Venv created"
fi

info "Upgrading pip…"
"$VENV_PIP" install --quiet --upgrade pip

info "Installing espansr…"
"$VENV_PIP" install --quiet -e "$SCRIPT_DIR"
ok "Package installed"

VENV_CMD="$VENV_DIR/bin/espansr"

# ─── Post-install setup ──────────────────────────────────────────────────────
info "Running post-install setup…"
if "$VENV_CMD" setup; then
    ok "Setup complete"
else
    die "Post-install setup failed. Resolve the message above and rerun ./install.sh"
fi

# ─── Shell integration ────────────────────────────────────────────────────────
setup_shell_alias() {
    local shell_rc
    if [[ "${SHELL:-}" =~ zsh ]]; then
        shell_rc="$HOME/.zshrc"
    else
        shell_rc="$HOME/.bashrc"
    fi

    local alias_line="alias espansr='$VENV_CMD'"

    if grep -qF "espansr" "$shell_rc" 2>/dev/null; then
        ok "Shell alias already present in $shell_rc"
    else
        echo "" >> "$shell_rc"
        echo "# espansr" >> "$shell_rc"
        echo "$alias_line" >> "$shell_rc"
        ok "Added alias to $shell_rc"
        info "Run: source $shell_rc  (or open a new terminal)"
    fi
}

setup_shell_alias

if [[ "$PLATFORM" == "wsl2" ]]; then
    info "WSL note: shell alias changes here do not add espansr to Windows PowerShell."
fi

# ─── PATH-visible command shim ────────────────────────────────────────────────
# `espansr setup` creates a real executable at ~/.local/bin/espansr so the
# command resolves in non-interactive shells (subprocess calls, .desktop
# launchers, systemd-user units, IDE terminals, and remote-desktop session
# shells such as RustDesk/RDP). Aliases alone never resolve there.
USER_BIN="$HOME/.local/bin"
if [[ ":$PATH:" != *":$USER_BIN:"* ]]; then
    warn "$USER_BIN is not on PATH for this shell."
    info "Most distros add it from ~/.profile on login. If yours does not, add:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    info "to your shell profile and start a new login shell."
fi

# ─── Non-interactive resolution smoke test ────────────────────────────────────
# Confirms `espansr` is reachable in a shell that does NOT source ~/.bashrc
# or ~/.zshrc. This is the exact context where the previous alias-only
# install silently failed under remote-desktop sessions.
info "Verifying non-interactive command resolution…"
if env -i HOME="$HOME" PATH="$USER_BIN:/usr/local/bin:/usr/bin:/bin" \
        bash -c 'command -v espansr' >/dev/null 2>&1; then
    ok "Non-interactive: 'espansr' resolves via PATH"
else
    warn "Non-interactive: 'espansr' did not resolve via PATH"
    info "Ensure $USER_BIN is on PATH for login shells, then rerun ./install.sh"
fi

# ─── Smoke test ──────────────────────────────────────────────────────────────
info "Running smoke test…"

LIST_OUTPUT="$("$VENV_CMD" list 2>&1)" || {
    echo "$LIST_OUTPUT"
    die "Smoke test failed: 'espansr list' exited non-zero"
}
echo "$LIST_OUTPUT"
ok "CLI: espansr list — OK"
STATUS_OUTPUT="$("$VENV_CMD" status 2>&1 || true)"
echo "$STATUS_OUTPUT"
ok "CLI: espansr status — OK"

if echo "$STATUS_OUTPUT" | grep -q "Espanso config: not found"; then
    warn "Dependency note: espansr does not install Espanso itself."
    if [[ "$PLATFORM" == "wsl2" ]]; then
        info "Recommended from WSL:"
        echo "  espansr wsl-install-espanso"
        info "Manual fallback in Windows PowerShell, then re-check from WSL:"
        echo "  winget install --id Espanso.Espanso -e --accept-package-agreements --accept-source-agreements"
        echo "  espanso start"
        echo "  espansr doctor"
    else
        info "Install and start Espanso from https://espanso.org, then run:"
        echo "  espansr setup"
        echo "  espansr doctor"
    fi
fi

# ─── XWayland app overrides (optional, Wayland sessions only) ────────────────
apply_xwayland_apps_overrides

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   espansr installed successfully!   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  CLI:  espansr publish / status / list / doctor"
echo "  GUI:  espansr gui"
echo "  Bin:  $VENV_CMD"
if (( XWAYLAND_OVERRIDES_APPLIED == 1 )); then
    echo ""
    echo "  XWayland overrides applied. To revert any time:"
    echo "      $XWAYLAND_REVERT_BIN"
fi
echo ""
info "Enable tab completion by adding to your shell config:"
echo "  eval \"\$(espansr completions bash)\"   # bash (~/.bashrc)"
echo "  eval \"\$(espansr completions zsh)\"    # zsh  (~/.zshrc)"
echo ""

