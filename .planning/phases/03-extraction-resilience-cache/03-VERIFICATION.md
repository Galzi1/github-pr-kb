---
phase: 03-extraction-resilience-cache
verified: 2026-04-04T00:00:00Z
status: passed
score: 6/6 must-haves verified
re_verification: false
---

# Phase 3: Extraction Resilience & Cache Verification Report

**Phase Goal:** Extraction survives GitHub rate limits and interrupted runs — already-cached comments are never re-fetched, using PR + comment ID as the immutable dedup key.
**Verified:** 2026-04-04
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | When GitHub API returns 429 or rate-limit header, the tool retries up to 5 times then raises RateLimitExhaustedError with progress count and resume hint | VERIFIED | `GithubRetry(total=5)` at line 114; `RateLimitExhaustedError` at line 43; `except RetryError` at line 247 raises with message containing "Re-run the same command to resume"; `test_rate_limit_exhaustion` passes |
| 2 | Already-cached PRs are flushed to disk before rate-limit error is raised | VERIFIED | `_merge_or_write` called per PR inside the try block before exception propagates; `test_rate_limit_partial_flush` verifies pr-1.json and pr-2.json exist after RetryError on pr3 |
| 3 | Re-running extraction on the same repo merges new comments into existing cache files without duplicating entries | VERIFIED | `_merge_or_write` builds `existing_ids` set (line 167) and filters `net_new` (line 168); `test_inside_window_comments_merged` and `test_no_duplicate_comment_ids` pass |
| 4 | PRs outside the active date window keep their existing cache untouched on re-run | VERIFIED | `since` early-stop logic (line 234) exits loop before calling `_merge_or_write`; `test_outside_window_not_fetched` asserts byte-for-byte identity and passes |
| 5 | Cache writes are atomic — interrupted writes leave no partial files | VERIFIED | `_write_cache_atomic` uses `tempfile.mkstemp` + `os.replace` (lines 139-142); cleanup on exception at lines 144-146; `test_atomic_write_no_partial_file` passes |
| 6 | Corrupt cache files are treated as missing and re-fetched cleanly | VERIFIED | `except (json.JSONDecodeError, ValidationError)` at line 176 logs warning and falls through to fresh write; `test_corrupt_cache_full_fetch` passes |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/github_pr_kb/extractor.py` | RateLimitExhaustedError, _write_cache_atomic, _merge_or_write, updated extract() with GithubRetry(total=5) | VERIFIED | All four present; `class RateLimitExhaustedError(Exception)` at line 43; `_write_cache_atomic` at line 130; `_merge_or_write` at line 149; `GithubRetry(total=5)` at line 114; old `_write_cache` absent |
| `tests/test_extractor.py` | 8 new test functions covering CORE-03, CORE-04, CORE-05, D-06 | VERIFIED | All 8 functions present (lines 385-581); `test_rate_limit_exhaustion` at line 385; all 21 tests pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/github_pr_kb/extractor.py` | `github.GithubRetry` | `GithubRetry(total=5)` passed to `Github()` constructor | WIRED | Line 114: `retry=GithubRetry(total=5)` |
| `src/github_pr_kb/extractor.py` | `os.replace` | atomic write via mkstemp + os.replace | WIRED | Line 142: `os.replace(tmp_name, str(cache_path))` inside `_write_cache_atomic` |
| `src/github_pr_kb/extractor.py` | `requests.exceptions.RetryError` | catch RetryError from PyGithub after retry exhaustion | WIRED | Line 247: `except RetryError as exc:` wraps entire `get_pulls` + iteration block |

### Data-Flow Trace (Level 4)

`_merge_or_write` is not a rendering component — it reads from and writes to disk. Data flow verified at code level:

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `_merge_or_write` | `existing` (PRFile) | `cache_path.read_text()` + `PRFile.model_validate()` | Yes — reads actual disk file | FLOWING |
| `_merge_or_write` | `net_new` | filtered from `new_comments` minus `existing_ids` set | Yes — real comment records from PyGithub | FLOWING |
| `_write_cache_atomic` | `pr_file` JSON | `pr_file.model_dump(mode="json")` | Yes — serializes real PRFile model | FLOWING |
| `extract()` | `written_paths` | `_merge_or_write` return value | Yes — real disk paths | FLOWING |

