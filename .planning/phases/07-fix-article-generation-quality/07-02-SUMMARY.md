---
phase: 07-fix-article-generation-quality
plan: 02
subsystem: generator
tags: [generator, anthropic, markdown, regenerate, pytest]
requirements-completed: [Q-02, Q-04]
completed: 2026-04-08
key-files:
  modified:
    - src/github_pr_kb/generator.py
    - tests/test_generator.py
key-decisions:
  - "KBGenerator now synthesizes article bodies with Claude using category-specific section templates and explicit uncertainty guidance."
  - "Bad synthesis output is rejected when it is empty, non-text, or too similar to the source comment."
  - "Comments below min_confidence are filtered before synthesis and counted separately."
  - "Regenerate rebuilds into a staging directory and swaps into place only after staged generation succeeds."
---

# Phase 7 Plan 02: Generator Quality Summary

**Replaced raw comment dumping with Claude-backed synthesis and added the safeguards needed to keep generation useful, retryable, and safe to rerun.**

## Accomplishments

- Added generator-side Anthropic client initialization, generate-model selection, and min-confidence handling
- Reworked article building to synthesize structured markdown instead of copying the raw comment body
- Rejected empty, malformed, and source-echo synthesis output without writing articles or mutating the manifest
- Added transactional `regenerate=True` support so full rebuilds do not wipe the live KB before the replacement is ready
- Rewrote the generator test suite around injected fake Anthropic clients and end-state assertions

## Outcome

Generated articles now contain synthesized knowledge content, low-value items can be filtered, and regenerate is safe against partial rebuild loss.
