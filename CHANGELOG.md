# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- `:bring-back-feature` restores a feature that worked before recent changes
  broke it. It proves the known-good state, reproduces the loss, names the
  breaking change and what it intended, and restores the behavior as a forward
  fix with a regression guard, keeping newer work, other sessions' changes and
  history intact.
- `:core-behaviors` lists a project's core behaviors plus any others found or
  named, confirms them in exactly one numbered question round with
  recommendations, then fixes, protects and documents every confirmed behavior
  in one pass and re-verifies each at the end. A reply confirms only what it
  names ("approve: 1, 4"); recommendations apply only through "approve all" or
  "all except", and anything left out stays deferred and unchanged, so no core
  behavior is dropped without an explicit answer. `:stabilize` keeps its
  read-only architecture handoff.
- `:dedupe` audits an evolved project's code, tests, governance and docs for
  duplication and disagreement, recommends the current direction for each
  finding and changes nothing until you approve by number, then applies only
  the approved reconciliation and verifies it. The project's own instruction
  hierarchy decides which source controls; current behavior and recent changes
  are evidence, never authority, and unresolved intent conflicts are asked. `:prune` and `:friction` keep
  their jobs.
- `:article-flow-revision` revises an article on The Productive Prompter from
  your own feedback in a chat model. It confirms the article it read first,
  edits the article's revision source or the matching Article Flow export
  (`source.json` with `article.md`), keeps your exact words apart from its
  draft, and returns `source.json` unchanged with `candidate.md` and
  `feedback.md` for Article Flow to validate. Article Flow supplied the prompt,
  and it is bundled verbatim. Expanding it starts and publishes nothing.
- Bundled-note tests reject a trigger that is a prefix of another, which
  Espanso would expand before the longer trigger could be typed.
- **Local only** prompts: a checkbox in the editor (`"local_only": true` in the
  JSON) keeps a prompt out of everything espansr shares. It still expands and
  appears in `:coms` and `espansr list`, but `espansr push` never sends it to a
  template remote (and removes one shared before it was marked), `espansr sync`
  never commits or pushes it from the checkout, `scripts/deliver.py` refuses
  it, and the capability catalog that connected tools read as context never
  describes it, even with `publish_definition`. Before every push, the commits
  it would send are read version by version, merges included. A version that
  is local only, was marked local only, or is an earlier version of one under
  another name stops the push, and so does any staged version that is local
  only, however it was staged. espansr fails closed: a template that cannot be
  read, does not parse without the mark, or has a `local_only` other than true
  or false stops push, sync and delivery before anything is staged and is kept
  like a private file. Only espansr's own block of `info/exclude` changes,
  byte for byte, including in a linked worktree. `espansr pull` never replaces
  a local-only copy, import keeps the flag, and starter updates never
  overwrite, rename or retire one. Text you paste elsewhere, copies made with
  other Git tools, and history already shared are outside what it controls.

- Connected callers can discover the Meta-Prompt Generator's natural intent
  and consume its exact reusable definition from the qualified catalog. Source
  content requires explicit publication opt-in; inline drafting and explicit
  OA capture retain their separate contracts.

- `:sample` shows a concrete final-state projection using a representative
  input, with observed execution and hypothetical output clearly distinguished.
- `:user-journey` walks a finished or nearly finished project's requirements,
  documents its actual backend, and authors final-state refinement specs through
  its existing specification process. `:journey` retains its observed-use role.

- `espansr catalog` exposes versioned template/workflow descriptors, source and
  installed semantic/byte provenance, prompt-only versus declared executor
  routes, and local publication drift. Existing publish/setup retains the last
  complete catalog on failed qualification. Frozen private selections preserve
  exact definition bytes and caller context through restart and replay.

- `scripts/verify_prompt_receiver.py` runs one maintainer-only receiving-model
  sample with tools disabled, no plan mode and enforced time, text and budget
  limits. It reports run, execution, structural and semantic verdicts
  separately: tool-like text is never execution evidence, and a claimed side
  effect that the recorded events rule out fails.

