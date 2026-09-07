# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Changed

- **Store reconciliation** — retires the unreleased `:git-sync-sh`/`:git-sync-ps`
	and `:refresh-espansr-sh`/`:refresh-espansr-ps` helper copies from installed
	template stores. `espansr sync` and the generated `:sync` trigger already
	provide the pull, push, and reinstall flow, so those notes were withdrawn
	before release.
- **Project metadata** — `pyproject.toml` now declares the author, and the
	LICENSE holder reads Josiah Hunter, matching the commit history.

## [1.2.0] — 2026-09-06

### Added

- **Windows launcher shim** — `install.ps1` writes
	`%LOCALAPPDATA%\espansr\bin\espansr.cmd` and appends that directory to the
	user PATH instead of the virtual environment's `Scripts` folder, so `python`
	and `pip` in new shells keep resolving to the user's own Python; legacy venv
	entries are removed, `doctor` reports the launcher, and Python detection also
	tries `py -3`.
- **External trigger collision warnings** — `espansr validate` warns when a
	trigger is also defined in another Espanso match file under `match/`.
- **Sync feedback** — after its commit `espansr sync` lists the committed files;
	the `:sync` trigger keeps its window open on Windows, opens a terminal (or logs
	to `sync.log` and calls `notify-send`) on Linux, and opens Terminal on macOS;
	a successful `espansr refresh` shows a balloon notification on Windows.
- **Test isolation and Windows CI** — autouse fixtures keep the suite off the
	real config directory, command shim, Espanso service, and template remote;
	CI adds a Windows job plus the discovery-sync and workflow-manifest checks;
	new tests cover bundled-note invariants, CLI error paths, GUI paths, and an
	Espanso YAML round-trip of every bundled note.
- **Bundled prompt notes** — 1.1.0 bundled only the `:espansr` quick help; the
	starter set now ships reusable AI prompt notes, each surfaced in the `:coms`
	popup, the `:espansr` quick help, and `docs/TEMPLATES.md`. Besides the notes
	with their own entries below (`:reality-max`, `:reality-min`,
	`:adversary-review`, `:continue`, `:project-systems`, and `:litmus`), the set
	contains:
	- `:project-init-llm` — initialize `AGENTS.md`-centered repo instructions for Codex, Claude, and Copilot.
	- `:feature` — turn feature intent into one implementation meta-prompt that drives architecture, behavior, and human-litmus verification outcomes, or a verified project-native flow on explicit request, stopping before implementation.
	- `:cb-transcript-feature` — turn a meeting transcript, notes, and answers into implementation-ready feature specifications through a structured question loop.
	- `:goal` — interpret, gap-check, clarify, and refine context into a tightly bounded, measurable goal.
	- `:show-me` — apply a standing operating standard to any task or corpus: ground in the real terrain, work outward in horizons, enrich with durable written context, and return actionable artifacts.
	- `:troubleshoot` — repair failures through context quality, bounded research, test-first fixing, verification, and affected-area review.
	- `:unblock` — diagnose and clear current blockers through evidence, bulk human input, and safe copy-paste actions.
	- `:verify` — fresh-context verification, repair, and documentation-alignment pass that fixes clear issues and summarizes remaining risk.
	- `:feedback` — apply current-cycle feedback and appended directives to the existing project, then verify the resulting changes.
	- `:docs-qa` — docs-only alignment pass for the work in the current context.
	- `:work-merge` — sanitize, verify, then merge and push only when the repository state is safe and unambiguous.
	- `:project-personal-growth` — session guide and record-keeper for the vault's Personal Growth program.
	- `:project-decision-helper` — read-only decision partner that frames the real choice and aligns it with your accepted values while you keep ownership.
	- `:git-yolo-sh` — Bash: commit current work, move dirty `main` work to a branch before updating `main`, and push with a `--force-with-lease` retry only for non-`main` branches.
	- `:git-yolo-ps` — the PowerShell version of `:git-yolo-sh`.
	- `:git-rebase-sh` — Bash: update `main` safely, move dirty `main` work to a branch when needed, rebase from `main`, and restore stashed changes after a clean rebase.
	- `:git-rebase-ps` — the PowerShell version of `:git-rebase-sh`.
	- `:git-branch-sh` — Bash: validate a branch name, update a clean `main` before branching, or move dirty `main` work onto the new branch and rebase it from the updated `main`.
	- `:git-branch-ps` — the PowerShell version of `:git-branch-sh`.
	- `:q&a` — evidence-bound Q&A session across the project, workspace, files, or connected context currently available.
	- `:explain` — faithful one-page explanation of the current context or a supplied source, with bullets and optional visuals.
	- `:visual` — workflow diagrams or visual explanations in the requested format and location.
	- `:gaps` — critical review switcher for gap review and first-principles analysis.
	- `:meta` — context-safe, scope-bound meta-prompt generator.
	- `:context` — condense drifting context into a standalone note in the seven handoff-packet sections.
	- `:template-builder` — draft or modify command templates by matching the existing project and command style.
	- `:sanitize` — assess sensitive or internal traces in a workspace and produce a recommendation-led cleanup plan.
	- `:research` — research a topic with strong evidence handling, clear synthesis, and explicit uncertainty.
	- `:audit` — turn incomplete project context into an interactive, self-contained HTML decision and audit packet.
	- `:html-help-doc` — turn project or process context into a self-contained interactive HTML help document and runbook with result tracking and model-ready copy-back.
	- `:ui-ux-audit` — audit every in-scope screen, flow, and state against a standalone usability baseline and produce an interactive recommendation workbench.
	- `:cb-agenda` — research project context and print one public-facing, email-ready meeting agenda in plain text.
	- `:telegram` — read an accessible source the user points to, infer its directive, and carry it out in the current context.
	- `:tddh` — concise reliability defaults: think deeply, verify facts, never invent information, and state uncertainty plainly.
	- `:listen` — rewrite research output as a listenable long-form article for text-to-speech.
	- `:revise` — clean up user-provided text for clarity while preserving meaning, tone, and direction.
	- `:cliche` — remove formulaic AI clichés and rewrite text in a natural, specific voice without changing its meaning.
	- `:pocket-extract` — PowerShell: extract each `.zip` into a folder named after it, remove the archive, and collect each folder's `transcription.txt` renamed after its folder.
	- `:tenable-scans` — PowerShell: unpack Tenable `.nessus` scan archives, renaming an existing destination folder with a timestamp suffix instead of deleting it, normalize the scan name, and copy the `.nessus` back to the root.

