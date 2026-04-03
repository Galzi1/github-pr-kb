---
phase: 02-github-extraction-core
plan: "02"
subsystem: api
tags: [pygithub, github-api, extraction, caching, json, pydantic, pytest, mocking]

# Dependency graph
requires:
  - phase: 02-01
    provides: PRRecord, CommentRecord, PRFile pydantic models used by extractor
provides:
  - GitHubExtractor class: authenticates via PAT, fetches PRs with state/date filters, writes per-PR JSON cache
  - is_noise() function: filters CI bots and non-substantive comments
  - SKIP_BOT_LOGINS frozenset: canonical bot login list for filtering
  - .github-pr-kb/cache/pr-N.json: per-PR cache file schema and location convention
affects: [03-resilience-cache, 04-classifier, 05-generator, 06-cli]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Auth.Token(token) for PyGithub authentication (not positional string)"
    - "get_pulls(state=, sort='updated', direction='desc') for lazy iteration with early-stop"
    - "model_dump(mode='json') for Pydantic v2 JSON serialization"
    - "conftest.py sets env var at module level (not fixture) to prevent import-time ValidationError"
    - "is_noise() gates all comment processing before building CommentRecord"

key-files:
  created:
    - src/github_pr_kb/extractor.py
    - tests/test_extractor.py
    - tests/conftest.py
  modified:
    - .gitignore

key-decisions:
  - "Break on since boundary (early-stop), continue on until boundary — both use pr.updated_at not created_at"
  - "SKIP_BOT_LOGINS is a frozenset of exact login strings; code review bots (Copilot, CodeRabbit) are NOT in it"
  - "is_noise() requires at least one 5+ char word — filters LGTM, emoji, +1 without explicit list"
  - "Reactions: store only non-zero counts for known keys (keeps JSON compact)"
  - "conftest.py sets GITHUB_TOKEN at module level to prevent pydantic ValidationError during pytest collection"
  - "PRs with zero comments after filtering still produce a cache file"

patterns-established:
  - "Noise filter pattern: check login first (cheap), then body regex (avoids regex on bot comments)"
  - "Cache write pattern: mkdir(parents=True, exist_ok=True) then write_text with utf-8 encoding"
  - "Deleted user fallback: check comment.user is not None, use '[deleted]' string"

requirements-completed: [CORE-01, CORE-02]

# Metrics
duration: 25min
completed: 2026-04-03
---

# Phase 2 Plan 02: GitHub Extractor Summary

**PyGithub-based GitHubExtractor that authenticates via PAT, iterates PRs with state/date filters and early-stop, filters CI bot noise and emoji-only comments while preserving review bot substantive feedback, and writes per-PR JSON cache files using Pydantic models**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-04-03T17:10:00Z
- **Completed:** 2026-04-03T17:35:00Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- GitHubExtractor class with Auth.Token authentication, state/date filtering, lazy iteration with early-stop
- is_noise() function filtering known CI bots and non-substantive comments (emoji-only, LGTM, single words)
- 12 extractor tests all passing GREEN using MagicMock PyGithub objects and tmp_path isolation
- Full test suite (26 tests: 12 extractor + 11 models + 3 config) passes with 96% coverage on extractor

## Task Commits

Each task was committed atomically:

1. **Task 1: Add .github-pr-kb/ to .gitignore** - `1899a40` (chore)
2. **Task 2: Create extractor test scaffolds with mocked PyGithub** - `50283ef` (test)
3. **Task 3: Implement GitHubExtractor with auth, filtering, noise detection, and cache write** - `5902379` (feat)

## Files Created/Modified

- `src/github_pr_kb/extractor.py` - GitHubExtractor class, is_noise(), _extract_reactions(), SKIP_BOT_LOGINS constant, DEFAULT_CACHE_DIR
- `tests/test_extractor.py` - 12 test functions with MagicMock PyGithub objects covering all filter/extraction behaviors
- `tests/conftest.py` - Session-scoped autouse fixture + module-level env var set for GITHUB_TOKEN
- `.gitignore` - Added `.github-pr-kb/` entry to prevent cache files from being committed

## Decisions Made

- `Auth.Token(settings.github_token)` used for authentication per PyGithub v2 API (not positional string)
- Early-stop (`break`) on `since` boundary because PRs are sorted desc by `updated_at` — remaining PRs are guaranteed older
- `continue` (not `break`) on `until` boundary — PRs after the upper bound are skipped but iteration continues to find in-range PRs
- `is_noise()` uses regex requiring at least one 5+ char word: catches LGTM, +1, emoji without maintaining an explicit list
- SKIP_BOT_LOGINS does NOT include `github-copilot[bot]` or `coderabbit[bot]` — these produce substantive review comments worth keeping
- `conftest.py` sets `GITHUB_TOKEN` at module level (before collection) because `config.py` instantiates `Settings()` at import time

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed conftest.py fixture scope — env var must be set at module level**

- **Found during:** Task 3 (running tests)
- **Issue:** The plan specified a session-scoped autouse fixture to set `GITHUB_TOKEN`, but `config.py` instantiates `settings = Settings()` at module level during import. A pytest fixture (even session-scoped) runs after collection, so the import fails with `ValidationError` before any fixture runs.
- **Fix:** Added `os.environ.setdefault("GITHUB_TOKEN", ...)` at conftest.py module level (before the fixture), and kept the fixture for documentation clarity.
- **Files modified:** `tests/conftest.py`
- **Verification:** All 26 tests pass; import succeeds during collection
- **Committed in:** `5902379` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - Bug)
**Impact on plan:** Necessary fix for test collection to succeed. No scope creep.

## Issues Encountered

- `uv` not on PATH in this shell environment — used full path `/c/Users/galzi/AppData/Local/Programs/Python/Python313/Scripts/uv.exe` for all commands
- `pytest-cov` was not in the virtual environment initially — installed via `uv run pip install pytest-cov`

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- GitHubExtractor is ready to be consumed by Phase 3 (Resilience & Cache) which adds retry logic and cache invalidation
- The per-PR JSON schema (`PRFile.model_dump(mode="json")`) is established and stable
- The `DEFAULT_CACHE_DIR = Path(".github-pr-kb/cache")` convention is established for all future phases
- No blockers

---
*Phase: 02-github-extraction-core*
*Completed: 2026-04-03*
