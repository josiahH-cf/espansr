# Review Rubric

Standard scoring rubric for all code reviews. Used by reviewer agents and human reviewers.

## Categories

### 1. Correctness

Does the code or documentation do what the spec, bug entry, or routine maintenance request says it should do?

- **PASS**: All acceptance criteria or requested maintenance outcomes met, edge cases handled where relevant, no logic errors
- **FAIL**: Any AC/requested outcome unmet, incorrect behavior, unhandled edge cases

Evidence required: Test results mapped to ACs, or request/diff/check evidence for routine maintenance.

### 2. Test Coverage

Are acceptance criteria or requested changes adequately verified?

- **PASS**: Every AC has at least one meaningful test, or routine maintenance has the relevant validation/check evidence
- **FAIL**: Missing tests for any feature AC, tests that pass without the feature, no edge case coverage, or no relevant check for routine maintenance

Evidence required: Test names mapped to AC IDs, or maintenance check commands/results.

### 3. Security

Is the code free from common vulnerabilities?

- **PASS**: No secrets in code, inputs validated at boundaries, no injection vectors, dependencies audited
- **FAIL**: Hardcoded secrets, unvalidated user input, SQL/XSS/command injection possible, known vulnerable dependencies

Evidence required: Security checklist completed.

### 4. Performance

Does the code avoid unnecessary performance problems?

- **PASS**: No obvious N+1 queries, no unbounded loops on user data, appropriate caching, reasonable memory usage
- **FAIL**: Quadratic or worse algorithms on user data, memory leaks, missing pagination, synchronous blocking on I/O

Evidence required: Note any perf-sensitive paths and their approach.

### 5. Style

Does the code follow project conventions?

- **PASS**: Matches existing patterns, naming conventions followed, file organization consistent, linting passes
- **FAIL**: Inconsistent naming, wrong file location, linting failures, dead code or unused imports

Evidence required: Linter output clean. Note: style issues are flagged but do not block approval alone.

### 6. Documentation

Are changes documented appropriately?

- **PASS**: Spec updated if behavior changed, decisions logged when needed, PR description complete, routine maintenance scope documented
- **FAIL**: Spec drift, missing decision records, empty PR description, or routine maintenance without request/check evidence

Evidence required: Spec diff if behavior changed; request scope and verification evidence for routine maintenance.

## Scoring

| Category | Weight | PASS/FAIL |
|----------|--------|-----------|
| Correctness | Required | |
| Test Coverage | Required | |
| Security | Required | |
| Performance | Advisory | |
| Style | Advisory | |
| Documentation | Required | |

**Required** categories must PASS for approval. **Advisory** categories are flagged but don't block.

## Final Verdict

- **APPROVE**: All Required categories PASS
- **REQUEST CHANGES**: Any Required category FAILS — list specific items to fix
- **COMMENT**: Only Advisory categories flagged — approve with notes
