# Phase 3: Extraction Resilience & Cache - Research

**Researched:** 2026-04-04
**Domain:** Python retry patterns, atomic file I/O, PyGithub rate-limit internals, merge-based cache updates
**Confidence:** HIGH

## Summary

Phase 3 extends the existing `GitHubExtractor` class with three interlocking capabilities: (1) exponential backoff on GitHub 429/403 rate-limit responses with configurable retry exhaustion, (2) atomic writes to prevent corrupt cache files on interruption, and (3) merge-based re-runs that append only net-new comments (by comment ID) to already-cached PR files rather than overwriting or skipping them.

PyGithub 2.8.1 (installed) ships with `GithubRetry(total=10)` as its default `retry` parameter. This class handles 403 and 429 responses silently — it inspects the response body, waits until `X-RateLimit-Reset`, and retries up to 10 times without raising an exception. The CONTEXT decisions call for only 5 retries with a clear error on exhaustion. The implementation must therefore pass `retry=GithubRetry(total=5)` explicitly when constructing `Github()`, so that after 5 exhausted retries `requests.exceptions.RetryError` propagates to caller code where it can be caught, converted to a user-readable message, and the accumulated cache flushed.

Atomic writes on Windows use `tempfile.NamedTemporaryFile(mode='w', dir=cache_dir, suffix='.tmp', delete=False)` followed by `os.replace(tmp.name, target_path)` — verified working on Python 3.14 / Windows 11. The temp file must be in the same directory as the target to guarantee both are on the same filesystem volume; this makes `os.replace` atomic on Windows.

**Primary recommendation:** Extend `GitHubExtractor` in-place — add `_write_cache_atomic`, `_merge_or_write`, and a `_run_with_retry` wrapper. Wire `GithubRetry(total=5)` into the `Github()` constructor at extractor init time to get exactly 5 retries before exception propagation.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** On re-run, merge new comments into existing cache files — do not skip cached PRs entirely. Compare comment IDs; append only those not already present.

**D-02:** Merging applies only to PRs whose `updated_at` falls within the active `since`/`until` date filter window. PRs outside the window keep their existing cache untouched.

**D-03:** Use exponential backoff for GitHub 429 responses and `X-RateLimit-Remaining=0`: start at ~1s, double per retry, cap at ~60s, max 5 retries.

**D-04:** On retry exhaustion, save all successfully-cached PRs to disk, then raise an error with a clear progress + resume message (not a raw traceback).

**D-05:** Use file-exists check to determine resume state — if `pr-{number}.json` exists, merge new comments; if missing, fetch fresh. No separate checkpoint file.

**D-06:** Use atomic writes (write to temp file, then rename to `pr-{number}.json`) to prevent partial/corrupt cache files on interruption.

**D-07:** Use Python stdlib `logging` module — INFO for per-PR progress ("PR #42: 3 new comments merged"), WARNING for retries ("Rate limited, retrying in 4s"), ERROR for failures.

**D-08:** On rate-limit exit, message includes progress count and resume hint: "Extracted 12/45 PRs before rate limit exhaustion. Re-run the same command to resume."

### Claude's Discretion

- Exponential backoff implementation details (jitter, exact timing constants)
- Whether to use PyGithub's built-in rate-limit awareness as a complement to the custom retry wrapper
- Logging format and logger naming conventions
- Temp file naming scheme for atomic writes

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-03 | Tool handles GitHub API rate limits with exponential backoff and resumes without data loss | GithubRetry(total=5) raises RetryError after 5 exhausted attempts; catch at extract() level, flush cache, raise RateLimitError with progress message |
| CORE-04 | Extracted comments are cached locally (JSON) so re-runs avoid redundant API calls | File-exists check in extract() loop; existing files → merge path; missing files → full fetch path |
| CORE-05 | Extraction is idempotent — re-running does not duplicate cached data (PR+comment ID as key) | _merge_or_write: load existing PRFile, build set of existing comment_ids, append only new ones |
</phase_requirements>

