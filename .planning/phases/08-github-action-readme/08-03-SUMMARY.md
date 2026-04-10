---
phase: 08-github-action-readme
plan: 03
subsystem: documentation
tags: [readme, docs, env, pytest]
requirements-completed: [INFRA-03]
completed: 2026-04-10
key-files:
  modified:
    - README.md
    - .env.example
  created:
    - tests/test_readme.py
key-decisions:
  - "README is automation-first and documents the shipped workflow before local CLI usage."
  - "PAT quickstart is documented before the GitHub App path, but credential roles stay explicitly separated."
  - ".env.example documents only the local config surface and points workflow-only secrets to repository settings."
---

# Phase 8 Plan 03: README Rewrite Summary

**Rewrote the README around the shipped workflow and aligned `.env.example` with the real local config surface.**

## Accomplishments

- Added README contract tests for automation-first ordering, credential-role clarity, uv install guidance, and git boundaries
- Replaced the placeholder README with setup instructions for the copyable workflow, PAT quickstart, GitHub App option, and local CLI usage
- Documented `kb/` plus `kb/.manifest.json` as committed output and `.github-pr-kb/cache/` as non-git working data
- Updated `.env.example` to cover `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `ANTHROPIC_GENERATE_MODEL`, `KB_OUTPUT_DIR`, and `MIN_CONFIDENCE`

## Outcome

The docs now match the shipped product: maintainers can configure automation correctly, and local users can get from zero to a working install from the README alone.