### Behavioral Spot-Checks

All behaviors verified by passing pytest suite (not by running server):

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| RetryError raises RateLimitExhaustedError with resume hint | `pytest test_rate_limit_exhaustion` | PASS | PASS |
| Partial flush — pr-1.json and pr-2.json exist before error | `pytest test_rate_limit_partial_flush` | PASS | PASS |
| Out-of-window cache byte-for-byte unchanged | `pytest test_outside_window_not_fetched` | PASS | PASS |
| Merge: 2 existing + 1 new = 3 (no duplicates) | `pytest test_inside_window_comments_merged` | PASS | PASS |
| Re-run same comments stays at 2 | `pytest test_no_duplicate_comment_ids` | PASS | PASS |
| Merge 1+1=2, correct IDs {1001, 2001} | `pytest test_merge_appends_new_only` | PASS | PASS |
| No .tmp files after extraction | `pytest test_atomic_write_no_partial_file` | PASS | PASS |
| Corrupt cache replaced, not crashed | `pytest test_corrupt_cache_full_fetch` | PASS | PASS |
| Full extractor test suite (21 tests) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py` | 21 passed | PASS |
| Full project test suite (35+6) | `.venv/Scripts/python.exe -m pytest tests/` | 35 passed, 6 skipped | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| CORE-03 | 03-01-PLAN.md | Tool handles GitHub API rate limits with exponential backoff and resumes without data loss | SATISFIED | `GithubRetry(total=5)` provides exponential backoff; `except RetryError` block flushes processed PRs before raising `RateLimitExhaustedError`; `test_rate_limit_exhaustion` + `test_rate_limit_partial_flush` verify both behaviors |
| CORE-04 | 03-01-PLAN.md | Extracted comments are cached locally (JSON) so re-runs avoid redundant API calls | SATISFIED | `_merge_or_write` loads existing cache and appends only net-new comments; PRs outside date window are skipped entirely (early-stop at `since` boundary); `test_outside_window_not_fetched` + `test_inside_window_comments_merged` verify |
| CORE-05 | 03-01-PLAN.md | Extraction is idempotent — re-running does not duplicate cached data (PR+comment ID as key) | SATISFIED | `existing_ids = {c.comment_id for c in existing.comments}` at line 167; `net_new = [c for c in new_comments if c.comment_id not in existing_ids]` at line 168; `test_no_duplicate_comment_ids` + `test_merge_appends_new_only` verify |

No orphaned requirements — REQUIREMENTS.md traceability table maps only CORE-03, CORE-04, CORE-05 to Phase 3, all of which are covered by plan 03-01.

### Anti-Patterns Found

No anti-patterns found. Scan results:

| File | Pattern | Severity | Result |
|------|---------|----------|--------|
| `extractor.py` | TODO/FIXME/PLACEHOLDER | — | None found |
| `extractor.py` | `def _write_cache(self` (old stub method) | — | Not present (correctly removed) |
| `extractor.py` | `return null / return []` stub patterns | — | None found |
| `test_extractor.py` | TODO/FIXME/PLACEHOLDER | — | None found |

Notable: `_merge_or_write` uses `return cache_path, len(net_new)` which correctly returns real path + real count, not stubs.

### Human Verification Required

None. All phase behaviors are verifiable programmatically via the test suite. Visual or UX items are not applicable — this is a Python library module with no UI surface.

### Gaps Summary

No gaps. All 6 observable truths are verified by substantive, wired, and data-flowing implementation. All 3 requirement IDs (CORE-03, CORE-04, CORE-05) are satisfied with passing tests. The old `_write_cache` method is correctly absent. No anti-patterns or stubs detected.

The SUMMARY deviation note (moving `get_pulls()` inside the `try/except RetryError` block) was a correct auto-fix — the production code reflects this fix at lines 229-255.

---

_Verified: 2026-04-04_
_Verifier: Claude (gsd-verifier)_
