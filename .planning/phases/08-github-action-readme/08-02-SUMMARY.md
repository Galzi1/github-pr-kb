---
phase: 08-github-action-readme
plan: 02
subsystem: github-actions
tags: [github-actions, workflow, cache, gh-cli, pytest]
requirements-completed: [ACTION-01, ACTION-02, ACTION-03]
completed: 2026-04-10
key-files:
  created:
    - .github/workflows/github-pr-kb.yml
    - tests/test_action_workflow.py
key-decisions:
  - "The shipped workflow is copyable into consumer repos because it bootstraps this tool from a second checkout."
  - "Repository-variable auth prefers the GitHub App path and falls back to KB_VARIABLES_TOKEN."
  - "Cursor persistence re-reads the latest repository variable and stores the monotonic max after publication succeeds."
---

# Phase 8 Plan 02: Workflow Automation Summary

**Shipped the merged-PR plus `workflow_dispatch` automation workflow, including cache restore, rolling PR publication, and monotonic cursor persistence.**

## Accomplishments

- Added `.github/workflows/github-pr-kb.yml` with merged-only trigger handling and manual backfill inputs
- Bootstrapped the CLI from a pinned checkout of `galzi/github-pr-kb` via `KB_TOOL_REPOSITORY` and `KB_TOOL_REF`
- Wired explicit `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, and `GH_TOKEN` responsibilities
- Restored `.github-pr-kb/cache/` through Actions cache and staged only KB publication outputs
- Added contract tests covering triggers, SHA-pinned actions, helper invocation shape, rolling PR behavior, and cursor endpoints

## Outcome

The repository now ships the actual GitHub Actions automation required for incremental KB updates without committing transient cache data or burying the skip logic in YAML alone.
