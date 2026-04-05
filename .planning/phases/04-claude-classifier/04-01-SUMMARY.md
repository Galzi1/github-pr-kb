---
phase: 04-claude-classifier
plan: 01
subsystem: api
tags: [pydantic, anthropic, classifier, models, tdd]

# Dependency graph
requires:
  - phase: 03-extraction-resilience-cache
    provides: PRFile, CommentRecord, PRRecord models and cache directory pattern
provides:
  - ClassifiedComment model with needs_review flag (confidence < 0.75)
  - ClassifiedFile model wrapping PRRecord + list[ClassifiedComment]
  - CategoryLiteral type alias for 5 classification categories
  - Settings.anthropic_api_key optional field
  - test_classifier.py with 7 TDD RED tests for Plan 02 to satisfy
affects: [04-claude-classifier-plan-02, 06-cli-wiring]

# Tech tracking
tech-stack:
  added: [anthropic SDK (test scaffolding only)]
  patterns: [TDD RED test scaffold, optional config field for feature flags, in-test imports to avoid collect-time ImportError]

key-files:
  created: [tests/test_classifier.py]
  modified: [src/github_pr_kb/models.py, src/github_pr_kb/config.py, tests/conftest.py]

key-decisions:
  - "CategoryLiteral uses Literal type alias (not Enum) — consistent with existing comment_type/state Literal pattern"
  - "anthropic_api_key: str | None = None — optional at Settings level; classifier __init__ raises ValueError if None (Plan 02)"
  - "PRClassifier imported inside each test function body — prevents ImportError at collection time before Plan 02 exists"
  - "ANTHROPIC_API_KEY set at conftest module level — same pattern as GITHUB_TOKEN, required before Settings() instantiates"

patterns-established:
  - "In-test imports: import module-level classes that don't exist yet inside test function body, not at module top"
  - "Conftest module-level setdefault: all required env vars set before pytest collection, not just inside fixtures"

requirements-completed: [CLASS-01, CLASS-02, CLASS-04]

# Metrics
duration: 3min
completed: 2026-04-05
---

# Phase 04 Plan 01: Data Contracts and Test Scaffolds Summary

**Pydantic classification models (ClassifiedComment, ClassifiedFile, CategoryLiteral) and optional anthropic_api_key field on Settings, with 7 TDD RED tests ready for Plan 02 to satisfy**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-05T10:20:37Z
- **Completed:** 2026-04-05T10:23:30Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Added ClassifiedComment and ClassifiedFile Pydantic models with CategoryLiteral type alias to models.py
- Extended Settings with anthropic_api_key: str | None = None and updated conftest.py to prevent collection-time ValidationError
- Created test_classifier.py with 7 collectible but intentionally failing tests covering categories, confidence thresholds, caching, field types, and body hashing

## Task Commits

Each task was committed atomically:

1. **Task 1: Add ClassifiedComment, ClassifiedFile, CategoryLiteral models** - `9ac17cb` (feat)
2. **Task 2: Add anthropic_api_key to Settings, set ANTHROPIC_API_KEY in conftest** - `cec9f7b` (feat)
3. **Task 3: Scaffold test_classifier.py with 7 failing tests (TDD RED)** - `136305b` (test)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `src/github_pr_kb/models.py` - Added CategoryLiteral, ClassifiedComment, ClassifiedFile after PRFile
- `src/github_pr_kb/config.py` - Replaced placeholder comment with `anthropic_api_key: str | None = None`
- `tests/conftest.py` - Added ANTHROPIC_API_KEY setdefault at module level; renamed fixture to `_set_dummy_env_tokens`
- `tests/test_classifier.py` - 7 TDD RED test functions, `make_mock_message` helper, `cache_dir_with_pr` fixture

## Decisions Made

- Used `str | None = None` for `anthropic_api_key` (not a required `str`) so `extract`-only users don't need ANTHROPIC_API_KEY set — the classifier's `__init__` will validate it is non-None in Plan 02
- `PRClassifier` is imported inside each test function body rather than at module level — this prevents `ImportError` at `pytest --collect-only` time before Plan 02 creates the class

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None — all tasks completed cleanly on first attempt.

## User Setup Required

None — no external service configuration required. ANTHROPIC_API_KEY will be needed for running the actual classify command (Plan 02+), but the test suite runs with the fake key set in conftest.

## Next Phase Readiness

- Plan 02 can implement `PRClassifier` and `body_hash` in classifier.py — all contracts are defined
- 7 tests are waiting in RED state; Plan 02 makes them GREEN
- Settings already has `anthropic_api_key` field; Plan 02 reads `settings.anthropic_api_key`
- No blockers

## Self-Check: PASSED

- FOUND: src/github_pr_kb/models.py
- FOUND: src/github_pr_kb/config.py
- FOUND: tests/conftest.py
- FOUND: tests/test_classifier.py
- FOUND: .planning/phases/04-claude-classifier/04-01-SUMMARY.md
- FOUND commit: 9ac17cb (Task 1)
- FOUND commit: cec9f7b (Task 2)
- FOUND commit: 136305b (Task 3)

---
*Phase: 04-claude-classifier*
*Completed: 2026-04-05*