- **`:reality-max` and `:reality-min` — the comprehensive and the minimal
	reality account** — two bundled notes that report what the context created,
	would create, or leaves true, grounded only in reliable context and never
	performing the underlying work. `:reality-max` classifies its evidence
	(verified reality / proposed reality / supported inference / unknown),
	preserves the target material's own logic instead of silently repairing it,
	and returns a headed `# Reality Summary` opening with a bold "If you only
	read one thing" line and closing with `## ✅ Definition of Done`; its Visual
	Aids section adds grounded workflow or sequence diagrams, comparison tables,
	and count tables only where they make the reality easier to grasp, each
	marking unknown or proposed parts and never added to look complete, and its
	Format Principles keep the account scannable. `:reality-min` returns one or
	two sentences on what was done, is true, or would happen if unexecuted
	material ran as written, then at most ten plain `- ` bullets stating exactly
	what was done, fewer when fewer suffice; it invents nothing, adds no headings,
	tables, diagrams, emoji, or nested bullets, and gives no recommendations.
	Both carry checkable output contracts (the max contract accepts the takeaway
	colon inside or outside the bold and an optional emoji on the closing
	heading; the min contract accepts `-` or `*` bullets) and produce the
	`evidence-report` artifact. An interim `:reality` note with a fixed
	two-paragraph, zero-to-ten-bullet contract existed only between releases;
	its trigger is recorded in `replaces` and no longer expands (see Removed).

- **`:adversary-review` — independent adversarial review of finished work** — a
	new bundled note that reviews a unit claimed complete against its spec of
	record without fixing anything. It numbers the requirements and marks each
	Done, Partial, Missing, or Changed with evidence, runs the build, test, lint,
	and start-up checks itself instead of trusting the summary, traces collateral
	impact and every unrequested change, screens security, failure-mode, and
	rollback risk, lists loose ends, missing work, and missing tests, proposes the
	spec wording that would have prevented the drift, names due governance and
	documentation updates, and closes with a PASS, PASS WITH FOLLOW-UPS, or FAIL
	verdict derived from tagged severities. Registered as the `adversarial-review`
	capability in the feature delivery cycle, reachable after the handoff or after
	verification and feeding the feedback cycle, with a checkable output contract.

