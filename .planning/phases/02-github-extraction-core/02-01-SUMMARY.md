---
phase: 02-github-extraction-core
plan: 01
subsystem: database
tags: [pydantic, python, models, json, serialization]

# Dependency graph
requires:
  - phase: 01-project-foundation
    provides: pyproject.toml with pydantic 2.12.5 installed, pytest infrastructure, test patterns from test_config.py
provides:
  - PRRecord pydantic v2 model (number, title, body, state Literal, url)
  - CommentRecord pydantic v2 model (comment_id, comment_type Literal, author, body, created_at, url, file_path, diff_hunk, reactions)
  - PRFile envelope model (pr, comments, extracted_at) with JSON round-trip
  - 11 unit tests proving validation and serialization behavior
affects: [02-02-extractor, 03-resilience-cache, 04-classifier, 05-generator]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pydantic v2 BaseModel with ConfigDict(extra='ignore') for forward-compatible schema"
    - "Literal types for comment_type and state enforce valid enum values at validation"
    - "model_dump(mode='json') + model_validate() for lossless JSON round-trip"
    - "TDD RED-GREEN: write failing tests first, then implement minimal code to pass"

key-files:
  created:
    - src/github_pr_kb/models.py
    - tests/test_models.py
  modified: []

key-decisions:
  - "ConfigDict(extra='ignore') on all three models makes schema forward-compatible with future field additions without breaking deserialization"
  - "Literal['review', 'issue'] for comment_type and Literal['open', 'closed'] for state enforce valid values at model construction — downstream code never sees invalid state"
  - "reactions: dict[str, int] = {} is safe as a mutable default in Pydantic v2 because __init__ deep-copies model defaults"

patterns-established:
  - "Model definition order: CommentRecord before PRRecord before PRFile (dependency order)"
  - "Optional fields default to None, not omitted — explicit None signals 'not applicable' vs missing"
  - "Pydantic v2 datetime fields serialize to ISO 8601 strings in model_dump(mode='json') without custom serializers"

requirements-completed: [CORE-01]

# Metrics
duration: 4min
completed: 2026-04-03
---

# Phase 2 Plan 01: Data Models Summary

**Three Pydantic v2 models (PRRecord, CommentRecord, PRFile) forming the data contract for all extraction, classification, and generation phases, with Literal-enforced state/type validation and lossless JSON round-trip**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-03T13:56:46Z
- **Completed:** 2026-04-03T14:00:53Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- PRRecord model with Literal["open", "closed"] state validation and Optional body
- CommentRecord model with Literal["review", "issue"] type, Optional file_path/diff_hunk for review context, and reactions dict with empty default
- PRFile envelope model with datetime extracted_at that round-trips through JSON without data loss
- 11 unit tests covering required field validation, Literal constraint enforcement, JSON round-trip, and ISO 8601 datetime serialization

## Task Commits

Each task was committed atomically:

1. **Task 1: Create test scaffolds (RED phase)** - `bdd192a` (test)
2. **Task 2: Implement pydantic models (GREEN phase)** - `bcad6d6` (feat)

_Note: TDD tasks have two commits — failing tests first, then implementation._

## Files Created/Modified

- `src/github_pr_kb/models.py` - Three Pydantic v2 BaseModel classes replacing the Phase 1 stub; exports PRRecord, CommentRecord, PRFile
- `tests/test_models.py` - 11 unit tests covering validation, optional fields, Literal constraints, reactions default, and JSON round-trip

## Decisions Made

- **ConfigDict(extra='ignore') on all models** — forward-compatible: new fields added by future phases won't cause ValidationError when loading existing cached files
- **Literal types for enums** — comment_type and state use Literal constraints instead of str, catching invalid values at model construction boundary rather than silently propagating
- **reactions mutable default is safe in Pydantic v2** — Pydantic v2's __init__ deep-copies model field defaults, so `reactions: dict[str, int] = {}` doesn't share state across instances (confirmed by test)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- PRRecord, CommentRecord, and PRFile are ready to be used by the extractor (plan 02-02)
- models.py is the data contract — extractor writes PRFile objects, classifier and generator consume them
- All 14 tests pass (11 model tests + 3 existing config tests), no regressions

---
*Phase: 02-github-extraction-core*
*Completed: 2026-04-03*

## Self-Check: PASSED

- FOUND: src/github_pr_kb/models.py
- FOUND: tests/test_models.py
- FOUND: .planning/phases/02-github-extraction-core/02-01-SUMMARY.md
- FOUND: commit bdd192a (test: RED phase)
- FOUND: commit bcad6d6 (feat: GREEN phase)
- All 14 tests pass (no regressions)