### Fixed

- A capability publication that still describes a template now marked local
  only is withdrawn the first time espansr reads the catalog (`espansr catalog`,
  the `:coms` popup, a sync), not only at the next complete publish. No read
  returns it, filtered or otherwise; `espansr catalog` says `withdrawn`, and
  warns when the file could not be removed. A new selection from an older
  catalog is refused when the definition it would read is local only; jobs
  frozen earlier still replay unchanged.
- `espansr sync` pushes what your Git configuration pushes, and checks all of
  it first. It used to check one branch and push it alone. With
  `push.default=matching`, other matching branches were silently left
  unpushed, and with `remote.<name>.push` it pushed a branch the mapping did not
  name. Now Git's own dry run decides the refs, and every one is checked against
  what each push URL lacks; if any would send a local-only or unclear version,
  nothing is pushed and the ref, file and setting are named. The checked commits
  are pushed exactly, so a commit made during the check is not sent. A mirror
  remote, a configured deletion, or a ref that names no commit is refused with
  the reason.
- `espansr sync`, `espansr push` and `push --template` no longer send a private
  version to a push URL that lacks it. A `pushurl` naming another repository
  was checked against what the fetched remote had. Such a destination is now
  read with `git ls-remote`, and nothing is pushed when it cannot be read.
- `espansr push`, `push --template` and `espansr sync` read what a destination
  has from the destination itself, every time. After `espansr remote set`
  named another repository, origin's remote-tracking refs still described the
  old one, so history the new one lacked, earlier versions of a local-only
  template included, went unchecked and was sent. `sync` did the same with refs
  a narrow fetch refspec keeps out of pruning (a branch deleted on the remote,
  or one left from the previous URL). `push` fetches `origin` first, so commits
  it already has are still recognized, and `push` and `sync` suggest
  `git reset --soft` only to a ref the destination still has.
- Saving a template as local only (the editor, an import, a restore) withdraws
  a capability publication that still describes it at once, even when the sync
  that follows stops before it publishes.
- A template with a repeated `local_only` key stays local only. espansr read
  only the last value, so saving or importing such a template could make it
  shareable. Now it opens as local only and saves one exact `true`, and the
  catalog withdraws a publication that describes it.
- A template whose bytes are not valid UTF-8 is no longer read as shareable.
  espansr retried such bytes as Latin-1, so a local-only template left with one
  stray byte and no `local_only` key lost its exclusion, and `push` or
  `espansr sync` sent it. Now it stops push, sync and delivery like any file
  espansr cannot read, and its exclusion stays; one that still spells
  `"local_only": true` stays local only.
- `espansr validate` warns about a `local_only` that is not a single `true` or
  `false`. The Local only note no longer implies other programs cannot read the
  prompt: a program that reads the template folder itself still can.
  `docs/CAPABILITY_CATALOG.md` states the rule such a program must apply,
  since espansr cannot apply it for that program.
- Restoring an older version never makes a local-only template shareable, even
  from a template object loaded before it was marked.
- A private starter keeps its trigger in any folder: setup, refresh and publish
  no longer seed the public starter beside one moved into `personal/`, which
  also stopped Espanso publication with a duplicate trigger.
- `espansr pull --template` takes each name as one exact file in the store: a
  folder or a path outside it is refused before anything changes, `..` and
  absolute paths resolve to the file they name, and a Git pattern or pathspec
  (`personal/*.json`, `:(glob)...`, `:!...`) that names no file is refused
  before anything changes, so no spelling replaces a local-only template. The
  command names what it pulled, what it skipped as local only, and what the
  remote did not have, instead of counting every name as pulled.
- A full pull that Git stops while it still tracks a template you marked local
  only explains that and says your copy is unchanged.
- `scripts/deliver.py` commits only the listed paths, as documented (anything
  else already staged, such as a private template staged by hand, stays out),
  and reads the outgoing commits again right before pushing.
