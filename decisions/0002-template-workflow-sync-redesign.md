# Decision 0002: Template workflow and sync redesign

**Date:** 2026-05-05
**Status:** Accepted
**Feature:** /specs/7-template-workflow-sync-redesign.md
**Trigger:** The bundled prompt library, help surfaces, trigger names, and sync commands have accumulated overlapping concepts that increase user memory burden and make prompt chaining difficult to follow.

## Context

espansr currently exposes bundled prompts as a flat starter set with mixed trigger naming styles and several static or partially overlapping help surfaces. The sync surface also mixes bundled starter reconciliation, live template publishing, remote Git pull/push, generated Espanso output, and setup/bootstrap behavior across commands whose names do not clearly map to source-of-truth lanes.

The user selected a deeper redesign path with direct prompt trigger renames and a broad sync command redesign. That makes the change intentionally breaking and requires explicit migration, documentation, and verification rules before implementation proceeds.

## Options

1. **Conservative maintenance** - Keep current triggers and command behavior, then improve docs and quick help. Lowest risk, but leaves the core memory model mostly intact.
2. **Moderate product polish** - Add metadata and help grouping while keeping command/trigger compatibility. Better discovery, but still forces users to remember old names and overlapping sync commands.
3. **Breaking workflow redesign** - Rename prompts directly, redesign command lanes, and add starter migration mechanics. Higher migration cost, but produces the clearest long-term mental model.

## Decision

Adopt the breaking workflow redesign. The redesigned model will prioritize clear prompt chains, category-aware discovery, direct trigger names, and separate source-of-truth lanes for live templates, remote sync, bundled starters, and Espanso output publishing.

## Consequences

- Existing users may need to relearn prompt triggers and CLI commands.
- Starter migration must preserve or report user-modified live templates instead of silently overwriting or deleting them.
- Documentation, quick help, popup help, CLI help, and completions must be updated together.
- Tests need to cover migration, renamed triggers, command lane behavior, and help-surface drift.

## Rollback Impact

Rollback requires reverting prompt trigger renames, command parser changes, starter migration behavior, docs, and any metadata-dependent catalog behavior. If migration has run in a user's live store, rollback must not assume old starter files can be reconstructed without backups.

## Validation Follow-up

- Add schema tests for workflow metadata round-tripping.
- Add bundled starter migration tests for old filenames/triggers, user modifications, backups, dry-run safety, and collision detection.
- Add command parser and completion tests for the new command lanes.
- Add popup and quick-help tests so stale trigger names are caught.
