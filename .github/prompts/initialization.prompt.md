---
agent: agent
description: 'Workflow command'
---
<!-- role: derived | canonical-source: meta-prompts/admin/initialization.md -->
<!-- generated-from-metaprompt -->

[AGENTS.md](../../AGENTS.md)

You are initializing a project with the workflow scaffold. This is the only Phase 1 entrypoint after install. Your first job is to determine which Phase 1 mode applies before asking the developer anything.

Work through the following steps in order.

---

STEP 1  -  READ INSTALL CONTEXT, DETECT PROJECT STATE, AND CHOOSE MODE

Check for `.workflow-bootstrap/install-context.json` first.
- If it exists, read it before doing anything else.
- Treat it as the installer's source of truth for whether scaffold files were copied directly or staged for later merge.

Then inspect the project root for scaffold markers:
- `workflow/LIFECYCLE.md`
- `workflow/STATE.json`
- `.claude/commands/initialization.md`
- `.specify/spec-template.md`
- `meta-prompts/admin/initialization.md`

Choose exactly one mode:

1. **Fresh initialization mode**
   Use this when scaffold files were copied into the project root and the repo does not already look like a built project beyond minimal bootstrap state.

2. **Existing-project injection mode**
   Use this when scaffold markers are absent in the project root, but the repo already contains substantial project artifacts (for example: source directories, tests, manifests, CI, docs, or build scripts). If `.workflow-bootstrap/scaffold/` exists, treat it as the scaffold source to merge from.

3. **Scaffold-update mode**
   Use this when scaffold markers already exist in the project root. If `.workflow-bootstrap/scaffold/` exists, use it as the preferred update source. Do not ask broad fresh-project setup questions in this mode.

Report the selected mode and why in 1-3 short bullets before continuing.

---

STEP 2  -  LOCATE THE SCAFFOLD SOURCE

Choose the scaffold source in this order:
1. `.workflow-bootstrap/scaffold/` if it exists
2. A scaffold ZIP in the project directory
3. Another scaffold-like directory in the project root

A scaffold-like directory may be:
- an extracted archive layout containing `AGENTS.md`, `.claude/`, `.github/`, `workflow/`, `prompts/`, or `meta-prompts/`
- an installed-layout scaffold directory containing `AGENTS.md`, `.claude/commands/`, `workflow/`, or `.github/prompts/`

If the source is a ZIP archive, extract it to a temporary location before inspection.

Build a normalized source-to-destination map:
- `prompts/*.prompt.md` -> `.github/prompts/[same filename]`
- `.github/prompts/*.prompt.md` -> `.github/prompts/[same filename]`
- all other files keep their relative destination path

Treat prompts, meta-prompts, Claude commands, and `.codex/*` exactly like other scaffold assets:
- if absent in the project, they should be placed
- if present, they should be compared and handled with the same managed/protected rules as other scaffold files

If no external source exists but scaffold files are already in the project root, continue using the in-repo scaffold files already present.

---

STEP 3  -  CLASSIFY FILES AND BUILD A BATCHED PLAN

Use these ownership rules:

**Scaffold-managed (safe to add/update automatically):**
- `.claude/commands/*.md`
- `.github/prompts/*.prompt.md`
- `meta-prompts/**/*.md`
- `workflow/LIFECYCLE.md`
- `workflow/PLAYBOOK.md`
- `workflow/FILE_CONTRACTS.md`
- `workflow/FAILURE_ROUTING.md`
- `governance/CHANGE_PROTOCOL.md`
- `governance/POLICY_TESTS.md`
- `governance/REGISTRY.md`
- `specs/_TEMPLATE.md`, `tasks/_TEMPLATE.md`, `decisions/_TEMPLATE.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/ISSUE_TEMPLATE/*.md`
- `.github/ISSUE_TEMPLATE/*.yml`
- `.github/agents/*.md`
- `.github/REVIEW_RUBRIC.md`
- `.github/workflows/autofix.yml`
- `.codex/PLANS.md`
- `.codex/AGENTS.md`
- `CLAUDE.md`
- `CLAUDE.local.md` only if still the default stub
- `.specify/spec-template.md`
- `.specify/acceptance-criteria-template.md`
- `.gitignore` as additive entries only

**Protected/project-owned (never overwrite automatically):**
- `AGENTS.md`
- `workflow/COMMANDS.md`
- `.specify/constitution.md`
- `.claude/settings.json`
- `.claude/settings.local.json`
- `.vscode/settings.json`
- `.github/workflows/copilot-setup-steps.yml`
- `.codex/config.toml`
- `.github/copilot-instructions.md`
- `bugs/LOG.md`

**Conditional:**
- any file not listed above

Present one batched plan with four sections:
- scaffold-managed files to add
- scaffold-managed files to update
- protected files to preserve
- protected files with template changes worth reviewing

