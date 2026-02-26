Review the changes on the current branch against the target branch.
Read the spec provided for this session.

Check:
1. Every acceptance criterion has a corresponding test
2. No existing test was modified to accommodate the implementation
3. No files outside the spec scope were changed
4. No hardcoded values, secrets, or environment-specific strings
5. No functions over 50 lines
6. No dead code or unused imports
7. Error handling is explicit, not silent
8. Naming is consistent with codebase conventions

Report:
- PASS: [criterion] — [evidence]
- FAIL: [criterion] — [what and where]

If all pass, confirm branch is ready for PR.
If any fail, list specific fixes needed.