---

## Standard Stack

### Core (already installed — no new dependencies required)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGithub | 2.8.1 (installed) | GitHub API access + GithubRetry | Already in use; GithubRetry handles 403/429 backoff; `total=` param controls retry count |
| pydantic | 2.12.5 (installed) | PRFile/CommentRecord deserialization for merge path | Already in use; `model_validate` loads existing cache files cleanly |
| Python stdlib: `logging` | 3.14 (installed) | Progress/warning/error output | Decided in D-07; no third-party dependency |
| Python stdlib: `tempfile`, `os` | 3.14 (installed) | Atomic file writes | `NamedTemporaryFile` + `os.replace` — stdlib-only, verified on Windows |
| Python stdlib: `json` | 3.14 (installed) | Serialize/deserialize cache files | Already in use |

**No new packages to install.** All required functionality is available in PyGithub 2.8.1 and the Python stdlib.

### Supporting (discretion area)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `random` (stdlib) | 3.14 | Full-jitter on backoff delays | If adding jitter to avoid thundering herd — `random.uniform(0, delay)` for full-jitter |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `GithubRetry(total=5)` | `tenacity` library | tenacity is more expressive but adds a dep; GithubRetry already understands GitHub headers; CONTEXT says no new deps implied |
| `os.replace` | `python-atomicwrites` library | atomicwrites adds a dep; `os.replace` is stdlib and verified on Windows 11 / Python 3.14 |
| stdlib `logging` | `structlog` | structlog has richer output but D-07 locked stdlib logging |

---

## Architecture Patterns

### Recommended Change Surface

Only `extractor.py` changes in this phase. Models and config are untouched. Test files are added/extended.

```
src/github_pr_kb/
└── extractor.py     # Three targeted additions:
                     #   1. _write_cache_atomic (replaces _write_cache)
                     #   2. _merge_or_write (new: load existing, diff IDs, write merged)
                     #   3. extract() updated: GithubRetry(total=5) in Github(), file-exists
                     #      branch, RetryError catch with flush + user message

tests/
└── test_extractor.py     # Extend with resilience scenarios
    test_resilience.py    # OR new file — rate-limit mocks, atomic write, merge tests
```

### Pattern 1: Configuring GithubRetry with a bounded total

PyGithub 2.8.1 default is `GithubRetry(total=10)`. To enforce exactly 5 retries:

```python
# Source: PyGithub source (inspected locally) + GitHub docs on retry-after/x-ratelimit-reset
from github import Auth, Github, GithubRetry

client = Github(auth=Auth.Token(settings.github_token), retry=GithubRetry(total=5))
```

After 5 exhausted retries, `requests.exceptions.RetryError` propagates from the PyGithub internals. Catch this at the `extract()` level.

**Key insight:** `GithubRetry` already reads `X-RateLimit-Reset` for primary rate limits and waits until the reset window. Setting `total=5` means: attempt up to 5 waits for the reset window before giving up. Do NOT add a second layer of sleep on top of this — the library already sleeps correctly.

### Pattern 2: Atomic Write (temp-then-replace)

```python
# Source: Python docs tempfile + os.replace; verified on Windows 11 / Python 3.14
import json
import os
import tempfile
from pathlib import Path

def _write_cache_atomic(self, cache_path: Path, pr_file: PRFile) -> None:
    """Write pr_file to cache_path atomically (temp file + os.replace)."""
    payload = json.dumps(pr_file.model_dump(mode="json"), indent=2)
    tmp_fd, tmp_name = tempfile.mkstemp(dir=cache_path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_name, cache_path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
```

**Why `mkstemp` over `NamedTemporaryFile`:** `mkstemp` returns a raw file descriptor and is reliably usable on Windows without the file-locking quirk of `NamedTemporaryFile` when `delete=True`. Both work with `delete=False`; `mkstemp` is slightly more explicit. Either is acceptable.

**Critical:** `dir=cache_path.parent` ensures temp file and target are on the same volume, making `os.replace` atomic on Windows.

