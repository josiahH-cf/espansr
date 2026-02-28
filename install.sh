#!/usr/bin/env bash
# install.sh — espansr installer
#
# Supports: Linux, WSL2, macOS
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

info "Installing espansr…"
"$VENV_PIP" install --quiet -e "$SCRIPT_DIR"
ok "Package installed"

VENV_CMD="$VENV_DIR/bin/espansr"

# ─── Post-install setup ──────────────────────────────────────────────────────
info "Running post-install setup…"
"$VENV_CMD" setup && ok "Setup complete" || warn "Setup completed with warnings"

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

# ─── Smoke test ──────────────────────────────────────────────────────────────
info "Running smoke test…"

"$VENV_CMD" list && ok "CLI: espansr list — OK" || die "Smoke test failed: 'espansr list' exited non-zero"
"$VENV_CMD" status && ok "CLI: espansr status — OK" || warn "espansr status returned non-zero (Espanso may not be installed)"

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   espansr installed successfully!   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "  CLI:  espansr sync / status / list"
echo "  GUI:  espansr gui"
echo "  Bin:  $VENV_CMD"
echo ""
