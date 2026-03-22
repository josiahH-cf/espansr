<!-- role: canonical-source -->
<!-- phase: 7 -->
<!-- description: Run tests against ACs, log bugs, verify behavior -->
# Phase 7 — Test & Mark Changes

**Objective:** Verify feature behavior against acceptance criteria in explicit test modes (`pre` and `post`), log failures as bugs, and confirm behavior matches spec.

**Trigger:** `pre` mode runs before Phase 6 implementation. `post` mode runs after Phase 6 implementation.

**Entry commands:**
- Claude: `/test`
- Copilot: `phase-7-test.prompt.md`

---

## What Happens

### Pre-Implementation Mode (`/test pre`)
1. Read spec ACs and existing test patterns
2. Write at least one test per AC using EARS/GWT format
3. Tests must fail before implementation exists
4. Include UI/visual tests where applicable
5. Commit failing tests

### Post-Implementation Mode (`/test post`)
1. Run full test suite
2. Compare results against each AC — mark pass/fail
3. Log failures as bugs via `/bug`
4. If behavior deviated from spec but tests pass, update spec notes
5. Verify no regressions
6. **Launch/smoke check** — attempt to verify the application starts and responds:
   a. Infer the likely run or start command from project tooling files (`package.json` scripts, `Makefile`/`justfile` targets, `Procfile`, `Dockerfile`, `pyproject.toml`, `Cargo.toml`, or `workflow/COMMANDS.md` Run entry).
   b. If a run command is found: execute it with a **30-second timeout**. If the process exits cleanly (exit code 0), record the startup output as evidence. If the process does not exit within 30 seconds, treat it as a long-running server — kill the process and record `[LAUNCH CHECK] PASS (server mode — process started and held for 30s)`. Confirm no crash or error output before recording PASS.
   c. If no run command can be inferred: record `[LAUNCH CHECK] Skipped — no inferable run command. Manual smoke test recommended.` in the test output and proceed. This is not a blocker.
   d. If the launch check fails (crash, non-zero exit, error output during the timeout window): log as a **blocking bug** via `/bug` with `severity: blocking` and the captured output.

## Gate

- `pre` mode: failing tests exist for every AC
- `post` mode: all acceptance criteria verified (pass or documented failure)
- Bug log reviewed — no blocking bugs remain
- No regressions in existing tests
- Launch/smoke check executed or explicitly skipped with documented reason

## Output

- Test results mapped to ACs
- Bug log entries for any failures
- Launch check evidence (startup output, health response, or skip reason)
- Updated spec if behavior deviated

## See Also

- Bug logging: `/bug` command
- Bug fixing: `/bugfix` command