### Pattern 3: Merge-Based Cache Update

```python
# Source: design from CONTEXT.md D-01/D-05, uses existing PRFile/CommentRecord models
def _merge_or_write(self, pr: PullRequest, new_comments: list[CommentRecord]) -> tuple[Path, int]:
    """
    If pr-{number}.json exists, load it, append only net-new comments (by comment_id),
    and write atomically. If missing, write fresh. Returns (path, new_count).
    """
    cache_path = self.cache_dir / f"pr-{pr.number}.json"
    if cache_path.exists():
        existing: PRFile = PRFile.model_validate(
            json.loads(cache_path.read_text(encoding="utf-8"))
        )
        existing_ids = {c.comment_id for c in existing.comments}
        net_new = [c for c in new_comments if c.comment_id not in existing_ids]
        merged = PRFile(
            pr=existing.pr,
            comments=existing.comments + net_new,
            extracted_at=datetime.now(timezone.utc),
        )
        self._write_cache_atomic(cache_path, merged)
        return cache_path, len(net_new)
    else:
        pr_record = PRRecord(number=pr.number, title=pr.title, body=pr.body,
                             state=pr.state, url=pr.html_url)
        pr_file = PRFile(pr=pr_record, comments=new_comments,
                         extracted_at=datetime.now(timezone.utc))
        self._write_cache_atomic(cache_path, pr_file)
        return cache_path, len(new_comments)
```

### Pattern 4: Rate-Limit Catch with Flush + User Message

```python
# Source: CONTEXT.md D-04/D-08; PyGithub source (GithubRetry raises RetryError after total exhausted)
from requests.exceptions import RetryError

def extract(self, ...):
    ...
    processed = 0
    total_prs: int | None = None   # unknown until iteration ends or stops early
    try:
        for pr in pulls:
            ...
            path, new_count = self._merge_or_write(pr, comments)
            processed += 1
            logger.info("PR #%d: %d new comments merged", pr.number, new_count)
    except RetryError as exc:
        logger.error(
            "Extracted %d PRs before rate limit exhaustion. "
            "Re-run the same command to resume.",
            processed,
        )
        raise RateLimitExhaustedError(
            f"Extracted {processed} PRs before rate limit exhaustion. "
            "Re-run the same command to resume."
        ) from exc
    return written_paths
```

**`RateLimitExhaustedError`** should be a project-defined exception (subclass of `Exception`) so callers can distinguish it from other failures. Define in `extractor.py` alongside the class.

### Pattern 5: Logging Setup

```python
import logging
logger = logging.getLogger(__name__)   # "github_pr_kb.extractor" — follows module path
```