- **`:continue` — resume work already in flight** — a new bundled note that
	picks up an agentic or AI workflow in any context without the user having
	to restate it: it rebuilds the real state from evidence rather than from a
	summary, chooses and performs the next correct work, verifies each unit,
	and keeps going until the objective is met. When it is genuinely blocked it
	returns one light numbered CONTINUE CHECKPOINT and resumes automatically
	from the answer. Distinct from `:unblock`, which sweeps a whole field of
	blockers as its own job; `:continue` raises only the blocker in front of it
	and never treats "continue" as permission to commit, push, publish, or
	deploy. Revives the `:continue` trigger, previously retired with the pruned
	`feature_continue` note.

- **`:project-systems` — Master Systems Process runner** — a new bundled note
	that resumes the Master Systems Process from its owning files in the vault's
	System folder rather than from chat. It is the coordinator's entry prompt for
	one project-agnostic workflow that carries a real problem from first statement
	through scope, done criteria, planning, execution, use, measurement, and a
	clear next decision, with Finance as one proof project. A session reads the
	project page, the master document, and the touched current-state page in
	order, opens with a short plain-language orientation, continues work that is
	already authorized, and pauses only for a new unit, a material scope change,
	a missing human decision, or an exhausted approval. It names the coordinator,
	runner, reviewer, and owner roles, creates no tracker or side artifacts,
	discovers before asking, and finishes each run by writing accepted results
	back so the master alone states current reality and the next action.

- **Workflow diagrams in `:coms` and `:aopen`** — the process graphs are now
	drawn as interactive diagrams from the workflow manifests: the `:coms`
	Processes view shows the graph with per-node details and copy / scratchpad
	/ show-command actions, and the editor gains a Workflows panel (toolbar
	button or `Ctrl+Shift+W`) where clicking a node selects that template.
	Manifests may carry optional `x`/`y` layout hints on nodes and `short`
	arrow labels on edges; manifests without hints get a deterministic
	auto-layout. Loop edges draw in the accent color and "feeds any node"
	sources draw once, dashed.

- **Capability graph and process layer** — templates can carry additive
	capability metadata (`capability_id`, `intent_tags`, `accepts`, `produces`,
	`use_when`, `avoid_when`, `output_contract`); optional workflow manifests
	under `templates/_meta/workflows/` describe how capabilities relate
	(bundled: `evidence-research-cycle` and `feature-delivery-cycle`); the
	`:coms` popup gains fuzzy search, artifact selectors, Recommended /
	Processes / Recent / Favorites views, per-command guidance, and direct
	copy/scratchpad/packet/editor actions; handoff packets provide explicit,
	user-saved context transport (`espansr packet`); `espansr workflows`
	inspects and validates manifests; `espansr check-output` validates model
	output against a template's structural output contract; and the new
	standalone `:litmus` note authors plain-language human-verification
	checklists. The refined `:feature` note adds honest INPUT COVERAGE and an
	explicit CLARIFICATION STATUS while preserving its nine-phase handoff
	workflow. Everything is optional and local: every trigger works exactly as
	before, no workflow owns a current step, nothing runs automatically, and no
	metadata reaches generated Espanso YAML. See docs/PROCESS.md.

- **`:sync` trigger** — `espansr setup` now also writes `espansr-sync.yml`, a
	managed Espanso shell trigger that runs `espansr sync` through the console
	entry point so its progress shows in a window (through `wsl.exe` for a WSL
	install whose Espanso runs on Windows). The keyword is `espanso.sync_trigger`
	in the espansr config (default `:sync`); `espansr validate` warns when a
	template reuses it, and the `:coms` catalog lists it as a system entry beside
	`:aopen`.

- **Remote-desktop and workstation Espanso tuning** —
	`espansr configure-remote-desktop` edits Espanso's `config/default.yml` for
	the machine's role and restarts Espanso, and `install.ps1` runs it on every
	Windows install: with no switch it passes `--auto`, which applies workstation
	tuning unless the file already carries the espansr remote-desktop host
	marker, so a declared host stays a host across reinstalls and
	`espansr refresh`; `.\install.ps1 -RemoteDesktop` applies host mode and
	`-LocalOnly` forces workstation mode. Host mode (the plain command) sets
	`win32_exclude_orphan_events: false` so Espanso stops discarding the
	software-injected keystrokes RustDesk/RDP deliver (the fix for triggers that
	never fired over a remote session), switches to the `Clipboard` backend with
	`preserve_clipboard: false` so an asynchronous paste cannot restore the
	previous clipboard over the expansion, sets `key_delay` and `backspace_delay`
	to 30, and quiets the tray icon and notifications. Workstation mode
	(`--local`) clears those host keys and sets
	`win32_exclude_orphan_events: false`, `preserve_clipboard: true`, and
	`restore_clipboard_delay: 1500`, so large templates, which paste through the
	clipboard, win the paste race while the user's clipboard is restored after
	the target app has released it. `--revert` removes the host-mode keys, and
	only those still holding the value espansr wrote; every key espansr does not
	own is left untouched in all modes.