- `scripts/deliver.py` refuses an unpushed earlier version of a template kept
  private in `templates/` under another name (same trigger, capability ID or
  prompt text), as `push` does, whether the private copy is tracked or not and
  listed or not. It checked only versions that were marked themselves, so a
  draft committed before it was marked and then renamed could be delivered.
  `push` and `espansr sync` now also recognize earlier versions of a private
  template saved as UTF-16.
- `scripts/deliver.py` no longer stashes uncommitted changes outside its path
  list to catch up with `origin/main`. Its `rebase --autostash` replayed
  another session's edit and left a staged one unstaged. When the branch is
  behind and such changes exist, preflight now stops before committing and
  names them; with nothing else uncommitted, or when already up to date, it
  works as before.
- `scripts/deliver.py` writes its temporary commit message and pull request
  body as UTF-8, the encoding git and gh read them in. On Windows it used the
  system code page, so an emoji in the body (such as Claude Code's attribution
  line) stopped the delivery after the push and before the pull request was
  opened, and other non-ASCII text arrived garbled.
- Sync no longer says the last capability publication was retained when none is
  on disk.
- The live template listing skips `.git`, so copies a pull keeps there are never
  counted as templates.
- With **Remote paste** on, espansr now sets Espanso to bring your copied text
  back 2 seconds after an expansion instead of leaving the prompt on the
  clipboard; workstation mode keeps its 1.5-second restore. The delay is meant
  to outlast slow pastes but has not been measured over a real remote session;
  an app that pastes later than it pastes your copied text instead. On Windows,
  a remote-desktop host still on an earlier release's untouched settings gets
  the restore on its next Sync or reinstall, once, and the command prints how
  to opt out; clipboard timing tuned on a machine stays byte for byte, and
  `espansr doctor` names the command for any machine whose saved setting never
  restores. `espansr configure-remote-desktop --restore-delay MS` tunes or
  disables the restore per machine; Sync keeps the chosen delay, `0` included.
- A clipboard choice survives Sync and reinstall even when it matches an
  earlier release's defaults: blocks this release writes carry a
  `# espansr-defaults:` line, so `--auto` never resets them, including a hand
  edit such as `preserve_clipboard: false`.
- `configure-remote-desktop --auto --restore-delay MS` changes only the restore
  lines: the mode, other tuning such as `key_delay`, comments, and everything
  outside the block stay byte for byte, and an older single-marker file keeps
  its own values instead of today's defaults. An indented comment right after
  a restore value is kept too; it used to make espansr rewrite the whole block
  and drop the block's comments.
- `espansr sync` with changes Git does not stage (only local-only templates, or
  a dirty submodule) commits nothing and still pushes and reinstalls, instead of
  stopping at "Could not commit".
- On Windows Sync or reinstall, the older single-marker Espanso settings an
  earlier release wrote untouched are upgraded too: a host that restored after
  Espanso's 0.3 s or never, and a workstation whose 0.7-second restore large
  prompts outlasted, leaving the prompt on the clipboard. Tuned settings stay.
- `espansr configure-remote-desktop` and the **Remote paste** switch report the
  saved file and the Espanso restart separately and never claim what an
  expansion does. When `default.yml` cannot be read or written they say why and
  that the file was left as it was, and the command exits 1, `--auto` included
  (it used to report the old settings as kept). A saved file whose restart
  failed is a warning (exit 0), not a success.
- `espansr doctor` reports the clipboard restore saved in `default.yml` as a
  saved setting and names what it cannot observe: whether the running Espanso
  loaded it, app-specific overrides, and what an expansion does.
- The capability catalog no longer keeps a stale publication that still
  describes a template now marked local only when a later build is
  unqualified; it is withdrawn until the next complete publication.
- `espansr starters` lists your own templates that no starter manages as
  "Your own templates (not bundled)" instead of "Local-only templates", which
  now means the privacy setting.
