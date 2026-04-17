---
phase: 09-wiki-style-kb-synthesis-merge-related-articles-into-compound
plan: "01"
subsystem: kb-generator
tags: [models, manifest, topic-planning, tdd]
completed_at: "2026-04-17T10:29:23Z"
duration_min: 10
tasks_completed: 2
files_modified: 4

dependency_graph:
  requires: []
  provides:
    - TopicGroup/TopicPlan models in models.py
    - Nested manifest format with auto-migration in generator.py
    - _sources_hash deterministic hashing
    - _plan_topics Claude-driven topic grouping
  affects:
    - src/github_pr_kb/generator.py
    - src/github_pr_kb/models.py

tech_stack:
  added:
    - python-frontmatter>=1.1.0
  patterns:
    - Pydantic ConfigDict(extra="ignore") on new models
    - Manifest auto-migration: detect flat format by absence of "comments" key
    - SHA-256 hash over sorted bodies for deterministic content fingerprinting

key_files:
  created: []
  modified:
    - src/github_pr_kb/models.py
    - src/github_pr_kb/generator.py
    - tests/test_generator.py
    - pyproject.toml

decisions:
  - Manifest nested format uses {"comments": {id: path}, "topics": {slug: metadata}} - "comments" key absence triggers migration (D-08, D-09)
  - _plan_topics reuses existing self._model (ANTHROPIC_GENERATE_MODEL) - no new model/env var (D-07)
  - _sources_hash sorts bodies before joining - ensures hash is order-independent for idempotent topic cache keys
  - TopicPlan validation wraps Claude JSON response - ValidationError raised (not silenced) so callers can handle failures explicitly (T-09-02 mitigation)

metrics:
  duration: 10 min
  completed_date: "2026-04-17"
---

# Phase 09 Plan 01: Data Models, Manifest Migration, and Topic Planning Pass Summary

**One-liner:** TopicGroup/TopicPlan Pydantic models with ConfigDict, nested manifest auto-migration from flat format, deterministic SHA-256 sources hash, and Claude-driven `_plan_topics()` returning validated TopicPlan.

## What Was Built

### Task 1: TopicGroup/TopicPlan models + python-frontmatter dependency (commit 64bcc66)

Added two new Pydantic models to `models.py` after `ClassifiedFile`:

- `TopicGroup`: slug, title, category (CategoryLiteral), article_keys (list[str]), ConfigDict(extra="ignore")
- `TopicPlan`: topics (list[TopicGroup]), ConfigDict(extra="ignore")
- Added `python-frontmatter>=1.1.0` to pyproject.toml via `uv add`
- 5 new tests: valid construction, invalid category rejection, empty article_keys accepted, extra fields ignored

### Task 2: Nested manifest format, auto-migration, _sources_hash, _plan_topics (commit 6d3a870)

Updated `generator.py`:

- `_load_manifest()` now returns `dict[str, dict]` in `{"comments": {...}, "topics": {}}` shape
- Old flat manifests (no "comments" key) auto-migrate to nested format on load
- `_slugs_from_manifest()` and `_process_classified_file()` updated to access `self._manifest["comments"]`
- `_generate_all_transactionally()` initializes `self._manifest = {"comments": {}, "topics": {}}` (not `{}`)
- `_sources_hash(article_bodies)`: static method, sorts bodies, SHA-256 hex digest
- `_plan_topics(article_summaries)`: calls Claude via `self._client`, parses JSON, validates into TopicPlan; raises on JSONDecodeError or ValidationError
- `TOPIC_PLAN_SYSTEM_PROMPT` constant added
- `import hashlib` added; `TopicPlan` imported from models
- 7 new tests for migration, roundtrip, hash consistency, hash order-independence, plan_topics happy path, single-source topic
- 6 existing tests updated to use nested manifest format (`manifest["comments"]`)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing tests used flat manifest assertions**
- **Found during:** Task 2 GREEN phase
- **Issue:** 6 existing tests checked `manifest["101"]` or `"101" not in manifest` - now invalid with nested format
- **Fix:** Updated assertions to use `manifest["comments"]["101"]` and `"101" not in manifest["comments"]`
- **Files modified:** tests/test_generator.py
- **Commit:** 6d3a870

## Threat Mitigations Applied

Per threat register:
- **T-09-01** (Manifest tampering): `_load_manifest` validates structure on load; flat format gracefully migrated; corrupt JSON caught and replaced with empty nested manifest
- **T-09-02** (Claude API JSON spoofing): `_plan_topics` parses through `TopicPlan.model_validate()` with Pydantic strict validation; ValidationError raised explicitly, not silenced

## Known Stubs

None - all new code paths have real implementations. `_plan_topics` calls the actual Claude client; stub behavior only in tests via MagicMock.

## Threat Flags

None - no new network endpoints, auth paths, file access patterns, or schema changes beyond what the plan's threat model already covers.

## Self-Check: PASSED

- `src/github_pr_kb/models.py` - TopicGroup and TopicPlan classes exist
- `src/github_pr_kb/generator.py` - _plan_topics, _sources_hash, TOPIC_PLAN_SYSTEM_PROMPT, nested manifest all present
- `pyproject.toml` - python-frontmatter dependency present
- Commits 64bcc66 and 6d3a870 exist in git log
- 51/51 tests pass, 0 ruff errors