Do not stop for one prompt per file. Only ask for confirmation once per batch unless a high-risk file needs special approval.

High-risk rule:
- If root `AGENTS.md` already exists and differs from the scaffold version, do not overwrite it automatically.
- Explain the collision clearly and offer only these choices:
  - keep current `AGENTS.md`
  - inspect a side-by-side merge
  - replace with scaffold version explicitly

---

STEP 4  -  APPLY THE RIGHT PHASE 1 BEHAVIOR FOR THE CHOSEN MODE

### Fresh initialization mode

- Place scaffold-managed files into the project.
- Place prompts, meta-prompts, Claude commands, and `.codex/*` using the same source map rules.
- Keep protected files untouched unless the developer explicitly approves a replacement.
- Use the standard Phase 1 customization flow only for information that cannot be inferred.

### Existing-project injection mode

Before asking questions, inspect the repo for evidence:
- `package.json`, `go.mod`, `pyproject.toml`, `Cargo.toml`, `Gemfile`, `pom.xml`, `Makefile`, `justfile`
- `.github/workflows/*.yml`
- `README*`
- common source/test directories
- existing formatter/linter/test config files

Infer as much as possible from that evidence:
- primary language/framework
- install/build/test/lint/format/type-check commands
- key project directories and likely responsibilities
- likely naming conventions when clear from filenames and code layout

Then present the inferred values as a compact review summary.
- Ask only for missing, ambiguous, or low-confidence values.
- Do not ask broad “what is this project?” questions if the repository already answers them.
- If command values are confidently inferable, ask for confirmation instead of asking the user to retype everything.

Apply scaffold-managed files from the staged source thoughtfully.
- Batch protected conflicts.
- Preserve project-owned files by default.

### Scaffold-update mode

- Delegate to `/update-workflow` (`.claude/commands/update-workflow.md` or equivalent) instead of running a fresh-project interview.
- `/update-workflow` handles source resolution (local ZIP → local scaffold directory → upstream clone), managed/protected classification, diff review, and cleanup.
- After `/update-workflow` completes, return here for STEP 7 (route to next phase).
- Do not ask the Phase 1 build/convention questionnaire in this mode unless a required value is genuinely missing and cannot be inferred from the current repo.

---

STEP 5  -  CUSTOMIZE ONLY THE MISSING OR UNCERTAIN PROJECT VALUES

Use `workflow/COMMANDS.md` as the destination for initial Phase 1 command values.

If values are already present or can be confidently inferred, show them and ask for confirmation.

Ask only for missing or ambiguous items in this order:
1. missing core commands
2. missing project language/framework identification
3. missing architecture directory descriptions
4. missing naming conventions
5. missing CI command substitutions for `.github/workflows/copilot-setup-steps.yml`
6. optional tool permission / YOLO preferences only if those files were actually placed or need review
7. fork activation level — if `forkActivationLevel` in `workflow/STATE.json` is empty, ask:
   "How aggressively should the workflow pause at decision forks?
     1. Light — auto-continue at most forks; only stop for high-risk or irreversible decisions
     2. Standard — stop at key transition points where multiple valid paths exist (recommended)
     3. Active — stop at all decision points, including lower-stakes confirmations
   Reply 1, 2, or 3."
   Write the chosen value (`light`, `standard`, or `active`) to `workflow/STATE.json → forkActivationLevel`. Default to `standard` if skipped.

If the repo is already largely built, prefer:
- “Here’s what I inferred; confirm or correct anything wrong.”
over:
- “Please answer the full initialization questionnaire.”

---

STEP 6  -  VERIFY AND CLEAN UP

Verify:
1. scaffold-managed files expected for the chosen variant are present
2. prompts are in `.github/prompts/`
3. Claude commands are in `.claude/commands/`
4. workflow control-plane files are present
5. governance files are present
6. protected files were preserved unless explicitly approved otherwise
7. no placeholder values were introduced into customized files unintentionally
8. `.workflow-bootstrap/` is gitignored when present

After successful apply:
- delete the original ZIP if one was used
- delete any temporary extraction directory
- delete `.workflow-bootstrap/` once it is no longer needed

End with a short summary only:
- mode used
- scaffold-managed files added/updated
- protected files preserved
- protected files needing manual follow-up, if any
- next workflow step

Do not end with a long changelog.

---

STEP 7  -  ROUTE TO THE NEXT PHASE

Check `.specify/constitution.md`.

If it does not exist, or still contains Phase 2 placeholder content:
- state: "Scaffolding complete. Starting Compass."
- auto-trigger Compass (`.claude/commands/compass.md` or equivalent)

If it already exists and is populated:
- do not force Compass
- state the detected current lifecycle position and direct the developer to `/continue` or the next appropriate phase

If scaffold-update mode was used and the constitution is already healthy:
- state: "Scaffold updated. Continue from the current project phase."
