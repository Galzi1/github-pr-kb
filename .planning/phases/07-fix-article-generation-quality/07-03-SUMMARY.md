---
phase: 07-fix-article-generation-quality
plan: 03
subsystem: cli
tags: [cli, click, classifier, generator, pytest]
requirements-completed: [Q-01, Q-04]
completed: 2026-04-08
key-files:
  modified:
    - src/github_pr_kb/cli.py
    - src/github_pr_kb/classifier.py
    - tests/test_cli.py
    - tests/test_classifier.py
key-decisions:
  - "CLI classify summaries now consume a public classifier contract via get_summary_counts instead of scraping private attrs with zero fallbacks."
  - "Cached low-confidence hits contribute to the published need_review metric."
  - "Generate performs a classified-input preflight, supports --regenerate, and distinguishes partial failures from total generation failures."
  - "Missing generate API keys receive a narrow Anthropic-specific hint while unrelated ValueErrors keep their original detail."
---

# Phase 7 Plan 03: Honest CLI Reporting Summary

**Updated the CLI to reflect what the generator and classifier actually did, including low-confidence filtering, synthesis failures, and full regenerate runs.**

## Accomplishments

- Added `PRClassifier.get_summary_counts()` and aligned review counting with cached low-confidence hits
- Updated classify output to report `new`, `cached`, `need review`, and `failed` from the explicit contract
- Added `--regenerate` to `generate` and passed it through to `KBGenerator.generate_all(regenerate=...)`
- Added generate preflight checks, partial-failure warnings, and zero-success failure handling
- Expanded CLI tests to cover filtered counts, regenerate passthrough, missing classified input, key-specific config errors, and upstream interface guards

## Outcome

CLI output now matches the real phase 7 behavior, and users can safely rerun full article synthesis with explicit failure semantics.
