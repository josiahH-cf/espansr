# Meta-Prompt: Bootstrap the orchestr Repository

> **Context:** You are working in a directory that contains two sibling projects:
> - `espansr/` — an existing, complete Python+PyQt6 project (text expansion template manager)
> - `orchestr/` — a new, empty repository that needs to be bootstrapped
>
> Focus ONLY on these two projects. Ignore any other directories at this level.

---

## Objective

Set up the `orchestr/` repository with:
1. **Workflow scaffolding** — adapted from espansr's battle-tested agent workflow files
2. **Feature specs** — copied from `espansr/specs/orchestr/` (the design work is already done)
3. **Project identity** — a new AGENTS.md, README, and config tailored to orchestr's Go-based architecture

Do NOT copy any espansr application code, tests, Python config, or espansr-specific documentation.

---

## Step 1: Copy and adapt workflow scaffolding

Copy these files from `espansr/` into `orchestr/`, then **adapt** each one as described below. Do not copy them verbatim — every file must be rewritten for orchestr's context.

### Files to copy and adapt

| Source (espansr/) | Destination (orchestr/) | Adaptation needed |
|---|---|---|
| `CLAUDE.md` | `CLAUDE.md` | **Copy verbatim.** It's fully generic (session rules, planning refs, scope discipline). No changes needed. |
| `CLAUDE.local.md` | `CLAUDE.local.md` | **Copy verbatim.** Empty personal-preferences stub. Add to `.gitignore`. |
| `.claude/settings.json` | `.claude/settings.json` | **Rewrite hooks.** Replace `black "$FILEPATH"` with `gofmt -w "$FILEPATH"`. Replace `ruff check . --fix` with `golangci-lint run --fix ./...`. Keep the permissions and structure identical. |
| `.claude/settings.local.json` | `.claude/settings.local.json` | **Copy verbatim.** Just sets `bypassPermissions`. |
| `.claude/commands/*.md` | `.claude/commands/*.md` | **Copy all 14 command files verbatim.** They are fully generic workflow commands (scope, plan, test, implement, review, merge, etc.) with no project-specific content. |
| `.codex/PLANS.md` | `.codex/PLANS.md` | **Copy verbatim.** Generic ExecPlan template. |
| `.codex/config.toml` | `.codex/config.toml` | **Copy verbatim.** Generic Codex configuration. |
| `.github/copilot-instructions.md` | `.github/copilot-instructions.md` | **Copy verbatim.** Generic Copilot rules that reference `/AGENTS.md`. |
| `.github/pull_request_template.md` | `.github/pull_request_template.md` | **Copy verbatim.** Generic PR template. |
| `.github/ISSUE_TEMPLATE/bug.md` | `.github/ISSUE_TEMPLATE/bug.md` | **Copy verbatim.** Generic bug template. |
| `.github/ISSUE_TEMPLATE/feature.md` | `.github/ISSUE_TEMPLATE/feature.md` | **Copy verbatim.** Generic feature template. |
| `.github/agents/reviewer.md` | `.github/agents/reviewer.md` | **Copy verbatim.** Generic review agent definition. |
| `workflow/LIFECYCLE.md` | `workflow/LIFECYCLE.md` | **Copy verbatim.** Generic feature lifecycle doc. |
| `specs/_TEMPLATE.md` | `specs/_TEMPLATE.md` | **Copy verbatim.** |
| `tasks/_TEMPLATE.md` | `tasks/_TEMPLATE.md` | **Copy verbatim.** |
| `decisions/_TEMPLATE.md` | `decisions/_TEMPLATE.md` | **Copy verbatim.** |

### Files to NOT copy

| File | Reason |
|---|---|
| `AGENTS.md` | Must be written from scratch for orchestr (see Step 2) |
| `README.md` | Must be written from scratch (see Step 3) |
| `CHANGELOG.md` | Start fresh — orchestr has no history yet |
| `VERIFY.md` | Espansr-specific verification checklist |
| `pyproject.toml` | Python packaging — irrelevant to Go |
| `install.sh` / `install.ps1` | Espansr-specific installers |
| `.github/workflows/ci.yml` | Espansr-specific CI (Python, PyQt6, apt packages) — write a new one for Go |
| `.github/workflows/copilot-setup-steps.yml` | Espansr-specific (Python setup) — write a new one for Go |
| `espansr/` | Entire application — wrong project |
| `tests/` | Python test suite — wrong project |
| `templates/` | Espanso template JSONs — wrong project |
| `specs/archive/` | Espansr's archived specs |
| `tasks/archive/` | Espansr's archived tasks |
| `specs/toggleable-yaml-preview.md` | Espansr feature spec |
| `specs/espansr-orchestr-connector.md` | Stays in espansr — it's the espansr-side integration |

---