- **PATH-visible `espansr` command shim** — `espansr setup` now makes sure a
	real `espansr` executable exists in the user bin directory: on Linux, macOS,
	and WSL2 a symlink at `~/.local/bin/espansr` to the venv's executable (a
	small wrapper script where symlinks are unsupported), and on Windows the venv
	`Scripts` folder that `install.ps1` persists to the user PATH. The command
	therefore resolves in non-interactive shells — subprocess calls, `.desktop`
	launchers, systemd user units, IDE terminals, and RustDesk/RDP session
	shells — where a shell alias never does. `espansr setup --force-shim`
	overwrites a stray non-symlink file blocking the shim path,
	`espansr doctor` reports the shim (creating it when missing) and warns when
	the bin directory is not on PATH, and both installers run a
	non-interactive resolution check before their smoke test.

- **Single-source discovery surfaces** — `espansr/core/discovery.py` is the
	one place bundled notes, CLI rows, and system triggers are registered;
	`python scripts/sync_discovery.py` renders it into the `:espansr` quick help
	(`templates/espansr_help.json`) and the generated note list in
	`docs/TEMPLATES.md`, `--check` reports drift, and
	`tests/test_discovery_sync.py` fails when a bundled trigger is missing from
	either surface, when a pruned trigger reappears, when a CLI subcommand has no
	quick-help row, or when a system trigger has no Discovery row.

- **Git-backed remote template sync** — `espansr remote set|status|remove`
	configures a Git remote for the live template store; `espansr pull` pulls it
	(optionally `--template NAME`) and refreshes Espanso output, reporting
	whether files were updated, templates were already up to date, the remote was
	empty, Git was unavailable, or the remote could not be reached;
	`espansr push` commits and pushes template JSON (`--template`, `--message`);
	the GUI gains **Pull Latest**; and `list`, `validate`, `doctor`, and `gui`
	pull first when a remote is configured and `remote.auto_pull` is on (the
	default), logging rather than failing when that pull cannot run.

- **`espansr publish` and `espansr starters`** — `publish` writes the managed
	Espanso output (`--dry-run` previews it) and first applies missing or
	changed bundled starter updates to the live store, backing up a changed
	local copy under `_versions/`; `starters` reports bundled drift (exit 1 when
	drift exists) or applies it with `--apply` (`--dry-run`, `--verbose`, and
	`--force` to replace invalid bundled-matching local JSON after backing it
	up), migrating renamed starters and retiring old ones while preserving
	local-only templates.

- **`espansr wsl-install-espanso`** — WSL2-only helper that runs PowerShell on
	the Windows host to install Espanso with `winget`, start it, and verify its
	config directory; when it cannot verify a complete install it exits 1 with
	an action-required checklist.

- **orchestratr connector** — `espansr status --json` prints machine-readable
	status for orchestratr health checks, and `espansr setup` writes or refreshes
	an `espansr.yml` manifest in the orchestratr apps directory when orchestratr
	is found (skipping registration otherwise).

- **`install.sh` provisions Espanso and XWayland app overrides** — on Linux and
	macOS the installer now installs Espanso when it is missing (the upstream X11
	`.deb` on apt distros, the X11 AppImage at `~/.local/bin/espanso` otherwise
	with an extract-and-run wrapper when FUSE is unavailable, or
	`brew tap espanso/espanso && brew install espanso` on macOS), seeds
	`config/default.yml` with `show_icon: false` and `show_notifications: false`
	when that file does not exist, and starts the daemon through a user systemd
	unit it writes itself on Linux or `espanso service register` and `start` on
	macOS. On a GNOME/Wayland session it offers once to force Chrome, VS Code,
	Obsidian, and gnome-terminal under XWayland (user-owned `.desktop`
	overrides, a `~/.local/bin/code` wrapper, and a systemd user drop-in for
	`gnome-terminal-server.service`), installing a revert script reachable as
	`espansr-revert-xwayland-apps`. Opt out with `--no-espanso`
	(`ESPANSR_NO_ESPANSO=1`) or `--no-xwayland-apps`
	(`ESPANSR_XWAYLAND_APPS=no`), or apply the overrides unattended with
	`--yes-xwayland-apps` (`ESPANSR_XWAYLAND_APPS=yes`); WSL2 installs skip the
	Espanso install and point to `espansr wsl-install-espanso`.

