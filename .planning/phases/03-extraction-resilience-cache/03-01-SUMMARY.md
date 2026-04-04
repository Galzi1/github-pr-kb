---
phase: 03-extraction-resilience-cache
plan: "01"
subsystem: extractor
tags: [resilience, rate-limit, atomic-writes, cache-merge, tdd]
dependency_graph:
  requires: [02-02]
  provides: [RateLimitExhaustedError, _write_cache_atomic, _merge_or_write]
  affects: [extractor.py, test_extractor.py]
tech_stack:
  added: [GithubRetry, tempfile.mkstemp, os.replace, pydantic.ValidationError]
  patterns: [atomic rename via mkstemp+os.replace, comment_id dedup set, try/except RetryError]
key_files:
  created: []
  modified:
    - src/github_pr_kb/extractor.py
    - tests/test_extractor.py
decisions:
  - "get_pulls() call moved inside try/except RetryError block — mock raises on call, not on iteration"
  - "Corrupt cache catches both json.JSONDecodeError and ValidationError — invalid JSON fails at parse, not Pydantic"
  - "Dedup by comment_id only (edited comments keep cached body) — accepted trade-off per CORE-05"
  - "RetryError message says rate limit but applies to any retry exhaustion — resume hint is valid regardless"
metrics:
  duration: 3 min
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_modified: 2
---

# Phase 3 Plan 01: Extraction Resilience and Cache Merge Summary

**One-liner:** Rate-limit retry via GithubRetry(total=5), atomic cache writes via mkstemp+os.replace, and comment_id dedup merge for re-run idempotency.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write 8 failing tests (RED) | 5891332 | tests/test_extractor.py |
| 2 | Implement resilience in extractor.py (GREEN) | 3c725ee | src/github_pr_kb/extractor.py |

## What Was Built

### RateLimitExhaustedError
Exception raised when GitHub API retry exhaustion occurs mid-extraction. Carries a progress count ("Extracted N PRs") and a resume hint ("Re-run the same command to resume"). Already-processed PRs are written to disk before the error is raised.

### _write_cache_atomic
Replaces old `_write_cache`. Uses `tempfile.mkstemp(dir=cache_path.parent, suffix=".tmp")` to create a temp file on the same filesystem volume, writes JSON via `os.fdopen`, then uses `os.replace` for an atomic rename. On failure, `contextlib.suppress(OSError)` cleans up the temp file. No `.tmp` orphans on successful completion.

### _merge_or_write
Loads existing `PRFile` from cache if present, builds `{c.comment_id for c in existing.comments}`, appends only net-new comments, writes atomically. Catches both `json.JSONDecodeError` and `ValidationError` for corrupt/schema-incompatible files — falls through to fresh write with a WARNING log. Returns `(cache_path, net_new_count)`.

### Updated extract()
- `Github(auth=..., retry=GithubRetry(total=5))` for automatic backoff
- `get_pulls()` call moved inside `try/except RetryError` block
- Loop calls `_merge_or_write` instead of `_write_cache`
- Logs `PR #N: M new comments merged` per PR
- Raises `RateLimitExhaustedError` on `RetryError` with progress + resume hint

## Test Coverage

21 tests pass in test_extractor.py (13 existing + 8 new). Full suite: 35 passed, 6 skipped (integration tests).

New tests added:
- `test_rate_limit_exhaustion` — RetryError -> RateLimitExhaustedError with resume hint
- `test_rate_limit_partial_flush` — processed PRs flushed before error
- `test_outside_window_not_fetched` — out-of-window cache byte-for-byte unchanged
- `test_inside_window_comments_merged` — 2 existing + 1 new = 3 (no duplicates)
- `test_no_duplicate_comment_ids` — re-run same comments stays at 2
- `test_merge_appends_new_only` — 1 existing + 1 new = 2, correct IDs
- `test_atomic_write_no_partial_file` — no .tmp files after extraction
- `test_corrupt_cache_full_fetch` — corrupt JSON replaced with valid 1-comment file

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `get_pulls()` raised RetryError before iteration began**
- **Found during:** Task 2 GREEN verification
- **Issue:** Plan spec had `pulls = self.repo.get_pulls(...)` outside try/except, but mock raised `RetryError` on the call itself (not during iteration). `test_rate_limit_exhaustion` failed.
- **Fix:** Moved `pulls = self.repo.get_pulls(...)` inside the `try` block so the exception is caught regardless of when it fires.
- **Files modified:** src/github_pr_kb/extractor.py
- **Commit:** 3c725ee (fixed inline before commit)

## Known Stubs

None — all data flows are wired. Cache merge reads/writes real files.

## Self-Check: PASSED
