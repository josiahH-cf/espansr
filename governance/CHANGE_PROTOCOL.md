# Governance Change Protocol

This protocol controls changes to instruction and policy files.

## Principle

Core policy files are not edited ad hoc during feature delivery. Changes require a proposal artifact and independent review.

Routine prompt, template, documentation, and small workflow wording corrections are not automatically governance changes.
They may use the Phase 8 stable-maintenance path when they do not alter authority, safeguards, approval rules,
security posture, or repository-wide policy.

## Trigger

Open a policy change when recurring failures indicate missing or unclear instructions, or when the proposed edit changes
repository policy, governance authority, review/merge rules, security safeguards, or required workflow gates.

Do not open a policy change for a focused template update, prompt clarification, typo fix, documentation correction, or small maintenance workflow wording update unless it changes the rules above.

## Required Proposal

Create a decision record that includes:

- Triggering failure pattern
- Files to change
- Proposed policy diff summary
- Compatibility and portability impact
- Rollback plan
- Validation updates required in `/governance/POLICY_TESTS.md`

## Approval Flow

1. Builder agent drafts proposal.
2. Reviewer agent validates necessity and risk.
3. Human approves merge for governance changes.

If the human maintainer explicitly requests a policy modernization, the request plus PR body may serve as the proposal
artifact when the change is isolated and the PR documents before/after behavior, compatibility impact, validation,
and rollback.

## Merge Rules

- Governance changes must be isolated from feature code changes.
- PR must include before/after behavior statement.
- PR must include rollback instructions.