- **In-place reinstall command** — `espansr refresh` identifies the OS and the
	recorded install location, then reruns the correct installer (`install.ps1`
	via PowerShell on Windows, `install.sh` via Bash on Linux/macOS/WSL2). It
	prints a small `ok` notification on success and opens the install folder if
	the reinstall fails. The installers now record this location via
	`espansr record-install` (stored as `install.json` in the config directory).
- **Commands popup scratchpad** — the `:coms` popup now includes an ephemeral,
	expandable scratchpad pinned at the bottom where you can type or paste any
	command, add context, and copy it back out. The scratchpad is throwaway and
	never saved.
- **Commands popup trigger** — espansr now generates an `espansr-commands.yml`
	file with a hardcoded `:coms` trigger that opens a lightweight read-only
	popup showing available Espanso triggers, descriptions, and output previews.
- **Template retirement command** — `espansr retire TARGET` backs up a live
	template, deletes the JSON file, and refreshes managed Espanso output.

### Changed

- **Espanso `default.yml` is edited as text** — `espansr configure-remote-desktop`
	owns one marked block (`# espansr-managed BEGIN ... END`), preserves every
	other byte of the file, records overridden keys as `# espansr-prev:` lines
	that `--revert` restores in both modes, keeps a one-time
	`default.yml.espansr-orig` backup, and migrates files written by the old
	layout; the mode flags are mutually exclusive.
- **`espansr status` exit code and help** — exits 1 when no Espanso config
	directory is found; a missing binary is a warning; the help text now says
	what it shows.
- **`espansr setup` reports failures** — each generated file prints generated,
	skipped, or failed, and setup exits 1 (stopping the installers) when Espanso
	is present and the publish or a generated file failed.
- **WSL scope** — detection and cleanup of Windows-side Espanso files only
	look at the current Windows user's profile.
- **`espansr sync` repurposed as the one-button update** — in 1.1.0 `sync`
	published templates to Espanso; that job is now `espansr publish` (with
	`--dry-run`). `espansr sync` resolves the repository folder and installer
	from the recorded install metadata, runs `git fetch --prune` and
	`git pull --rebase` (stashing uncommitted work first and restoring it
	afterwards), then, unless `--no-push` is given, stages everything
	(`git add -A`), commits with the fixed message `espansr sync: local changes`,
	and pushes when the branch is ahead of its upstream, and finally reruns the
	recorded installer. On a rebase conflict it aborts the rebase, restores the
	stash, lists the conflicted files, and skips the reinstall so a broken tree
	is never reinstalled; a checkout that is not a git work tree, or a failed
	fetch, reinstalls the current checkout without pulling or pushing.
	`--no-push` pulls and reinstalls only. The GUI toolbar gains a **Sync**
	button that runs the same flow and refuses to start while the editor has
	unsaved changes.

- **`:feature` output contract checks the final artifact only** — the contract
	now requires the `FINAL IMPLEMENTATION META-PROMPT` and `REALITY SUMMARY`
	sections, at least one `If this was built correctly:` entry with
	`Model verdict:` and `Human verdict:` fields, and the `ALL_GATES_GREEN` and
	`BUDGET_EXHAUSTED` terminal states, and still fails any output whose human
	verdicts were prefilled. The approval-round packet is a checkpoint the
	contract never checks, and the note says so beside the packet; run
	`espansr check-output` on the reply that follows your approval.

- **`:meta` stays within the requested scope and silent on gaps** — the
	meta-prompt generator gained Scope Rules: the request defines the scope,
	quality words and "etc." never add work, no unrequested checks, tests,
	features, or designs are introduced, the narrower reading of an ambiguous
	phrase wins, and the same boundary is written into the drafted prompt. It
	now recognizes whether it runs in a fresh chat (the notes are the whole
	brief) or inside a project (read-only inspection to ground names and
	constraints, never to widen the task), and when the input leaves something
	out it neither fills the gap nor mentions it — gap, unknown, and assumption
	callouts are excluded from the draft. With blank notes and no connected
	context it returns exactly `No task supplied to draft from.`