- On WSL, the Windows-side Espanso folders are in the current user's exact
  profile folder: `%USERPROFILE%`, read through `cmd.exe /u /c set` so
  non-ASCII characters and an `&` arrive intact, and converted by `wslpath`. A
  non-ASCII user name no longer crashes every command, a profile not named
  after the user (`José.CORP`, a renamed account, another drive) is found, and
  a folder that only looks like the user's is never used or cleaned. When the
  profile cannot be established, no Windows-side folder is used; earlier
  versions took the only folder under `C:\Users` as the user's. Espanso is
  still found when Windows' PATH is not shared with WSL, and the orchestratr
  manifest uses the same folder. With drives mounted at a custom root
  (`/windows/c` instead of `/mnt/c`), the `:aopen`, `:coms` and `:sync`
  triggers written into that profile launch through `wsl.exe` as on `/mnt`,
  instead of Linux commands Windows Espanso cannot run, and a saved Linux
  Espanso path moves to that profile the same way.
- `install.sh` checks the libraries Qt itself links (`libegl1`, `libgl1`,
  `libfontconfig1`, `libxkbcommon0`) on Debian/Ubuntu and WSL, and warns when
  PyQt6 still cannot load, instead of reporting success for windows that
  cannot open.
- `espansr sync` checks every ref its push sends. With
  `push.default=matching`, a plain `git push` also sent other branches whose
  commits were never checked.
- `espansr sync` stops before pull, commit, push and reinstall when `git stash`
  saved the local changes but could not finish (a skip-worktree or
  assume-unchanged entry does this), and says where the changes are, instead
  of carrying on as if nothing had been stashed.
- `espansr push --template` commits only the files it names; other staged work
  stays staged instead of riding along under that commit message.
