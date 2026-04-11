---
phase: 08-github-action-readme
plan: 01
subsystem: automation-helper
tags: [github-actions, cursor, automation, pytest]
requirements-completed: [ACTION-02, ACTION-03]
completed: 2026-04-10
key-files:
  created:
    - src/github_pr_kb/action_state.py
    - tests/test_action_state.py
key-decisions:
  - "The workflow skip/cursor contract lives in a stdlib-only Python helper instead of opaque YAML."
  - "Merged-event and manual-dispatch logic use separate formulas, both normalized to UTC ISO timestamps."
  - "next_cursor is emitted as a candidate only; workflow persistence must re-read and write monotonically."
---

# Phase 8 Plan 01: Action State Helper Summary

**Added a standalone `github_pr_kb.action_state` module that makes workflow run/skip decisions testable and deterministic.**

## Accomplishments

- Implemented `decide_action_run(...)` for merged-event and manual-dispatch paths
- Added a `python -m github_pr_kb.action_state` JSON CLI for workflow consumption
- Locked malformed or timezone-naive timestamp handling to deterministic non-zero exits
- Added focused pytest coverage for auto no-op, manual backfill, force runs, and isolated CLI execution

## Outcome

Phase 8 now has a reusable helper for cost-aware skipping and monotonic cursor candidates without importing runtime settings or other env-bound surfaces.
