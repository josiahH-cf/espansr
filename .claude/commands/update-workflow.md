<!-- role: derived | canonical-source: meta-prompts/admin/update-workflow.md -->
<!-- generated-from-metaprompt -->
You are updating an existing project's development scaffolding. This project was previously initialized with the scaffold  -  its files are already in place and have been customized. A new version of the scaffold source has been placed in this project directory. Find it.

Work through the following steps in order.

---

STEP 1  -  LOCATE, DETECT SOURCE KIND, DETECT VARIANT, AND INVENTORY

Find the scaffold source using this resolution order (first match wins):

1. **Local ZIP archive** — prefer a scaffold ZIP if one exists in the project root.
2. **Local scaffold-like directory** — accept one scaffold-like directory candidate inside the project root.
3. **Upstream GitHub repository** — if no local source is found, offer to fetch from upstream.

Local source detection:
- A scaffold-like directory may be:
  - an extracted archive layout containing `AGENTS.md`, `.claude/`, `.github/`, `workflow/`, `prompts/`, or `meta-prompts/`
  - an installed-layout scaffold directory containing `AGENTS.md`, `.claude/commands/`, `workflow/`, or `.github/prompts/`
- If multiple plausible local sources remain after inspection, stop and ask the user which one to use.

If the source is a ZIP archive, extract it to a temporary location so you can inspect it before placing anything.
If the source is a directory, inspect it in place and do not mutate it until the update is confirmed and applied.

Upstream fetch (when no local source exists):
- Inform the user: "No local scaffold source found. I can fetch the latest version from the upstream repository (https://github.com/josiahH-cf/workflow, main branch)."
- If the user confirms, run: `git clone --depth 1 --branch main https://github.com/josiahH-cf/workflow.git .workflow-update-tmp`
- Use `.workflow-update-tmp/template/` as the scaffold source directory.
- Also copy `.workflow-update-tmp/prompts/` and `.workflow-update-tmp/meta-prompts/` into the source map if they exist.
- Treat the clone as source kind: **upstream clone**.
- If the clone fails (network error, repo unavailable), report the error and state: "No scaffold source available. To retry, either place a scaffold ZIP in the project root or confirm the upstream URL: https://github.com/josiahH-cf/workflow" — then stop.
- If the user declines the upstream fetch, state the same message and stop.

Determine the source kind:
- ZIP archive
- extracted archive layout
- installed-layout scaffold directory
- upstream clone

Determine which scaffold variant this is by inspecting the normalized contents:
- If it contains `AGENTS.md` or template roots like `.claude/`, `.github/`, `workflow/`, `.specify/`, or `governance/` → template content is present.
- If it contains prompt files at `prompts/*.prompt.md` or `.github/prompts/*.prompt.md` → prompt content is present.
- If it contains both → this is the full variant.

Build a normalized source-to-destination map before continuing:
- Files from `prompts/*.prompt.md` map to `.github/prompts/[same filename]`
- Files from `.github/prompts/*.prompt.md` map to `.github/prompts/[same filename]`
- All other files keep their relative path from the source root

Report: "Detected source kind: [ZIP archive / extracted archive layout / installed-layout scaffold directory / upstream clone]. Detected scaffold variant: [template-only / metaprompts-only / full]. Contents: [N] files."

---

STEP 2  -  CLASSIFY FILES AND BUILD UPDATE PLAN

Classify every normalized destination file from the source map into one of three categories:

**Auto-replace (generated/static  -  safe to overwrite):**
- `.claude/commands/*.md`  -  generated slash commands
- `workflow/LIFECYCLE.md`  -  lifecycle reference
- `workflow/PLAYBOOK.md`  -  phase execution contract
- `workflow/FILE_CONTRACTS.md`  -  artifact validation contract
- `workflow/FAILURE_ROUTING.md`  -  failure and escalation rules
- `meta-prompts/**/*.md`  -  canonical meta-prompts and admin flows
- `governance/CHANGE_PROTOCOL.md`  -  policy change protocol
- `governance/POLICY_TESTS.md`  -  policy validation matrix
- `governance/REGISTRY.md`  -  canonical policy registry
- `specs/_TEMPLATE.md`, `tasks/_TEMPLATE.md`, `decisions/_TEMPLATE.md`  -  blank templates
- `.github/PULL_REQUEST_TEMPLATE.md`  -  PR template
- `.github/ISSUE_TEMPLATE/*.md`  -  markdown issue templates
- `.github/ISSUE_TEMPLATE/*.yml`  -  form issue templates
- `.github/agents/*.md`  -  GitHub agent definitions
- `.github/REVIEW_RUBRIC.md`  -  review scoring rubric
- `.github/workflows/autofix.yml`  -  CI autofix workflow
- `.codex/PLANS.md`  -  Implementation plan template
- `.codex/AGENTS.md`  -  Codex adapter (references ../AGENTS.md)
- `CLAUDE.md`  -  Claude config (imports AGENTS.md, not customized per-project)
- `CLAUDE.local.md`  -  only if it is still the default stub
- `.gitignore`  -  additive entries (will be appended, not replaced)
- `.github/prompts/*.prompt.md`  -  generated Copilot prompt files (source may be `prompts/*.prompt.md` or `.github/prompts/*.prompt.md`; apply these in Step 5)
- `.specify/spec-template.md`  -  spec template (not customized per-project)
- `.specify/acceptance-criteria-template.md`  -  AC format reference

**Protect (customized per-project  -  never auto-overwrite):**
- `AGENTS.md`  -  customized with project-specific Overview (from Compass)
- `workflow/COMMANDS.md`  -  customized with project-specific Core Commands and Code Conventions (from Init + Scaffold)
- `.specify/constitution.md`  -  project identity from Compass interview (never auto-overwrite)
- `.claude/settings.json`  -  customized tool permissions and hooks (PostToolUse, Stop)
- `.claude/settings.local.json`  -  local Claude override (personal; gitignored)
- `.vscode/settings.json`  -  local/editor preference overrides (personal)
- `.github/workflows/copilot-setup-steps.yml`  -  customized CI command env values and runtime steps
- `.codex/config.toml`  -  customized Codex settings
- `.github/copilot-instructions.md`  -  may have project-specific additions
- `bugs/LOG.md`  -  project bug log (if exists)

**Conditional (may or may not be customized):**
- Any file not in the above lists.

Use the normalized destination path in the `File` column. If a destination file does not yet exist in the project, show `Category = New file` and `Action = Will add (does not exist yet)` regardless of its overwrite class.

Present the update plan as a table:

| File | Category | Action |
|------|----------|--------|
| [file] | Auto-replace | Will overwrite with new version |
| [file] | Protect | Will skip (customized) |
| [file] | New file | Will add (does not exist yet) |

Ask: "Here is the update plan. Auto-replace files will be overwritten. Protected files will be skipped. New files will be added. Proceed?"

Wait for confirmation before continuing.

---

STEP 3  -  SHOW CHANGES FOR AUTO-REPLACE FILES

For each auto-replace file that already exists in the project:
1. Compare the existing version with the new version from the source map.
2. If they differ, show a brief summary of what changed:
   - Lines added / removed / modified (counts)
   - Key changes in plain language (e.g., "New /build-session command added", "Review command updated with additional checks")
3. If they are identical, note: "[file]  -  no changes."

Present all changes as a summary report. Ask: "These are the changes that will be applied. Continue with the update?"

Wait for confirmation.

---

STEP 4  -  APPLY UPDATES

**Auto-replace files (except `.github/prompts/*.prompt.md`, which are handled in Step 5):**
For each auto-replace file:
- If the file exists and differs: overwrite it with the new version.
- If the file exists and is identical: skip silently.
- If the file does not exist: place it.

**.gitignore (special handling):**
- Do not replace the existing .gitignore.
- Check each entry in the new .gitignore. If an entry is missing from the existing .gitignore, append it.
- Report any entries that were added.

**New files:**
Place any normalized destination file that does not exist in the project. Defer normalized prompt files to Step 5.

**Protected files:**
Skip entirely. Do not touch.