- Usage-count readers wait up to five seconds for the checkpoint lock instead
  of about half a second, which once failed CI on Windows. The wait is not
  free: every publication to Espanso (`espansr publish`, `setup`, `pull`,
  `retire`, and the window's Publish and Auto-publish) reads usage before it
  finishes. While another espansr process holds the lock, or when the lock
  cannot be taken at all, it pauses up to five seconds, and the window stops
  responding meanwhile, before it reports usage unavailable and finishes.
- The Linux CI matrix reports every Python version instead of cancelling the
  rest after the first failure.

- `:pmi-auth` delegates to the current registered PMI release's verified WSL
  entrypoint, preserving its credential reuse, profile serialization, attended
  challenges and exit status instead of embedding a second auth implementation.

- Receiving-model verification cleans its owned process group/job, including
  descendants left after leader exit, on completion, limits and exceptions.
  Saved-event evaluation rejects structured execution failures and malformed or
  conflicting terminal results even without a receipt, while retaining valid
  receipt-free success.

- Command search matches prefixes from the first character, including `a` and
  `i`, and focuses the search field whenever the command reference opens.

- Workflow discovery loads identical bundled and installed projections once,
  while still reporting conflicting content and renamed duplicate identities.

- Atomic writes use a short temporary sibling name so long backup paths that
  fit Windows' path limit also fit while being written. Final backup names,
  original bytes, atomic replacement and failure cleanup are preserved.

- Atomic writes of Espanso files retry briefly when Windows reports "Access
  is denied" because another process, such as Espanso reloading its match
  files, holds the destination open. A reinstall no longer fails on that
  momentary race. `scripts/deliver.py` now verifies that each changed
  template's Espanso expansion matches main, not only the installed copy,
  and no longer crashes printing installer output on a Windows code page.
- Windows Espanso restarts (`publish`, `setup`, `refresh`, `sync`) now start
  the daemon through WMI, outside the job object of whatever program ran
  espansr. A daemon started from an agent host, IDE, or similar app no longer
  stops, taking every trigger with it, when that app closes; `espanso restart`
  remains the fallback. `espansr doctor` warns on Windows when Espanso is not
  running or is running inside another program's process group.
- `:template-builder` and `:one-shot` run a named install operation such as
  a reinstall exactly as the project defines it instead of a lighter
  substitute, report the exact commands, and confirm that restarted services
  run independently of the session. `AGENTS.md` defines reinstall as
  `espansr refresh`.

- Installers now install or upgrade standard Espanso runtimes to 2.4.1+ so
  native usage counters work after installation. Windows and WSL share the
  official, checksum-verified per-user installer; Linux preserves existing
  X11/Wayland Debian packages or managed AppImages; macOS upgrades through
  Homebrew. Current runtimes skip downloads, custom installs get guidance,
  and explicit runtime opt-outs remain available on every platform. Failed
  downloads do not stop a working runtime. Usage version caching refreshes
  when the executable changes during an upgrade.
- Real runtime canaries on native CI verify Windows/Linux upgrades from 2.3.0,
  the macOS Homebrew route, statistics enablement and counter availability.

- Windows publish/reinstall verification reads Espanso's daemon directly,
  avoiding false restart warnings from its silent batch wrapper. Unix
  installers quote command aliases through both shell parsing layers and
  refresh stale aliases while preserving other shell settings. macOS uses
  the current Homebrew install route without the obsolete Espanso tap.
  Bash scripts retain LF line endings in Windows checkouts for WSL use,
  and macOS Bash correctly expands variables before Unicode punctuation.
- Native macOS CI and installer canaries on Linux, macOS, and Windows now
  exercise fresh installation, real Git pull/push and reinstall, bundled-note
  upgrades, custom-template preservation, and prompt copying in Qt.

### Added

- **PMI Auth** - `:pmi-auth` expands into one WSL Bash command for GitHub,
  Google CLI/ADC, and the canonical PMI Admin app. It reuses existing stores,
  invokes browser enrollment only when needed, verifies the exact app identity
  and Admin role, and preserves provider prerequisites and failure boundaries.
  Private account and origin values resolve from the PMI checkout at runtime.
  The command appears in quick help, docs, and the live command reference.

- **Meeting Actions** - `:meeting-actions` turns a Pocket meeting transcript
  into a concise meeting summary and supported action bullets for manual
  review and copying into Todoist. It preserves ownership, uncertainty, and
  the boundary between transcript data and instructions, and appears in the
  quick help, docs, and live command reference.

- **Unattended template delivery loop** — `scripts/deliver.py` is the one
	delivery route for every model: it commits only the listed paths, runs
	`pytest`, `ruff`, `black`, and the discovery check in a clean worktree,
	pushes, opens a pull request, waits for CI, squash-merges as `(#N)`,
	reinstalls with `espansr refresh`, and verifies with `espansr doctor` and
	installed-copy parity, stopping with a stage-specific exit code.
	`AGENTS.md` defines the loop (ask, clarify once, "go", implement, deliver,
	report, ask for the next change) and its house rules; `CLAUDE.md`
	authorizes running it unattended; `:template-builder` follows a project's
	own delivery loop and go-ahead word; `.claude/settings.json` allows the
	commands it needs; `black` is pinned to CI's 26.x; and a governance test
	keeps the rules in place.

- **`:one-shot` — end-to-end delivery in one pass** — takes a request typed
	after the trigger and, without questions, contextualizes it from project
	instructions and current state, plans internally, implements, verifies with
	the project's checks and a hunt for outliers and missing information,
	updates affected documentation, runs an adversarial review, and delivers:
	commit, push, pull request, merge once required checks pass, and the
	project's install or deploy step. In a plain chat the finished result is the
	deliverable. Project rules take precedence; it never force-pushes, bypasses
	protections, or merges failing checks, and it reports blockers instead of
	asking or guessing.

- **`:reverse-engineer` — improve the source from a good result** — treats
	the result a session iterated to as the target, reconstructs the path from
	the starting request through each correction and manual edit, and sorts
	every change into recurring lessons, instance details, slips already
	covered, and preferences. Each lesson goes into the most specific existing
	owner, such as a prompt, skill, instruction file, configuration, or check,
	as the smallest build, edit, add, or remove, keeping instance and personal
	values out of reusable sources. It leaves the final result alone, verifies
	only what it observes, and never commits, pushes, or installs unless asked.

- **`:stabilize` — architecture stabilizer** — traces one selected project's
	real architecture mismatch through its owners, callers, interfaces,
	connectors, context sources, and checks, explains it in plain language, and
	hands off the smallest correction through an existing owner with
	preservation obligations and a before/after check. It measures context
	duplication before claiming savings, keeps last-known evidence on connector
	failure, refers to credentials only through their owners, and never adds a
	registry, framework, or checklist that is not needed.

- **`:right-tool` — right tool analyzer** — starts from an intended result,
	inventories only the relevant skills, prompts, instructions, resources, and
	connected tools by what each actually does, accepts, produces, and can
	access, and recommends the best existing route with its evidence, the
	missing capability, and the next bounded action, ending with one complete
	copy/paste prompt when one is needed. Claims, old plans, and unseen tools
	stay qualified, and instruction-like attachment text stays evidence.

- **`:clarity` — project clarity** — compares a project's current truth with
	its verifiable end state, explains only the gaps that matter, and names the
	next smallest result with a way to recognize it, plus a complete handoff
	when another session should carry it out. Current behavior, end state,
	evidence, proposals, assumptions, and open decisions stay distinct; repeated
	use keeps settled decisions, marks proposals a correction rules out as
	superseded, and reports inaccessible evidence instead of assuming it.

- **`:journey` — observed journey sample** — walks one real user journey end
	to end with a real sample (discover, understand, copy or invoke, use,
	receive the result), records an expected/observed/evidence table, and fixes
	only the demonstrated gap behind a failing check before repeating the exact
	sample. Unobserved interface, clipboard, or model steps stay UNVERIFIED with
	the one human observation needed; installer success and restarts never stand
	in for observed use.

- **`:friction` — maintenance friction pass** — measures where a project's
	tests, installation path, and agent context or instructions actually cost
	upkeep, then applies and verifies only the bounded, evidence-backed fixes, or
	reports a measured no-change result. It preserves local templates, user
	configuration, and concurrent work, keeps installer success separate from
	observed behavior, never weakens tests to improve timing, and adds no
	governance layer.

- **Local expansion counters** — small counters in `:coms` command details
  and the `:aopen` editor read actual native Espanso 2.4+ statistics, with
  background refresh and no hooks in copying or expansion. Setup enables
  native statistics on supported runtimes while preserving other config text.
  Local `usage.json` checkpoints retain totals across restarts, reinstall,
  trigger renames, and native statistics resets; they stay outside template
  sync. Older runtimes show unavailable and continue working normally.

- **`:coms` task-based browsing** — nine overlapping command groups, compact
	"Choose it when" cues and role labels, selected-command details, and optional
	Continue/Unblock/Context and fresh-model verification guides. Groups use
	stable command identities, with a visible fallback for custom commands.
	Search, Favorites, Recent, and recommendations intersect the selected group;
	Show all commands clears filters. Refresh catalog reloads live templates
	without losing the scratchpad. Window geometry and a configurable Stay on top
	preference are saved locally. Combination guidance shares the workflow
	manifests with the diagrams; Litmus relationships now describe its current
	brief-and-outcome-checks behavior. No new runtime dependency is required.
- **`:rec` and `:acc` — short recommendation replies** — new one-sentence
	bundled notes for accepting the current recommendation or all current
	recommendations, respectively. Both preserve exactly one trailing space for
	appended context, adjustments, or item-specific exceptions and are surfaced
	in `:coms`, the `:espansr` quick help, and the template note list.
- **`:clarify-features` — iterative clarification and specification writing** —
	a new bundled prompt that contextualizes a batch of rough ideas or dictated
	notes, identifies and uses the project's native specification and agent-loop
	authoring mechanism, and asks as many console-only clarification rounds as
	needed. It accepts stream-of-consciousness speech-to-text answers, resolves
	material wording ambiguities, writes finalized specs once unblocked, validates
	native registrations, and asks for the next batch. Final specs default to
	project files with an explicit console-output override; projects without a
	native mechanism use simple Markdown specs. Surfaced in `:coms`, the
	`:espansr` quick help, and the `docs/TEMPLATES.md` note list.
- **`:playbook` — source-grounded, emoji-guided playbook builder** — a new
	bundled prompt that contextualizes around the user's current project or
	process, verifies the relevant instructions, asks only the necessary
	clarifying questions, and presents a simple, emoji-guided playbook directly
	in chat or the console, with plain-language steps and copyable commands,
	meta-prompts, or settings only where needed. Surfaced in the `:espansr`
	quick help and the `docs/TEMPLATES.md` note list.
- **`:canary-runner` — synthetic-data canary test with automatic cleanup** — a
	new bundled prompt that exercises developed work through a small, real run on
	synthetic inputs, reports the observed result, and then removes all
	attributable canary data across the locations actually used once the selected
	workflows pass or when cleanup is explicitly requested. A cleanup-only
	instruction removes the data without starting another run. Surfaced in the
	`:espansr` quick help and the `docs/TEMPLATES.md` note list.
- **`:fix-this` — context-first repair command** — a new bundled prompt that
	takes the issue already visible in the conversation and repository,
	investigates the underlying cause, plans and implements the repair, updates
	the downstream project material that repair affects, and finishes with exactly
	five plain-language bullets describing what actually happened. It is separate
	from `:troubleshoot`, which is unchanged. Surfaced in the `:espansr` quick
	help and the `docs/TEMPLATES.md` note list.
- **`:image-generator` — short-input image creation and editing** — a new
	bundled prompt that turns brief instructions and any supplied reference images
	into concrete visual direction, covering professional headshot, cartoon,
	photorealistic, and custom styles. It supplies explicit defaults for the
	Use/layout, Keep/avoid, and Words inputs and leaves Make/change and Style to
	creative intent, then generates or edits the image directly. Surfaced in the
	`:espansr` quick help and the `docs/TEMPLATES.md` note list.

### Changed

- `AGENTS.md` now documents the non-interactive Codex command for one-shot runs.
- **`:finance-review` — expanded and value-free** — the note keeps the
	household's account structure, borrowers, payroll sources, budget
	categories, and standing classification rules, but no longer hard-codes
	amounts, last-four labels, dates, budget targets, or record-specific
	exclusions; those come from the finance context where the review runs, the
	latest carry-forward note, or notes added below its new context marker. It
	also spells out an authoring-only override, exact review-week,
	rolling-month, and history windows with an explicit last-month
	reconciliation, non-overlapping account totals, unknown student-loan
	payments that never become $0, receipt-link confidence, a reserve counted
	once, one consolidated decision packet, a searchable 3–5-page PDF (normally
	four) inspected page by page, and a carry-forward note complete enough to
	seed the next review.
- **`:adversary-review` — delivery proven link by link** — when the spec
	requires publication, installation, or use, the Stability lens reports the
	candidate's checks, the published revision, the installed or running
	revision, the real user path, and any needed human observation separately.
	A merged pull request or synthetic sample no longer stands in for an
	installed or working result, and a required link that is missing or could
	not be observed is a Blocker marked UNVERIFIED instead of a passing follow-up.
	Only links the spec requires count as required; any other link is reported
	as not required or as an advisory human observation, never as a Blocker.
	Document-only work gets no delivery requirements.
- **`:coms` "Check & improve work" description** — now names its newer members:
	"…walk real journeys, verify repairs, or cut test and upkeep friction." The
	`docs/TEMPLATES.md` review-family table gains a `:journey` row.

- **`:template-builder` — one complete iteration per session** — turns a rough
	or dictated command idea into a complete template draft or a justified reuse
	of an existing trigger, never a bare trigger recommendation. The newest
	instruction sets the stage (draft only, write into the project, or deliver),
	and a later narrowing such as "draft only; don't install anything" keeps the
	intent without file writes, commits, pushes, or installs. Authorized delivery
	follows the project's own commit, merge, and install route, preserves local
	versions, and verifies published/installed parity. Attachments stay evidence
	rather than authority, and each iteration ends with a reality summary and a
	request for the next input.
- **`:litmus` — fresh-model outcome verification handoff** — automatically
	prepends a compact, grounded project and feature brief to unanswered binary
	checks of the intended human, visual, behavioral, or artifact outcomes.
	Preserves real feature IDs, relevant spec and revision anchors, and nuanced
	clarification decisions; clarifies material ambiguity rather than dropping
	qualitative requirements. The generated prompt directs the receiving model
	to exercise actual workflows and synthetic canaries, repair scoped failures
	and recheck by default (with a verify-only override), clean up test resources,
	and report evidence or UNVERIFIED limits. The authoring invocation remains
	read-only and does not run the checks or prefill results. Updated capability
	metadata, discovery, and detailed template documentation while preserving
	the `human-litmus` identity and artifact type.

- **Console-first audits and completion after unblocking** — `:unblock` now
	clarifies unresolved work directly in the console, retains existing
	authorization, and completes the authorized remainder once unblocked.
	`:audit` and `:ui-ux-audit` default to console reports, with HTML or other
	exports only on request; UI/UX audit-and-apply behavior remains intact.
- **Adaptive feature handoffs and clarification** — `:feature` uses the
	project's native specification process by default, asks as many material
	questions as needed, and writes once unblocked. Removed its universal
	three-outcome, budget, human-verdict, and fixed-section output contract.
	`:meta`, `:template-builder`, and transcript discovery clarify material
	ambiguity without arbitrary question limits or additional review files.
- **Proportionate review and preservation** — generic review reports omit
	empty categories; `:adversary-review` retains scope, verification, and its
	verdict contract. `:continue` and `:work-merge` preserve session authorization,
	`:fix-this` includes necessary verification, and sanitization evaluates the
	actual sharing boundary and file purpose instead of treating repository
	instructions, CI, prompts, or tool provenance as automatically private.
	Updated discovery descriptions and default output metadata, including
	explicit `:unblock` capability metadata.

- **`:project-personal-growth` — regenerated from the vault** — the note's body
	is again a projection of the vault's `Personal Growth - Meta-Prompt.md`
	(2026-09-02 revision): the active project is the one the tracker names,
	the Litmus Rules gain the explicit closure dispositions, the dependency-order
	constraint admits a logged closure disposition, and the Output Rules move in
	coherent batches instead of one question at a time. Metadata and the
	appended-notes footer are unchanged.
- **`:project-decision-helper` — dated value-model mirror** — the prompt now
	states that the vault's `Values Working System v1.md` is authoritative when it
	is accessible and that the embedded baseline mirrors it as of 2026-09-02 for
	use only when the vault is unavailable. The value model itself is unchanged.
- **`:reality-max` / `:reality-min` — explicit capability IDs** — both notes now
	declare `capability_id` values `reality-max` and `reality-min` instead of
	relying on the file-stem fallback, so consumers that do not derive IDs see the
	same identity `docs/PROCESS.md` lists. `:reality-max` also tells the user which
	other prompt or command to run next instead of naming espansr, keeping the
	body tool-neutral.
- **Claude Code hook** — the repository's `PostToolUse` hook runs `ruff check`
	on edited Python files instead of a `prettier` step that never applied to
	this Python project.
- **`:project-systems` — Coordinator and Watcher** — the note now carries the
	Master Systems Process coordinator-and-watcher prompt verbatim: continue
	authorized work without repeated “continue” prompts, load the vault context
	in a fixed order, name the actual execution and review roles and models,
	establish the unattended boundary, run the continuous working loop, classify
	blockers before escalating, observe and improve the process, keep
	documentation with its owners, and finish with the result, evidence, unknown,
	and next decision. It gains the standard appended-notes footer.
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