## Step 2: Write AGENTS.md for orchestr

Create `orchestr/AGENTS.md` with the following content. This is the single source of truth for the project:

```markdown
# Project

- Project name: orchestr
- Description: A system-wide hotkey launcher and app orchestrator. Background daemon with leader-key chords, localhost HTTP API, and cross-environment launching.
- Primary language/framework: Go (single binary, cross-platform)
- Scope: Hotkey registration, app lifecycle management, IPC via HTTP, system tray, cross-env launching (WSL2 ↔ Windows)
- Non-goals: cloud APIs, multi-tenant, mobile/web, plugin system, package manager distribution (v1)

# Build

- Install: `go install ./...` or `make install`
- Build: `go build -o orchestr ./cmd/orchestr`
- Test (all): `go test ./...`
- Test (single): `go test ./internal/hotkey -run TestLeaderKeyCapture`
- Lint: `golangci-lint run ./...`
- Format: `gofmt -w .`
- Type-check: Go compiler handles this natively

# Architecture

- `cmd/orchestr/` — Main binary entrypoint (daemon start, CLI commands)
- `internal/daemon/` — Background daemon lifecycle, single-instance lock, signal handling
- `internal/hotkey/` — Platform-specific hotkey capture (evdev, CGEventTap, RegisterHotKey, Wayland)
- `internal/registry/` — App registry: YAML config parsing, hot-reload, app state tracking
- `internal/api/` — Localhost HTTP API server (JSON, port 9876)
- `internal/launcher/` — App launching, PID tracking, bring-to-front, cross-env (WSL2)
- `internal/tray/` — System tray icon, minimal status menu
- `internal/gui/` — Management GUI (config editor, app table) — lightweight, infrequent use
- `configs/` — Default/example YAML configs

# Feature Lifecycle

1. **Ideate** — Human files a GitHub issue or describes the feature
2. **Scope** — Agent explores the codebase and writes `/specs/[feature-name].md` using the template
3. **Plan** — Agent decomposes the spec into `/tasks/[feature-name].md` (2–5 tasks)
4. **Test** — Agent writes failing tests for each acceptance criterion
5. **Implement** — Agent makes tests pass, one task per session
6. **Review** — A different agent or human reviews the PR

GitHub Issues are the human intake mechanism. Agents read issues but do not create, edit, or close them.
All agent-driven planning happens in local files (`/specs/`, `/tasks/`, `/decisions/`).

# Conventions

- Functions and variables: Go standard (`camelCase` local, `PascalCase` exported)
- Files: lowercase with underscores where needed (e.g., `hotkey_linux.go`)
- Build tags for platform: `//go:build linux`, `//go:build darwin`, `//go:build windows`
- Prefer explicit error handling — `if err != nil { return err }` over silent swallow
- No dead code — remove unused imports, variables, and functions
- Every exported function has a doc comment
- No hardcoded secrets, URLs, or environment-specific values
- Use `internal/` for all non-entrypoint packages (enforced by Go)

# Cross-Platform Strategy

- Platform-specific code isolated in files with build tags: `*_linux.go`, `*_darwin.go`, `*_windows.go`
- Shared interface per platform concern:
  - `hotkey.Listener` — platform-specific hotkey capture
  - `launcher.Executor` — platform-specific process launch and bring-to-front
  - `tray.Provider` — platform-specific system tray
- WSL2 bridging: daemon runs on Windows host; launches WSL apps via `wsl.exe -d <distro> -- <cmd>`

# Testing

- Write tests before implementation
- Place tests alongside source files using `_test.go` naming
- Use table-driven tests where multiple inputs test the same function
- Each acceptance criterion requires at least one test
- Do not modify existing tests to accommodate new code — fix the implementation
- Run the full test suite before committing
- Tests must be deterministic — no flaky tests in the main suite
- Platform-specific tests use build tags; CI matrix covers Linux, macOS, Windows

# Dependencies

- Minimize external dependencies — Go stdlib covers HTTP, JSON, YAML (with a small library), and OS interaction
- Hotkey capture will need platform-specific C interop (cgo) or syscall wrappers
- System tray: evaluate `getlantern/systray` or `fyne.io/systray`
- GUI: evaluate `fyne.io/fyne` for the minimal management interface
- YAML: `gopkg.in/yaml.v3`

# Planning

- Features with more than 3 implementation steps require a written plan
- Plans go in `/tasks/[feature-name].md` or as an ExecPlan per `/.codex/PLANS.md`
- Plans are living documents — update progress, decisions, and surprises as work proceeds
- A plan that cannot fit in 5 tasks indicates the feature should be split. Call this out.
- Small-fix fast path: if a change is <= 3 files and has no behavior change, a full spec/task lifecycle is optional; still document intent in the PR and run lint + relevant tests.

# Commits