After applying all non-prompt updates:
- If the source does not contain prompt files, delete the original ZIP (if one was used), any temporary extraction directory, `.workflow-update-tmp/` (if an upstream clone was used), and the confirmed staging source directory if it is inside the project root and is not the project root itself.

- If the source does not contain prompt files, commit all scaffold changes now: "Update project scaffolding to [version or date]"

---

STEP 5  -  UPDATE COPILOT PROMPT FILES

If the source contains prompt files at `prompts/*.prompt.md` or `.github/prompts/*.prompt.md`:

Copy each normalized prompt file from the source map into the project's `.github/prompts/` directory, overwriting existing versions. VS Code discovers slash commands from `.github/prompts/` in each workspace.

Show what was updated:
   - Files replaced (with change summary if possible)
   - New files added
   - Files unchanged

State: "Copilot prompt files updated in .github/prompts/. Type / in Copilot chat to verify."

After prompt files are updated:
- Delete the original ZIP (if one was used), any temporary extraction directory, `.workflow-update-tmp/` (if an upstream clone was used), and the confirmed staging source directory if it is inside the project root and is not the project root itself.
- Commit all scaffold changes: "Update project scaffolding to [version or date]"

---

STEP 6  -  REVIEW PROTECTED FILES IN ONE BATCH

Compare every protected file that exists in both the source map and the project.

If protected files differ:
1. Present a single batched summary table:
   - File
   - What is new in the template version
   - What appears project-specific in the current version
   - Recommended default action (`Keep current version`)
2. Ask once: "Protected files with template changes are listed above. By default they will remain untouched. Would you like side-by-side comparisons for any of them, or should I leave them all as-is?"
3. Only if the user requests deeper review for a specific file:
   - show the side-by-side comparison for that file
   - ask whether to keep, manually merge, or explicitly replace

---

STEP 7  -  CHECK WORKFLOW PREFERENCES

After all updates are applied, check `workflow/STATE.json` for missing preference fields:

- If `forkActivationLevel` is empty, ask:
  "How aggressively should the workflow pause at decision forks?
    1. Light — auto-continue at most forks; only stop for high-risk or irreversible decisions
    2. Standard — stop at key transition points where multiple valid paths exist (recommended)
    3. Active — stop at all decision points, including lower-stakes confirmations
  Reply 1, 2, or 3."
  Write the chosen value (`light`, `standard`, or `active`) to `workflow/STATE.json → forkActivationLevel`. Default to `standard` if skipped.

- If `advisoryProfile` is empty, leave as-is — it will be auto-detected during the next Compass or `/continue` session.

Apply only what is explicitly confirmed.

If no protected files have changes, state: "All protected files are up to date  -  no action needed."

---

STEP 8  -  VERIFY

Report the update results:

1. List all files that were updated (auto-replaced).
2. List all new files that were added.
3. List all protected files that were skipped.
4. List any protected files where the user chose to merge or replace.
5. Confirm Copilot prompt files were updated (if applicable).
6. Confirm Claude commands are in place at .claude/commands/.
7. Confirm workflow control-plane files are present at `workflow/LIFECYCLE.md`, `workflow/PLAYBOOK.md`, `workflow/FILE_CONTRACTS.md`, and `workflow/FAILURE_ROUTING.md`.
8. Confirm governance files are present at `governance/CHANGE_PROTOCOL.md`, `governance/POLICY_TESTS.md`, and `governance/REGISTRY.md`.
9. Confirm `.github/workflows/copilot-setup-steps.yml` remains project-customized and was not overwritten unless explicitly approved.
10. Confirm no template placeholder values were introduced into customized files.
11. Confirm local preference files (`.claude/settings.local.json`, `.vscode/settings.json`) were not overwritten unless explicitly approved.
12. Check current YOLO configuration: report whether `.claude/settings.local.json` and `.vscode/settings.json` have YOLO mode enabled, and which option (A/B/C/D) is active. If the configuration appears incomplete or inconsistent, offer to re-run the YOLO setup from initialization Step 4.

State: "Scaffolding update complete. All generated files (slash commands, templates, lifecycle docs) have been updated. Your project customizations (AGENTS.md, tool configs) are preserved."
