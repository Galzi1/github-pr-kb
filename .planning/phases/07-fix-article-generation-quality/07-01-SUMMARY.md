---
phase: 07-fix-article-generation-quality
plan: 01
subsystem: classifier-config-generator-contracts
tags: [classifier, config, generator, pydantic, pytest]
requirements-completed: [Q-03, Q-04]
completed: 2026-04-08
key-files:
  modified:
    - src/github_pr_kb/config.py
    - src/github_pr_kb/classifier.py
    - src/github_pr_kb/generator.py
    - tests/test_classifier.py
    - tests/test_config.py
    - tests/test_generator.py
key-decisions:
  - "Classifier JSON parse failures now return None and increment the failed counter instead of caching fake fallback records."
  - "classification-index.json self-heals on load by pruning legacy entries whose summary is 'classification failed'."
  - "Settings now expose anthropic_generate_model and min_confidence for downstream generator behavior."
  - "GenerateResult owns a filtered counter so generator and CLI can report low-confidence skips honestly."
---

# Phase 7 Plan 01: Foundation Contracts Summary

**Established the phase 7 contracts in config, classifier, and generator so later synthesis and CLI work could rely on explicit settings, counters, and failure handling.**

## Accomplishments

- Added `anthropic_generate_model` and `min_confidence` to `Settings`
- Removed fake classifier fallback records on JSON parse failure and pruned stale failed index entries on load
- Extended `GenerateResult` with `filtered`
- Added focused tests for classifier parse failure handling, index pruning, new config fields, and the generator result contract

## Outcome

Phase 7 now has the configuration and data-shape foundations required for synthesized generation and honest CLI reporting.