- One logical change per commit
- Present-tense imperative subject line, under 72 characters
- Reference the spec or task file in the commit body when applicable
- Commit after each completed task, not after all tasks

# Branches

- Branch from the latest target branch immediately before starting work
- One feature per branch
- Delete after merge
- Never commit directly to the target branch
- Naming: `[type]/[slug]` (e.g., `feat/hotkey-engine`, `fix/pid-tracking`). Include the issue number if one exists: `feat/42-hotkey-engine`

# Worktrees

- Use git worktrees for concurrent features across agents
- Worktree root: `.trees/[branch-name]/`
- Each worktree is isolated: agents operate only within their assigned worktree
- Artifacts (specs, tasks, decisions) live in the main worktree and are shared read-only
- Never switch branches inside a worktree — create a new one

# Pull Requests

- Link to the spec file
- Diff under 300 lines; if larger, split the feature
- All CI checks pass before requesting review
- PR description states: what changed, why, how to verify

# Review

- Reviewable in under 15 minutes
- Tests cover every acceptance criterion
- No unrelated changes in the diff
- Cross-agent review encouraged: use a different model than the one that wrote the code

# Security

- No secrets in code or instruction files
- Use environment variables for all credentials
- Sanitize all external input
- Log security-relevant events
- HTTP API binds to localhost only (127.0.0.1) — never 0.0.0.0

# Agent Boundaries

- Agents do not create or modify GitHub issues, labels, milestones, or projects
- Agents do not push to main/master directly
- Agents do not modify CI/CD workflows without explicit human instruction
- Agents work within local files: specs, tasks, decisions, and source code

# Related Projects

- **espansr** — Espanso template manager (Python/PyQt6). First app to be orchestrated.
  - Connector spec: see `espansr/specs/espansr-orchestr-connector.md` in the espansr repo
  - Provides `orchestr.yml` manifest and `espansr status --json` for health checks
```

---

## Step 3: Copy feature specs

Copy the entire `espansr/specs/orchestr/` directory contents into `orchestr/specs/`:

```
espansr/specs/orchestr/01-core-daemon.md       → orchestr/specs/01-core-daemon.md
espansr/specs/orchestr/02-hotkey-engine.md      → orchestr/specs/02-hotkey-engine.md
espansr/specs/orchestr/03-app-registry.md       → orchestr/specs/03-app-registry.md
espansr/specs/orchestr/04-http-api.md           → orchestr/specs/04-http-api.md
espansr/specs/orchestr/05-cross-env-launch.md   → orchestr/specs/05-cross-env-launch.md
espansr/specs/orchestr/06-management-gui.md     → orchestr/specs/06-management-gui.md
espansr/specs/orchestr/07-installer-permissions.md → orchestr/specs/07-installer-permissions.md
```

Do NOT copy `META-PROMPT.md` — it's this file and is for bootstrapping only.

Do NOT copy `espansr/specs/espansr-orchestr-connector.md` — that belongs in espansr.

---

## Step 4: Write CI workflows for Go

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  ci:
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        go-version: ["1.22", "1.23"]
    runs-on: ${{ matrix.os }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-go@v5
        with:
          go-version: ${{ matrix.go-version }}

      - name: Lint
        uses: golangci/golangci-lint-action@v6
        with:
          version: latest

      - name: Test
        run: go test -race ./...

      - name: Build
        run: go build -o orchestr ./cmd/orchestr
```

Create `.github/workflows/copilot-setup-steps.yml`:

```yaml
name: "Copilot Setup Steps"

on:
  workflow_dispatch:
  push:
    paths:
      - .github/workflows/copilot-setup-steps.yml
  pull_request:
    paths:
      - .github/workflows/copilot-setup-steps.yml

jobs:
  copilot-setup-steps:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-go@v5
        with:
          go-version: "1.23"

      - name: Install dependencies
        run: go mod download

      - name: Validate environment
        run: |
          golangci-lint run ./...
          go test ./...
```

---

## Step 5: Write initial README

Create `orchestr/README.md`:

```markdown
# orchestr

A system-wide hotkey launcher and app orchestrator.

Press a leader key chord to instantly launch, focus, or cycle between your internal tools — across native apps, WSL2, and terminal sessions.

## Status

**Pre-development** — specs complete, implementation not started.

## Architecture

- **Daemon:** Background process with system tray, single-instance lock
- **Hotkey Engine:** Leader key (Ctrl+Space) + chord (single keypress) to trigger actions
- **App Registry:** YAML config defining apps, their launch commands, and health checks
- **HTTP API:** Localhost JSON API on port 9876 for programmatic control
- **Cross-Environment:** Launch native and WSL2 apps from the same daemon

## Specs

See `/specs/` for the complete design:

| # | Spec | Description |
|---|------|-------------|
| 01 | Core Daemon | Background process, system tray, lifecycle |
| 02 | Hotkey Engine | Leader key + chord capture, per-platform |
| 03 | App Registry | YAML config, hot-reload, app state |
| 04 | HTTP API | Localhost REST endpoints |
| 05 | Cross-Environment Launch | Native + WSL2 bridging |
| 06 | Management GUI | Minimal config editor |
| 07 | Installer & Permissions | Autostart, OS permissions, uninstall |

## Platforms

- Linux (X11 + Wayland)
- macOS
- Windows
- WSL2 (apps launched from Windows-side daemon)

## Related

- [espansr](https://github.com/josiahH-cf/espansr) — First app to be orchestrated. See its `specs/espansr-orchestr-connector.md` for the integration spec.

## License

[Choose license]
```