Callers configure the root logger level. Tests can assert `caplog` records (pytest's built-in log capture).

### Anti-Patterns to Avoid

- **Double-sleeping on rate limits:** `GithubRetry` already sleeps until `X-RateLimit-Reset`. Adding `time.sleep()` on top of this will double the wait time with no benefit.
- **Using `retry=None` (no built-in retry) and reimplementing everything from scratch:** GithubRetry's header-aware backoff is well-tested; CONTEXT.md says using it as a complement is acceptable. Use `GithubRetry(total=5)` rather than `retry=None` + custom sleep loop.
- **Writing cache before comment collection:** If comment collection raises, an empty or partial cache file would be written. Always collect first, then write atomically.
- **Using `os.rename` instead of `os.replace`:** `os.rename` raises `FileExistsError` on Windows if the destination exists. `os.replace` is the correct cross-platform atomic replacement call.
- **Leaving temp files on disk after failure:** Always `os.unlink` the temp file in the `except` block.
- **Opening `NamedTemporaryFile` without closing before `os.replace`:** On Windows, an open file handle blocks `os.replace`. Always close the temp file before calling `os.replace`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub 403/429 backoff + header parsing | Custom `time.sleep` loop inspecting response headers | `GithubRetry(total=5)` passed to `Github()` | GithubRetry parses `X-RateLimit-Reset`, `Retry-After`, and the response body message; getting this right manually has many edge cases |
| Atomic file write | `path.write_text()` with try/except | `mkstemp` + `os.replace` | Plain `write_text` leaves partial file on crash; `os.replace` is atomic on both Windows and Linux |
| Dedup of comments | Content hash or string compare | `comment_id` integer set | GitHub comment IDs are immutable and globally unique per repo; set membership check is O(1) and exact |

**Key insight:** PyGithub's `GithubRetry` is essentially a battle-tested implementation of the GitHub REST API retry recommendations. Treat it as infrastructure, not something to replace.

---

## Common Pitfalls

### Pitfall 1: PyGithub default retry silently waits forever

**What goes wrong:** With `GithubRetry(total=10)` (the default), hitting a primary rate limit causes PyGithub to silently sleep for up to 855s (the remaining rate-limit window) then retry. The user sees nothing, the process hangs, and if it keeps hitting limits it will retry 10 times before finally raising `RetryError`. This can mean 10 × 855s = 2.4 hours of silent sleeping.

**Why it happens:** `GithubRetry` calculates backoff from `X-RateLimit-Reset` header and sleeps internally via urllib3's `Retry.sleep()`. There is no exception raised until `total` is exhausted.

**How to avoid:** Pass `retry=GithubRetry(total=5)` explicitly. This caps silent retry count at 5. Add a `WARNING` log in the retry path — but note that `GithubRetry` logs at `INFO`/`DEBUG` internally (to `github.GithubRetry` logger), so configure the application logger to surface those.

**Warning signs:** Process appears to hang for many minutes between log lines.

### Pitfall 2: `os.rename` raises `FileExistsError` on Windows

**What goes wrong:** `os.rename(src, dst)` where `dst` already exists raises `FileExistsError` on Windows (unlike POSIX where it atomically replaces).

**Why it happens:** Windows semantics for `MoveFile` without `MOVEFILE_REPLACE_EXISTING` flag.

**How to avoid:** Always use `os.replace` (not `os.rename`). `os.replace` passes the `MOVEFILE_REPLACE_EXISTING` flag and works correctly on Windows.

**Warning signs:** `FileExistsError: [WinError 183] Cannot create a file when that file already exists` on second run.

### Pitfall 3: Temp file on different drive than target

**What goes wrong:** If `tempfile.mkstemp()` is called without `dir=`, Python picks the system temp directory (e.g., `C:\Users\user\AppData\Local\Temp`). If the cache is on a different drive (e.g., `D:\`), `os.replace` will fail with `OSError: [WinError 17] The system cannot move the file to a different disk drive`.

**Why it happens:** Atomic rename is only possible within the same filesystem volume.

**How to avoid:** Always pass `dir=cache_path.parent` to `mkstemp` / `NamedTemporaryFile`.

### Pitfall 4: Merging when PRFile deserialization fails

**What goes wrong:** An existing `pr-{number}.json` is partially written (from a previous interrupted non-atomic write). `PRFile.model_validate()` raises `ValidationError`. If uncaught, the merge path crashes and the PR is not updated.

**Why it happens:** Pre-Phase-3 code used `Path.write_text()` directly, which is not atomic. Any existing corrupted files must be handled.

**How to avoid:** Wrap `PRFile.model_validate()` in a try/except `ValidationError`. On failure, log a WARNING and fall through to the full-fetch path (treat the file as missing).

**Warning signs:** `pydantic.ValidationError` during `_merge_or_write` on an existing cache file.

### Pitfall 5: Catching `RetryError` too broadly

**What goes wrong:** `requests.exceptions.RetryError` is raised for any connection error after retries — not just rate limits. Catching it and printing a rate-limit message when the real problem was a network timeout misleads the user.

**Why it happens:** `GithubRetry` raises `RetryError` (wrapping `MaxRetryError`) for all retry-exhaustion cases, not just rate limits.

**How to avoid:** Inspect `str(exc)` or `exc.__cause__` for rate-limit indicators when constructing the user message, or keep the message generic enough to cover both: "GitHub API call failed after 5 retries. Re-run the same command to resume from PR #N."

---

## Code Examples

### Verified: GithubRetry constructor (inspected from installed PyGithub 2.8.1)

```python
# Source: .venv/Lib/site-packages/github/GithubRetry.py (inspected locally)
from github import GithubRetry

# Default: GithubRetry(total=10, secondary_rate_wait=60.0)
# For Phase 3: limit to 5 retries
retry = GithubRetry(total=5)
```

### Verified: GithubException / headers access

```python
# Source: inspected locally — GithubException.headers is a dict[str, str] | None
from github.GithubException import GithubException

# exc.status   → int HTTP status code (403 or 429)
# exc.headers  → dict with 'x-ratelimit-remaining', 'x-ratelimit-reset', 'retry-after'
# exc.data     → decoded JSON response body
```

### Verified: Atomic write on Windows (tested locally)

```python
# Source: Python docs + local test on Windows 11 / Python 3.14
import contextlib
import json
import os
import tempfile
from pathlib import Path

def write_atomic(path: Path, content: str) -> None:
    """Write content to path atomically via temp file + os.replace."""
    tmp_fd, tmp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_name, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
```

### Verified: RetryError import path

```python
# Source: requests library (installed as PyGithub dependency)
from requests.exceptions import RetryError  # raised by PyGithub after GithubRetry exhausts total
```

### Verified: Logger naming convention

```python
import logging
# Module-level — produces "github_pr_kb.extractor" logger name
logger = logging.getLogger(__name__)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PyGithub positional token string | `Github(auth=Auth.Token(token))` | PyGithub v2 | Already adopted in Phase 2 |
| Manual `time.sleep` + exception catch | `GithubRetry` passed to `Github(retry=...)` | PyGithub 1.58+ (2022) | Built-in backoff with header awareness; no custom sleep loop needed |
| `path.write_text()` cache writes | `mkstemp` + `os.replace` atomic writes | Phase 3 | Prevents corrupt files on interruption |

**Deprecated/outdated:**
- `os.rename` for atomic replace on Windows: replaced by `os.replace` (Python 3.3+)
- PyGithub `login_or_token` positional arg: deprecated since PyGithub v2, use `auth=Auth.Token()`

---

## Open Questions

1. **Should `GithubRetry`'s internal INFO/DEBUG logs be surfaced to the user?**
   - What we know: `GithubRetry` logs retry events to `logging.getLogger("github.GithubRetry")` at INFO/DEBUG level. These won't appear unless the caller configures that logger.
   - What's unclear: CONTEXT.md says use WARNING for retries in the extractor. There may be duplicate/confusing log output if both the library and extractor log retries.
   - Recommendation: Log at WARNING in extractor's `extract()` catch path. Do not configure `github.GithubRetry` logger in this phase — leave it to the CLI phase (Phase 6) to configure overall log verbosity.

2. **Is `total=5` in `GithubRetry` per-request or per-session?**
   - What we know: `GithubRetry(total=5)` is per-request (each API call gets 5 retries). A session with 100 PRs × 2 API calls = 200 calls, each independently getting 5 retry attempts.
   - What's unclear: CONTEXT.md D-03 says "max 5 retries" — it likely means 5 retries per rate-limit event, which is what `total=5` provides.
   - Recommendation: Use `GithubRetry(total=5)` as-is. Document that it's per-request.

---

## Environment Availability

Step 2.6: SKIPPED (no new external dependencies — all tools are already in the venv and stdlib).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py -x` |
| Full suite command | `.venv/Scripts/python.exe -m pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-03 | `RetryError` caught → RateLimitExhaustedError raised with message | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_rate_limit_exhaustion -x` | ❌ Wave 0 |
| CORE-03 | Per-PR cache flushed before error raised | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_rate_limit_partial_flush -x` | ❌ Wave 0 |
| CORE-04 | Second run skips fetch for PRs outside date window | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_outside_window_not_fetched -x` | ❌ Wave 0 |
| CORE-04 | Second run fetches fresh comments for PRs inside window | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_inside_window_comments_merged -x` | ❌ Wave 0 |
| CORE-05 | Re-running produces no duplicate comment IDs | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_no_duplicate_comment_ids -x` | ❌ Wave 0 |
| CORE-05 | Merge path appends only net-new comments | unit (mock) | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_merge_appends_new_only -x` | ❌ Wave 0 |
| D-06 | Interrupted write leaves no partial file (atomic write) | unit | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_atomic_write_no_partial_file -x` | ❌ Wave 0 |
| D-06 | Corrupt existing cache falls through to full fetch | unit | `.venv/Scripts/python.exe -m pytest tests/test_extractor.py::test_corrupt_cache_full_fetch -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/Scripts/python.exe -m pytest tests/test_extractor.py -x`
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All 8 new tests listed above need to be added — all to `tests/test_extractor.py` (continuing the established pattern). No new test files required; no new fixtures. `conftest.py` already sets `GITHUB_TOKEN` at module level.

- [ ] `tests/test_extractor.py::test_rate_limit_exhaustion` — covers CORE-03 (mock `RetryError`, assert `RateLimitExhaustedError`)
- [ ] `tests/test_extractor.py::test_rate_limit_partial_flush` — covers CORE-03 (2 PRs processed before error, verify both cache files written)
- [ ] `tests/test_extractor.py::test_outside_window_not_fetched` — covers CORE-04 (PR outside `since`/`until` with existing cache → API not called)
- [ ] `tests/test_extractor.py::test_inside_window_comments_merged` — covers CORE-04 (existing cache + new PR comments → merged file)
- [ ] `tests/test_extractor.py::test_no_duplicate_comment_ids` — covers CORE-05 (identical comment IDs on re-run → count unchanged)
- [ ] `tests/test_extractor.py::test_merge_appends_new_only` — covers CORE-05 (2 existing + 1 new → 3 total, not 4)
- [ ] `tests/test_extractor.py::test_atomic_write_no_partial_file` — covers D-06 (verify write_atomic leaves no .tmp file on success)
- [ ] `tests/test_extractor.py::test_corrupt_cache_full_fetch` — covers Pitfall 4 (put corrupted JSON in cache dir → extractor treats as missing)

---

## Sources

### Primary (HIGH confidence)

- PyGithub 2.8.1 source — `GithubRetry.py`, `GithubException.py`, `Github.__init__` inspected directly in `.venv/`
- Python stdlib docs — `tempfile.mkstemp`, `os.replace` (Windows atomic rename behavior)
- GitHub REST API docs — [Rate limits for the REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api) — headers verified: `x-ratelimit-remaining`, `x-ratelimit-reset`, `retry-after`, status codes 403 and 429
- Local Windows 11 / Python 3.14 verification — `os.replace` atomic write pattern tested end-to-end

### Secondary (MEDIUM confidence)

- [PyGithub issue #3080](https://github.com/PyGithub/PyGithub/issues/3080) — confirmed default `GithubRetry(total=10)` behavior and `retry=None` workaround
- [PyGithub issue #1319](https://github.com/PyGithub/PyGithub/issues/1319) — rate limit handling discussion, header access patterns

### Tertiary (LOW confidence)

None — all critical claims verified against PyGithub source or official GitHub docs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries inspected from installed `.venv/`; no new dependencies
- Architecture: HIGH — patterns verified against source inspection and local tests; atomic write confirmed on Windows
- Pitfalls: HIGH — Windows `os.rename` vs `os.replace` behavior confirmed; GithubRetry silent-sleep behavior confirmed from source

**Research date:** 2026-04-04
**Valid until:** 2026-07-04 (PyGithub API is stable; retry behavior tied to version 2.8.1 already pinned)