- **Bundled notes and discovery surfaces after adversarial review** — the
	`:espansr` quick help gains CLI rows for `sync`, `doctor`, `workflows`,
	`packet`, `check-output`, `completions`, `wsl-install-espanso`, and
	`configure-remote-desktop`, Discovery rows for `:aopen` and `:sync`, and a
	footer naming the Linux/WSL, Windows, and macOS config paths. Capability
	metadata now covers `:troubleshoot` (`troubleshooting`),
	`:cb-transcript-feature` (`spec-discovery`), `:audit` (`audit-packet`), and
	`:ui-ux-audit` (`experience-audit`); `:reality-max` and `:reality-min`
	produce `evidence-report`; `:verify` accepts `verification-report`; and the
	manifests gain the `visual-workflow → html-help-doc`,
	`goal-refinement → human-litmus`, and `feature-handoff → human-litmus`
	edges. `:context` now emits the seven handoff-packet sections (Objective,
	Confirmed facts and evidence, Decisions, Assumptions, Material unknowns,
	Evidence references, Candidate capabilities) with `(none)` under empty ones
	and no front matter. `:verify`, `:sanitize`, and `:work-merge` gained the
	standard appended-notes footer and `:verify` lost its yolo ship section;
	`:project-systems` lost its `:unblock` aside and its Entry points section
	now states that the master owns the shortcut's verification state;
	`:reality-max` replaced "Relationship to show-me" with "Format Principles";
	`:gaps` lost its example callouts, keeps one optional callout area, and is
	filed under review, as is `:docs-qa`; `:git-yolo-sh` no longer uses `set -e`
	and guards every step with `return 1`; `:tenable-scans` renames an existing
	destination folder with a timestamp suffix instead of deleting it;
	`:cliche` is addressed as `cliche` and returns `No text available to edit.`
	when it finds nothing to edit; `:meta` returns `No task supplied to draft
	from.` on blank input with no context; `:project-decision-helper` ships its
	intake fields blank and defines the `auto` depth; `:show-me` sweeps only
	when a corpus is in scope; `:cb-agenda` has a compact research checklist;
	`:explain`, `:unblock`, `:audit`, and `:html-help-doc` state their
	boundaries (`:explain` points to the reality account for a bare end state,
	`:unblock` hands back once the path is clear, and the two HTML notes name
	the decision-packet versus runbook split); and the `:work-merge` and
	`:reality-min` blurbs now read "sanitize, verify, then merge and push only
	when the repo state is safe" and "one or two sentences and up to ten bullets
	on exactly what was done".

- **`:coms` "Prompt to scratchpad"** now places the command's full prompt in
	the scratchpad (previously only the trigger); system entries without a
	prompt body still insert their trigger.
- **Default theme is now Dark** — the GUI and `:coms` popup default to dark mode
	everywhere. Light mode must be explicitly selected from the toolbar theme
	selector (Auto/Dark/Light).
- **Windows vs WSL install guidance** — installer output and user docs now make it explicit that Windows PowerShell and WSL are separate environments with separate PATH, shell integration, and `espansr` installs.
- **Windows installer startup check** — `install.ps1` now verifies Espanso startup registration and starts the service when possible, so native Windows installs do not rely on an implicit prior Espanso boot configuration.
- **Publish-first wording** — README, verification docs, installers, and quick
	help now present `publish` as the primary local Espanso output command and
	keep `sync` only as legacy compatibility wording. The `sync` name has since
	been repurposed as the one-button update described above.
- **Contributor rules, release workflow, and repository scaffolding** —
	`CONTRIBUTING.md` now follows the `AGENTS.md` branch naming (`agent/` or
	`user/` plus `type-short-description`), documents the discovery-sync step
	and the rule that every user-visible change gets an Unreleased changelog
	entry, and no longer references a PR template that does not exist;
	`.codex/AGENTS.md` treats bundled prompt notes as default work like the
	other rules files; the release workflow validates the tag as semver, uses
	its `version` input on manual dispatch, and takes release notes from the
	matching `CHANGELOG.md` section when it exists, falling back to the commit
	log; the monthly docs-compliance workflow checks all eight baseline
	documents; dead entries were dropped from `.aiignore`, the Markdown
	duplicates of the issue templates were removed, and the agent-task issue
	template's placeholders use Python paths.
- **Local `pytest` runs GUI tests offscreen** — `tests/conftest.py` sets
	`QT_QPA_PLATFORM=offscreen` by default (an explicit value still wins),
	matching CI, so the PyQt6 suite no longer pops windows or steals focus.

### Removed