---

## Step 6: Initialize Go module and scaffold

```bash
cd orchestr/
go mod init github.com/josiahH-cf/orchestr
mkdir -p cmd/orchestr internal/{daemon,hotkey,registry,api,launcher,tray,gui} configs
```

Create a minimal `cmd/orchestr/main.go`:

```go
package main

import (
	"fmt"
	"os"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Println("orchestr — system-wide app launcher")
		fmt.Println("Usage: orchestr [start|stop|status|reload|version]")
		os.Exit(0)
	}

	switch os.Args[1] {
	case "version":
		fmt.Println("orchestr v0.0.0-dev")
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s\n", os.Args[1])
		os.Exit(1)
	}
}
```

Create `configs/example.yml`:

```yaml
# orchestr configuration
leader_key: "ctrl+space"
api_port: 9876

apps:
  - name: espansr
    description: "Espanso template manager"
    chord: "e"
    command: "espansr gui"
    ready_cmd: "espansr status --json"
    ready_timeout_ms: 3000
```

---

## Step 7: Create .gitignore

```
# Build
orchestr
*.exe
/dist/

# Go
vendor/

# IDE
.idea/
.vscode/
*.swp
*~

# OS
.DS_Store
Thumbs.db

# Agent personal config
CLAUDE.local.md

# Worktrees
.trees/
```

---

## Step 8: Initial commit

```bash
cd orchestr/
git add -A
git commit -m "Bootstrap orchestr repository

Scaffolding:
- AGENTS.md, CLAUDE.md, workflow docs adapted from espansr
- 14 Claude slash commands (generic workflow)
- GitHub templates (issues, PRs, CI, Copilot, reviewer agent)
- Go module, minimal CLI entrypoint, example config

Feature specs (from espansr design phase):
- 01: Core daemon and system tray
- 02: Hotkey engine (leader key + chord)
- 03: App registry and YAML config
- 04: Localhost HTTP API
- 05: Cross-environment launching (WSL2)
- 06: Management GUI
- 07: Installer and permissions

No implementation — specs only. Ready for Phase 2 (Plan)."
```

---

## Verification

After running this prompt, the orchestr repo should contain:

```
orchestr/
├── .claude/
│   ├── commands/           (14 generic workflow commands)
│   ├── settings.json       (Go-adapted hooks)
│   └── settings.local.json
├── .codex/
│   ├── PLANS.md
│   └── config.toml
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug.md
│   │   └── feature.md
│   ├── agents/
│   │   └── reviewer.md
│   ├── copilot-instructions.md
│   ├── pull_request_template.md
│   └── workflows/
│       ├── ci.yml          (Go CI — multi-OS, multi-version)
│       └── copilot-setup-steps.yml (Go setup)
├── .gitignore
├── AGENTS.md               (orchestr-specific — Go, daemon architecture)
├── CLAUDE.md               (generic session rules)
├── CLAUDE.local.md          (gitignored personal prefs)
├── README.md               (orchestr overview)
├── cmd/orchestr/main.go    (minimal entrypoint)
├── configs/example.yml     (example app config)
├── decisions/_TEMPLATE.md
├── go.mod
├── internal/
│   ├── api/
│   ├── daemon/
│   ├── gui/
│   ├── hotkey/
│   ├── launcher/
│   ├── registry/
│   └── tray/
├── specs/
│   ├── _TEMPLATE.md
│   ├── 01-core-daemon.md
│   ├── 02-hotkey-engine.md
│   ├── 03-app-registry.md
│   ├── 04-http-api.md
│   ├── 05-cross-env-launch.md
│   ├── 06-management-gui.md
│   └── 07-installer-permissions.md
├── tasks/_TEMPLATE.md
└── workflow/LIFECYCLE.md
```

**Zero espansr-specific content should exist in the orchestr repo.** The only reference to espansr should be:
- `AGENTS.md` → Related Projects section (link to espansr as first orchestrated app)
- `README.md` → Related section (link to espansr connector spec)
- `configs/example.yml` → espansr as an example app entry
