<!-- role: canonical-source -->
<!-- slash-command: review-bot -->
<!-- description: Automated review, commit, push, and conditional merge for completed features -->
# Review Bot

> The review bot is the **default review pathway** for completed feature branches. After tests pass, it runs the full review rubric, and if everything passes, it commits, pushes, opens a PR, and merges only when local permissions, branch protection, CI state, and repository rules allow it. If issues are found, it writes a findings file so `/continue` can route back to fix them.

**Standing rules for all sessions:**

- Follow `AGENTS.md` and workflow contracts in `/workflow/PLAYBOOK.md`, `/workflow/FILE_CONTRACTS.md`, and `/workflow/FAILURE_ROUTING.md`.
- Reference `.github/REVIEW_RUBRIC.md` for scoring criteria.
- Every artifact produced (review findings, commit, PR) is written to its canonical location before moving on.
- The review bot SHOULD be a different model than the one that implemented the feature when possible.

---

## Review Bot Phase

**Covers:** Automated full-rubric review → commit/push/PR/conditional merge on PASS; findings file on FAIL

**Purpose:** Make bot review the default pathway without assuming repository permissions. After post-tests pass, the bot runs the full review rubric against the spec, task file, and diff. If all checks pass, it commits, pushes, opens a PR, and merges when the repository allows it. If any check fails, it produces a structured findings file that `/continue` can consume to route back to implementation for fixes.

**When triggered:**
- **Automatically** by `/continue` after Phase 7 (Test `post`) passes
- **On demand** via `/review-bot` when you want to run the bot review manually

**Session inputs:** A feature ID that is labeled `status:implemented` with all ACs passing.

---

```text
You are an automated review bot. Your job is to review a completed feature branch, and if it passes all checks, commit, push, open a PR, and merge it only when repository permissions and rules allow. You operate as the default review pathway; do not assume manual approval is unnecessary when branch protection or repository policy requires it.

STEP 1: BOOTSTRAP
Read the following files:
- /AGENTS.md (hub navigation)
- /workflow/PLAYBOOK.md (phase gates)
- /workflow/FILE_CONTRACTS.md (artifact contracts)
- /.github/REVIEW_RUBRIC.md (scoring rubric — 6 categories)
- .specify/constitution.md (project identity)

Identify the target feature from /workflow/STATE.json or from the provided feature ID.
Read the spec at /specs/[feature-id]-[slug].md
Read the task file at /tasks/[feature-id]-[slug].md
Read the full diff of the feature branch against the target branch.

STEP 2: FULL RUBRIC REVIEW
Evaluate every category from the review rubric. For each, report PASS or FAIL with specific evidence.

Acceptance criteria coverage — for each criterion in the spec:
- Does a test exist that verifies this criterion?
- Does the implementation satisfy the criterion?
- Report: PASS with test location, or FAIL with what is missing.

Code quality:
- No existing tests were modified to accommodate the new code.
- No files outside the spec's Affected Areas were changed.
- No hardcoded values, secrets, or environment-specific strings.
- No functions over 50 lines.
- No dead code or unused imports.
- Error handling is explicit, not silent.
- Naming is consistent with existing codebase conventions.

Security:
- No secrets committed or logged.
- Inputs validated at system boundaries.
- No injection vectors (SQL, XSS, command injection).

Performance:
- No obvious N+1 queries, unbounded loops, or memory leaks.

Style:
- Matches project conventions (per COMMANDS.md Code Conventions).
- Linter clean.

Documentation:
- Spec updated if behavior changed.
- Decisions logged if non-obvious choices were made.

Run the project test suite to confirm all tests pass:
- Execute the Test (all) command from /workflow/COMMANDS.md
- Execute the Lint command from /workflow/COMMANDS.md
- Execute scripts/workflow-lint.sh

Run a launch/smoke check:
- Infer the run or start command from project tooling files (package.json scripts, Makefile/justfile targets, Procfile, Dockerfile, pyproject.toml, Cargo.toml, or workflow/COMMANDS.md Run entry).
- If found: execute it with a **30-second timeout**. If the process exits cleanly (exit code 0), capture the startup output as evidence. If the process does not exit within 30 seconds, treat it as a long-running server — kill the process and record `[LAUNCH CHECK] PASS (server mode — process started and held for 30s)`. Confirm no crash or error output before recording PASS.
- If not inferable: record "[LAUNCH CHECK] Skipped — no inferable run command. Manual smoke test recommended." in the summary. This is not a FAIL.
- If launch fails (crash, non-zero exit, error output during the timeout window): report as a FAIL in the summary with captured output.

Produce a summary:
- Total criteria: [N], Passed: [N], Failed: [N]
- Rubric category results (6 categories, each PASS/FAIL)
- Code quality issues: [list or "None"]
- Test suite: PASS/FAIL
- Lint: PASS/FAIL
- Launch check: PASS/FAIL/SKIPPED [evidence or reason]

STEP 3: DECISION

IF ALL checks pass (all criteria PASS, all rubric categories PASS, tests PASS, lint PASS, launch check PASS or SKIPPED):
  1. State: "Review Bot PASSED for [feature-id]-[slug]. Completing safe git/PR steps."
  2. Commit all changes with message: "feat([feature-id]): [short description] — bot-reviewed"
  3. Push the feature branch
  4. Create a PR with:
     - Title: concise imperative summary
     - Body: the full rubric review report as evidence
     - Spec reference link
     - AC evidence table
  5. Merge the PR immediately only if permissions, required checks, and branch/review rules allow it (squash merge preferred)
  6. Delete the feature branch after merge only when deletion is safe
  7. Update /workflow/STATE.json — advance to next feature or Phase 8
  8. Update the task file status to reflect completion
  9. Label the feature `status:done`
  10. If any push/PR/merge step cannot be completed safely, leave the PR/branch in the last completed safe state and report the exact manual step required.

IF ANY check fails:
  1. Write a findings file to /reviews/[feature-id]-bot-findings.md with the format below
  2. State: "Review Bot FAILED for [feature-id]-[slug]. Findings written to /reviews/[feature-id]-bot-findings.md. Run /continue to auto-route back to implementation."
  3. Update /workflow/STATE.json — set projectPhase back to 6-code, testMode to implement
  4. Do NOT commit, push, or merge

FINDINGS FILE FORMAT (/reviews/[feature-id]-bot-findings.md):

# Bot Review Findings: [feature-id]-[slug]

## Summary
- Date: [ISO date]
- Feature: [feature-id]-[slug]
- Verdict: FAIL
- Spec: /specs/[feature-id]-[slug].md
- Task: /tasks/[feature-id]-[slug].md
- Rubric: .github/REVIEW_RUBRIC.md

## Rubric Scores
| Category | Score | Evidence |
|----------|-------|----------|
| Correctness | PASS/FAIL | [details] |
| Test Coverage | PASS/FAIL | [details] |
| Security | PASS/FAIL | [details] |
| Performance | PASS/FAIL | [details] |
| Style | PASS/FAIL | [details] |
| Documentation | PASS/FAIL | [details] |

## Acceptance Criteria
- AC-1: PASS/FAIL — [test reference or issue]
- AC-2: PASS/FAIL — [test reference or issue]

## Issues Found
- [ ] [Category] [file:line] — [description of issue and specific fix needed]
- [ ] [Category] [file:line] — [description of issue and specific fix needed]

## Re-entry Instructions
Run /continue to automatically route back to Phase 6 (Code) for this feature.
The implementing agent should address each issue in the Issues Found list above.
After fixes, /continue will re-run /test post and then /review-bot again.
```