Every trigger below existed only on `main` between 1.1.0 and this release
(1.1.0 bundled only `:espansr`). None expands any more, and
`tests/test_discovery_sync.py` keeps them out of the discovery surfaces.

- **Replaced triggers** (each recorded in its successor's `replaces` field):
	`:project-init` → `:project-init-llm`; `:qa` → `:docs-qa`; `:critique`,
	`:gaps-2`, `:principles`, and `:fp` → `:gaps`; `:plain`, `:dumb`,
	`:simplify`, `:explain-1`, `:distill`, and `:summarize` → `:explain`;
	`:hide-ai` → `:sanitize`; `:defaults` → `:tddh`; `:pocket-note` →
	`:telegram`; `:work-merge-safe` → `:work-merge`; `:reality` →
	`:reality-max` and `:reality-min`. `:humanize` was renamed `:cliche`.
- **Pruned without replacement** — `:feat-plan`, `:feat-runner`, `:feat`, and
	`:agent-scaffold` (the feature-loop system retired when the standalone
	`:feature` arrived), `:feedback-loop` (persistent feedback capture; the
	bounded `:feedback` does not revive it), `:merge` and `:rebase` (the
	`:work-merge` and `:git-rebase-*` helpers remain), `:save`, and `:pocket`
	(renamed `:pocket-system`, then pruned).

### Fixed

- **Installer hang after the first publish** — the Espanso daemon spawned by
	`espanso restart` inherited the command's output pipes, so `espansr setup`
	never returned; restart and service commands now run detached from output
	pipes and the restart is verified through `espanso status`.
- **Espanso config no longer round-tripped through YAML** — comments and
	values such as `toggle_key: OFF` are no longer lost or retyped by the
	remote-desktop configuration.
- **Installer checks** — `install.ps1` starts Espanso before running setup,
	anchors its service-state matching so `not running` is no longer read as
	running, uses the real exit code of timed-out checks, refuses
	`-RemoteDesktop` with `-LocalOnly`, and probes a reused venv before trusting
	it; `install.sh` tries python3.14 and python3.13 first, kills only the
	exact `espanso` process, and warns instead of reporting success when
	`espansr status` fails.
- **Sync failure handling** — a failed stash restore, a failed commit, a
	missing upstream, and git timeouts each stop `espansr sync` with a clear
	message instead of pushing a partial tree or a traceback.
- **Console and file robustness** — CLI output no longer crashes on characters
	the console cannot encode; the Espanso match, launcher, popup, sync, and
	config files plus `config.json` and `install.json` are written atomically;
	remote URLs with embedded credentials print masked.
- **WSL install hint** — `espansr wsl-install-espanso` now says to run `setup`
	before `doctor`.
- **`:project-systems` entry point** — the note's Entry points section now
	states that the master owns the shortcut's verification state instead of
	claiming the shortcut is pending alignment against a missing tracker.
- **Retired-template local cleanup** — publishing now removes stale managed
	`espansr.yml` output when no triggered templates remain.
- **GUI delete publishing** — deleting a template from the GUI now publishes the
	remaining templates after the undo window closes.
- **Windows installer compatibility** — `install.ps1` no longer uses
	PowerShell 7-only syntax while declaring PowerShell 5.1 support.
- **WSL candidate path probing hardening** — `espansr doctor` and GUI startup no longer crash when unreadable Windows profile paths exist under `/mnt/c/Users/*`. Unreadable candidate directories are now skipped with warnings so canonical Espanso path detection continues.
- **WSL launcher regeneration reliability** — rerunning `espansr setup` now refreshes the generated `espansr-launcher.yml` safely for Windows-hosted WSL Espanso configs, so the `:aopen` launcher trigger can recover from stale launcher output without manual YAML edits.
- **Windows launcher console suppression** — the generated native Windows `:aopen` launcher now prefers `pythonw.exe` and no longer opens an extra console window when it starts the GUI.
- **First-publish install gap** — `espansr setup` now performs an initial publish when Espanso is detected, so bundled triggers like `:verify` are available immediately after install instead of waiting for a manual save/publish cycle.
- **Stale bundled starters retired at setup** — the initial publish that
	`espansr setup` runs now applies bundled updates (`update_bundled=True`), so
	renamed or retired starters are migrated or retired on install and reinstall
	instead of lingering as stale triggers in `:coms`, with a changed local copy
	backed up under `_versions/` first; the `:coms` catalog also rebuilds its
	template manager on every build so a long-running process reflects the
	current template directory.
- **Atomic template writes** — template JSON, version backups, and bundled
	template copies are written to a temporary file in the destination directory,
	flushed, and swapped in with `os.replace` (`espansr/core/atomic.py`, PR #77),
	so an interrupted save can no longer leave a truncated template behind.

## [1.1.0] — 2026-03-01

Completes the v1.0 feature roadmap with the test suite passing.

### Added

- **Shell Tab Completion** — `espansr completions bash` and `espansr completions zsh` generate shell completion scripts from argparse introspection. `install.sh` prints a sourcing hint after install.
- **`espansr doctor`** — Diagnostic command that checks Python version, config dir, templates, Espanso config, binary, launcher file, and template validation. Returns exit 0/1.
- **CLI Dry-Run and Verbose Modes** — `espansr sync --dry-run` and `espansr setup --dry-run` preview changes without writing. `espansr setup --verbose` shows per-file detail. Flags are combinable.
- **Colored CLI Output** — `ok()`, `warn()`, `fail()`, `info()` helpers in `cli_color.py` with TTY detection and `NO_COLOR` support. Applied to doctor, status, validate, and setup output.
- **Setup and Platform Resilience** — Bundled template path fallback to `importlib.resources`. `espansr setup --strict` returns 1 if Espanso not found. Bundled templates validated during setup. Platform config caching with `@lru_cache`.
- **GUI Status Bar and Sync Feedback** — Permanent status indicator showing Espanso config path. Sync result messages with template count or error details.
- **GUI Template Preview Pane** — Live output preview that substitutes variables with defaults, labels, or formatted dates.
- **GUI Dark/Light Mode** — Auto-detection via `QStyleHints.colorScheme()` with `QPalette` luminance fallback. Runtime theme switcher (Auto/Dark/Light) in toolbar.
- **GUI Keyboard Shortcuts** — Ctrl+S sync, Ctrl+N new, Ctrl+I import, Ctrl+F search, Delete/Ctrl+D delete. Platform-native key sequences.

## [1.0.0] — 2026-02-28

First public release.

### Added

- **Template Import** — `espansr import <path>` CLI command and GUI toolbar button for importing external template JSON files or directories. Strips unrecognized fields, de-duplicates names with numeric suffixes.
- **Espanso Config Validation** — `espansr validate` CLI command with six validation rules (empty trigger, short trigger, bad prefix, unmatched placeholders, unused variables, duplicate triggers). Sync blocks on errors, proceeds with warnings. GUI surfaces validation messages in the status bar.
- **Espanso Launcher Trigger** — `generate_launcher_file()` writes `espansr-launcher.yml` with a shell trigger to open the GUI from Espanso. WSL2-aware command construction. Configurable trigger keyword.
- **Inline Variable Editor** — `VariableEditorWidget` with add/edit/delete rows, name validation, date-type format field, form-type multiline toggle, and live YAML preview.
- **GUI Single-Screen Layout** — Splitter-based browser/editor layout with toolbar (Sync Now, auto-sync toggle), inline template editor, inline delete confirmation, and window geometry persistence.
- **Cross-Platform Installer Architecture** — `PlatformConfig` dataclass as single source of truth for all platform-specific paths. `espansr setup` CLI command performs all post-install work. `install.sh` restructured to a thin bootstrap that delegates to `espansr setup`.
- **Windows Installer** — `install.ps1` PowerShell script (5.1+ compatible) with Python version check, venv creation, and delegation to `espansr setup`.
- **Bundled starter template** (`espansr_help.json`) copied on first install.
- **`espansr --version`** flag prints the installed version.
- **CI pipeline** with Ruff lint, Black format check, and pytest across Python 3.11, 3.12, 3.13.

### Changed

- **WSL/Platform Utility Module** — All platform detection consolidated into `espansr/core/platform.py` (`get_platform()`, `is_wsl2()`, `get_windows_username()`). Callers no longer read `/proc/version` or call `cmd.exe` directly.
- **Espanso Path Consolidation** — `get_espanso_config_dir()` persists resolved path to config. `clean_stale_espanso_files()` removes managed files from non-canonical directories. All Espanso candidate paths defined once in `PlatformConfig`.
- **`espansr status`** shows platform-specific guidance when Espanso is not found.

## [0.1.0] — 2025-01-01

### Added

- Initial standalone build with template CRUD, JSON storage, Espanso YAML generation.
- CLI interface (`sync`, `status`, `list`, `gui` commands).
- PyQt6 GUI with template browser and editor.
- WSL2 support for Windows-side Espanso config detection.
