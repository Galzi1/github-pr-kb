---
phase: 04-claude-classifier
plan: 02
subsystem: api
tags: [anthropic, classifier, pydantic, sha256, dedup, atomic-writes]

# Dependency graph
requires:
  - phase: 04-claude-classifier-plan-01
    provides: ClassifiedComment, ClassifiedFile, CategoryLiteral models and 7 TDD RED tests
  - phase: 03-extraction-resilience-cache
    provides: PRFile, CommentRecord, PRRecord models and pr-N.json cache file pattern
provides:
  - PRClassifier class with classify_pr() and classify_all() methods
  - SHA-256 body_hash() function for content-hash dedup
  - classification-index.json read/write with corrupt-index recovery
  - classified-pr-N.json atomic output files
  - print_summary() for classification run metrics
affects: [06-cli-wiring]

# Tech tracking
tech-stack:
  added: [anthropic SDK (runtime use, not just test scaffolding)]
  patterns:
    - SHA-256 content-hash dedup — body_hash(body) => classification-index.json lookup before any API call
    - Atomic file write pattern (mkstemp + os.replace) — same as extractor.py, applied to classified-pr-N.json and index
    - Explicit api_key constructor parameter — falls back to settings.anthropic_api_key; ValueError if still None
    - Category normalization + confidence clamping — guard against malformed API responses

key-files:
  created: [src/github_pr_kb/classifier.py]
  modified: []

key-decisions:
  - "body_hash is a public function (not _body_hash) — tests import it directly from classifier module"
  - "classify_pr returns ClassifiedFile (not list[ClassifiedComment]) — tests are authoritative over plan prose"
  - "PRClassifier.__init__ takes explicit api_key parameter — tests pass api_key='sk-ant-fake'; falls back to settings if None"
  - "classification-index.json written atomically after each successful API call — prevents data loss on crash mid-run"
  - "anthropic.APIError caught at base class level — covers RateLimitError, AuthenticationError, APIStatusError uniformly"

patterns-established:
  - "Tests are authoritative when plan prose and test code conflict — implementation matched tests, not plan description"
  - "Corrupt index recovery: log WARNING (not silent), return empty dict, rebuild from scratch on next classify run"

requirements-completed: [CLASS-01, CLASS-02, CLASS-03, CLASS-04]

# Metrics
duration: 2min
completed: 2026-04-05
---

# Phase 04 Plan 02: PRClassifier Implementation Summary

**PRClassifier with SHA-256 comment dedup, anthropic.APIError handling, atomic writes, and category normalization — all 7 TDD RED tests turned GREEN**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-05T10:29:07Z
- **Completed:** 2026-04-05T10:31:59Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments

- Implemented PRClassifier with classify_pr() returning ClassifiedFile and classify_all() globbing pr-*.json
- SHA-256 dedup via body_hash() + classification-index.json prevents redundant Claude API calls (CLASS-03)
- All 7 classifier tests pass GREEN; full suite 42 passed, 6 skipped (integration only), 0 failed

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement PRClassifier in classifier.py** - `b45a9fa` (feat)
2. **Task 2: Make all classifier tests pass (GREEN phase)** - no separate commit needed — tests passed without modification on first run

**Plan metadata:** (docs commit — see below)

## Files Created/Modified

- `src/github_pr_kb/classifier.py` - Full PRClassifier implementation: body_hash, _write_atomic, _load_index, _save_index, _classify_comment, classify_pr, classify_all, print_summary

## Decisions Made

- `body_hash` is a public function because tests import it directly: `from github_pr_kb.classifier import body_hash`. Plan said `_body_hash` (private) but tests are authoritative.
- `classify_pr` returns `ClassifiedFile`, not `list[ClassifiedComment]` as plan prose stated — tests showed the correct return type.
- `PRClassifier.__init__` accepts explicit `api_key` parameter (with fallback to `settings.anthropic_api_key`) so tests can inject a fake key without mocking settings.
- `classification-index.json` is written atomically after each individual API call (not batched at end) — prevents losing all classifications on crash mid-run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Public body_hash vs private _body_hash**
- **Found during:** Task 1 (reading test_classifier.py before implementing)
- **Issue:** Plan specified `def _body_hash(body: str) -> str:` (private, with leading underscore), but tests import `from github_pr_kb.classifier import body_hash` (public name)
- **Fix:** Implemented as `body_hash` (public) to match the tests — tests are the source of truth
- **Files modified:** src/github_pr_kb/classifier.py
- **Verification:** test_body_hash_deterministic and test_body_hash_different_bodies both PASSED
- **Committed in:** b45a9fa (Task 1 commit)

**2. [Rule 1 - Bug] classify_pr return type: ClassifiedFile not list[ClassifiedComment]**
- **Found during:** Task 1 (reading test_classifier.py before implementing)
- **Issue:** Plan specified `classify_pr(self, pr_number: int) -> list[ClassifiedComment]`, but tests do `result = classifier.classify_pr(1)` then assert `isinstance(result, ClassifiedFile)` and `len(result.classifications) == 1`
- **Fix:** Implemented `classify_pr` to return `ClassifiedFile` to match tests
- **Files modified:** src/github_pr_kb/classifier.py
- **Verification:** All 5 tests calling classify_pr PASSED (including test_classified_comment_fields, test_cache_hit_no_api_call)
- **Committed in:** b45a9fa (Task 1 commit)

**3. [Rule 1 - Bug] PRClassifier constructor needs explicit api_key parameter**
- **Found during:** Task 1 (reading test_classifier.py before implementing)
- **Issue:** Plan specified constructor reads only from settings; tests pass `PRClassifier(cache_dir=..., api_key="sk-ant-fake")` directly
- **Fix:** Added `api_key: str | None = None` parameter to `__init__` with fallback to `settings.anthropic_api_key`
- **Files modified:** src/github_pr_kb/classifier.py
- **Verification:** All 5 tests instantiating PRClassifier PASSED without mocking settings
- **Committed in:** b45a9fa (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 — plan prose vs test code mismatches)
**Impact on plan:** All fixes were necessary to match the TDD RED tests that defined the contract. No scope creep. The plan's intent (body hashing, classify_pr, constructor config) was fully delivered — only signatures differed.

## Issues Encountered

None beyond the plan/test mismatches documented above. Tests passed on first run after implementation.

## User Setup Required

None - no external service configuration required. ANTHROPIC_API_KEY will be needed for running the actual classify command, but the test suite uses `api_key="sk-ant-fake"` directly.

## Next Phase Readiness

- PRClassifier is fully implemented and tested — ready for CLI wiring in Phase 6
- `classify_pr(pr_number)` and `classify_all()` are the entry points for CLI integration
- classification-index.json dedup is transparent to callers — cache hit behavior is automatic
- No blockers

## Known Stubs

None — classifier.py is fully wired. classify_pr reads real pr-N.json files from cache, calls real Claude API (mocked in tests), writes real classified-pr-N.json output.

## Self-Check: PASSED

- FOUND: src/github_pr_kb/classifier.py
- FOUND commit: b45a9fa (Task 1)
- VERIFIED: .venv/Scripts/python.exe -m pytest tests/test_classifier.py -v — 7 PASSED
- VERIFIED: .venv/Scripts/python.exe -m pytest tests/ -x — 42 passed, 6 skipped, 0 failed

---
*Phase: 04-claude-classifier*
*Completed: 2026-04-05*