---

## Integration with `/continue`

The orchestrator dispatches to `/review-bot` after Phase 7 (`/test post`) passes. The flow is:

```
Phase 7 (test post PASS) → Phase 7a (review-bot)
  → PASS → commit/push/PR/conditional merge → next feature or Phase 8 when merge completes, or manual step report when blocked
  → FAIL → findings file → Phase 6 (re-implement) → Phase 7 → Phase 7a (retry)
```

When `/continue` encounters a findings file at `/reviews/[feature-id]-bot-findings.md`:
1. Read the findings file
2. Present the issues to the implementing agent
3. The agent fixes the issues
4. After fixes, `/continue` advances back through test → review-bot

## Relationship to Phase 7b (Review & Ship) and Cross-Review

- **Phase 7a (Review Bot)** is the **default review** path. Most features should flow through here.
- **Phase 7b (Review & Ship)** remains available as a **manual fallback** for cases where human review is desired (e.g., security-critical features, architectural changes).
- **Cross-review** (`/cross-review`) can still be triggered manually for high-risk features.
- The review bot's rubric evaluation counts as a full review. If the bot is a different model than the implementer, it also counts as a cross-review.

## File Connections

| File | Role |
|------|------|
| `workflow/LIFECYCLE.md` | Phase 7a position in lifecycle |
| `workflow/PLAYBOOK.md` | Phase gate for bot review |
| `workflow/FILE_CONTRACTS.md` | Findings file artifact contract |
| `workflow/ORCHESTRATOR.md` | Dispatch rule for 7a-review-bot |
| `workflow/ROUTING.md` | Bot agent routing entry |
| `workflow/FAILURE_ROUTING.md` | Failure routing for bot review failures |
| `.github/agents/review-bot.agent.md` | Bot agent definition |
| `.github/REVIEW_RUBRIC.md` | Scoring rubric |
