#!/usr/bin/env bash
# install.sh — automatr-espanso installer
#
# Supports: Linux, WSL2, macOS
# Does NOT require: llama.cpp, LLM models, requests library
#
# Usage: ./install.sh [--no-desktop]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_MIN="3.11"

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
        return 0  # Homebrew handles deps separately
    fi

    info "Checking system packages for PyQt6…"
    local missing=()

    # PyQt6 on Linux needs xcb platform libs
    for pkg in libxcb-cursor0 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
                libxcb-randr0 libxcb-render-util0 libxcb-shape0 libxkbcommon-x11-0; do
        if ! dpkg -s "$pkg" &>/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done

    if (( ${#missing[@]} > 0 )); then
        warn "Missing packages: ${missing[*]}"
        if command -v apt-get &>/dev/null; then
            info "Installing missing packages (requires sudo)…"
            sudo apt-get install -y -q "${missing[@]}" || warn "Could not install system packages — GUI may not work"
        else
            warn "Cannot auto-install. Please install: ${missing[*]}"
        fi
    else
        ok "System packages present"
    fi
}

install_system_deps

# ─── Virtual environment ──────────────────────────────────────────────────────
if [[ -d "$VENV_DIR" ]]; then
    info "Using existing venv: $VENV_DIR"
else
    info "Creating virtual environment at $VENV_DIR…"
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    ok "Venv created"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

info "Upgrading pip…"
"$VENV_PIP" install --quiet --upgrade pip

info "Installing automatr-espanso…"
"$VENV_PIP" install --quiet -e "$SCRIPT_DIR"
ok "Package installed"

VENV_CMD="$VENV_DIR/bin/automatr-espanso"

# ─── Espanso detection ────────────────────────────────────────────────────────
detect_espanso() {
    info "Detecting Espanso…"

    if [[ "$PLATFORM" == "wsl2" ]]; then
        # Try to find Windows user and check Windows Espanso config
        local win_user
        win_user="$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')" || true
        if [[ -n "$win_user" ]]; then
            for candidate in \
                "/mnt/c/Users/$win_user/.config/espanso" \
                "/mnt/c/Users/$win_user/.espanso" \
                "/mnt/c/Users/$win_user/AppData/Roaming/espanso"; do
                if [[ -d "$candidate" ]]; then
                    ok "Espanso config found (WSL2): $candidate"
                    return 0
                fi
            done
        fi
        warn "Espanso config not found. Install Espanso on Windows first."
        warn "Then run: automatr-espanso status"
        return 0
    fi

    # Linux / macOS native
    if command -v espanso &>/dev/null; then
        ok "Espanso binary: $(command -v espanso)"
    else
        warn "Espanso not found in PATH."
        warn "Install Espanso from https://espanso.org and re-run to verify."
    fi

    # Check config paths
    local config_candidates=()
    if [[ "$PLATFORM" == "macos" ]]; then
        config_candidates=(
            "$HOME/Library/Application Support/espanso"
            "$HOME/.config/espanso"
        )
    else
        config_candidates=(
            "$HOME/.config/espanso"
            "$HOME/.espanso"
        )
    fi

    for p in "${config_candidates[@]}"; do
        if [[ -d "$p" ]]; then
            ok "Espanso config: $p"
            return 0
        fi
    done

    warn "No Espanso config directory found. Run 'espanso start' to initialize Espanso."
}

detect_espanso

# ─── Templates directory ──────────────────────────────────────────────────────
setup_templates_dir() {
    local config_dir
    if [[ "$PLATFORM" == "macos" ]]; then
        config_dir="$HOME/Library/Application Support/automatr-espanso"
    else
        config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/automatr-espanso"
    fi

    local templates_dir="$config_dir/templates"
    mkdir -p "$templates_dir"
    ok "Templates dir: $templates_dir"

    # Copy any bundled templates (currently none per Phase 4 decision)
    local bundled_dir="$SCRIPT_DIR/templates"
    if [[ -d "$bundled_dir" ]]; then
        local count
        count="$(find "$bundled_dir" -name "*.json" | wc -l)"
        if (( count > 0 )); then
            info "Copying $count bundled template(s)…"
            find "$bundled_dir" -name "*.json" -exec cp -n {} "$templates_dir/" \;
            ok "Templates copied (existing files preserved)"
        fi
    fi
}

setup_templates_dir

# ─── AutoHotkey script (WSL2 only) ───────────────────────────────────────────
setup_autohotkey() {
    if [[ "$PLATFORM" != "wsl2" ]]; then
        return 0
    fi

    info "WSL2: Checking AutoHotkey setup…"

    local win_user
    win_user="$(cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')" || true
    if [[ -z "$win_user" ]]; then
        warn "Could not determine Windows username — skipping AutoHotkey setup"
        return 0
    fi

    local ahk_dir="/mnt/c/Users/$win_user/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
    local ahk_script="$SCRIPT_DIR/scripts/automatr-espanso.ahk"

    if [[ ! -f "$ahk_script" ]]; then
        # No AHK script bundled — skip silently
        return 0
    fi

    if [[ -d "$ahk_dir" ]]; then
        cp "$ahk_script" "$ahk_dir/" 2>/dev/null && ok "AutoHotkey script installed to Startup folder" || \
            warn "Could not copy AutoHotkey script — copy manually from scripts/"
    else
        warn "Windows Startup folder not found at expected path"
    fi
}

setup_autohotkey

# ─── Shell integration ────────────────────────────────────────────────────────
setup_shell_alias() {
    local shell_rc
    if [[ "${SHELL:-}" =~ zsh ]]; then
        shell_rc="$HOME/.zshrc"
    else
        shell_rc="$HOME/.bashrc"
    fi

    local alias_line="alias automatr-espanso='$VENV_CMD'"

    if grep -qF "automatr-espanso" "$shell_rc" 2>/dev/null; then
        ok "Shell alias already present in $shell_rc"
    else
        echo "" >> "$shell_rc"
        echo "# automatr-espanso" >> "$shell_rc"
        echo "$alias_line" >> "$shell_rc"
        ok "Added alias to $shell_rc"
        info "Run: source $shell_rc  (or open a new terminal)"
    fi
}

setup_shell_alias

# ─── Smoke test ──────────────────────────────────────────────────────────────
info "Running smoke test…"

"$VENV_CMD" list >/dev/null 2>&1 && ok "CLI: automatr-espanso list — OK" || die "Smoke test failed: 'automatr-espanso list' exited non-zero"
"$VENV_CMD" status >/dev/null 2>&1 && ok "CLI: automatr-espanso status — OK" || warn "automatr-espanso status returned non-zero (Espanso may not be installed)"

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   automatr-espanso installed successfully!   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  CLI:  automatr-espanso sync / status / list"
echo "  GUI:  automatr-espanso gui"
echo "  Bin:  $VENV_CMD"
echo ""
