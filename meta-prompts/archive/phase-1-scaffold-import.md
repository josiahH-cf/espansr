<!-- role: canonical-source -->
<!-- phase: 1 -->
<!-- description: Import scaffold files into a project and establish baseline -->
# Phase 1 — Scaffold Import

**Objective:** Place or stage workflow scaffold files into a project, then let `/initialization` route the repo through the correct Phase 1 behavior.

**Trigger:** New project needs the agentic workflow, or existing project needs scaffold update.

**Context:** This phase is executed by the `admin/initialization.md` meta-prompt. It is listed here for lifecycle completeness.

---

## What Happens

1. `install.sh` copies scaffold files directly for fresh repos or stages them for non-empty repos
2. `/initialization` detects whether the repo is fresh, existing/non-scaffolded, or already scaffolded
3. Scaffold-managed files are placed or updated
4. Protected project-owned files are preserved unless explicitly approved
5. Project conventions are inferred or confirmed
6. Verification pass confirms Phase 1 is complete

## Gate

- All scaffold files placed
- AGENTS.md has no unresolved placeholder brackets (except `[PROJECT-SPECIFIC]` in Overview — filled by Compass)
- `workflow/COMMANDS.md` has `[PROJECT-SPECIFIC]` placeholders in Core Commands and Code Conventions — filled by Phase 1 (initial) and Phase 4 (finalized)
- `.specify/` directory exists with 3 template files
- `/workflow/STATE.json` exists and is valid JSON

## Output

Project ready for Phase 2 (Compass) or resumed at the current lifecycle phase after scaffold update.

## Auto-Advance

If the constitution is missing or still placeholder-based, Phase 1 completion auto-triggers Phase 2 (Compass). Otherwise the project resumes from its current lifecycle state.

## See Also

- Full initialization process: `meta-prompts/admin/initialization.md`
- Scaffold update command: `/update-workflow` (`meta-prompts/admin/update-workflow.md`)
