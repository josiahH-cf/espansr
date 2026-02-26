# Copilot Instructions

## Project Standards

- Read `/AGENTS.md` before starting any task — it defines the project's conventions, testing rules, commit practices, and review expectations

## Completions

- Match naming conventions and patterns in the file being edited
- Prefer explicit types over inferred when the language supports both
- Do not generate placeholder or TODO comments

## Code Review

- Flag functions over 50 lines
- Flag nesting deeper than 3 levels
- Flag missing error handling on I/O operations
- Flag tests that assert only the happy path
- Flag hardcoded values that should be configuration
- Verify every acceptance criterion from the linked spec has a test

## PR Descriptions

- State what changed, why, and how to verify
- Link to the spec in /specs/ if one exists
- List files changed, grouped by concern

## Coding Agent

- Read the linked spec before starting
- Do not modify files outside the scope described in the issue
