# Plan Risk Review: 03-01 — Extraction Resilience & Cache

## 1. Plan Summary

**Purpose:** Add three interlocking resilience capabilities to `GitHubExtractor`: (1) rate-limit backoff via `GithubRetry(total=5)`, (2) atomic cache writes via `mkstemp` + `os.replace`, and (3) merge-based re-runs that deduplicate comments by `comment_id`.

**Key components touched:**
- `src/github_pr_kb/extractor.py` — 3 new methods (`_write_cache_atomic`, `_merge_or_write`, `RateLimitExhaustedError`), modifications to `__init__` and `extract()`, removal of `_write_cache`
- `tests/test_extractor.py` — 8 new test functions
- External dependencies: PyGithub's `GithubRetry`, `requests.exceptions.RetryError`, stdlib `tempfile`, `os`, `contextlib`, `logging`

**Stated assumptions:**
- `GithubRetry(total=5)` raises `requests.exceptions.RetryError` after exhaustion
- `os.replace` is atomic on Windows when source and target are on the same volume
- `comment_id` is a stable, unique identifier for deduplication

**Theory of success:** After this change, extraction survives rate limits (caches partial progress, raises a clear error with resume hint), re-runs merge new comments without duplicates, and interrupted writes leave no corrupt files.

---

## 2. Assumptions & Evidence

### A1: `GithubRetry(total=5)` propagates `RetryError` after 5 retries
- **Type:** Explicit, foundational
- **Evidence:** Research doc states this was verified by inspecting PyGithub 2.8.1 source locally. HIGH confidence.
- **If wrong:** The core rate-limit handling path breaks — `extract()` would never catch the error, and the process would either hang or crash with an unexpected exception type.
- **Testable?** Yes (secret) — mock-based unit test covers this. Could also be verified with an integration test against a rate-limited endpoint.
- **Verdict:** Well-justified.

### A2: `RetryError` is ONLY raised for rate limits
- **Type:** Implicit, structural
- **Evidence:** Research doc Pitfall 5 explicitly calls this out — `RetryError` can also be raised for network errors, connection timeouts, etc. The plan's `except RetryError` catch will label ALL such errors as "rate limit exhaustion."
- **If wrong:** User sees "rate limit exhaustion" message when the real problem is a DNS failure or network timeout. Misleading but not data-destructive — cached PRs are still flushed.
- **Testable?** Yes (secret) — inspect `exc.__cause__` for rate-limit indicators.
- **Verdict:** **Known issue, accepted in the plan.** The research doc recommends keeping the message "generic enough to cover both." The plan's message says "Re-run the same command to resume" which is reasonable advice regardless of cause. Low severity.

### A3: `os.replace` is atomic on Windows with same-volume temp files
- **Type:** Explicit, foundational
- **Evidence:** Research doc states this was verified locally on Windows 11 / Python 3.14. Python docs confirm `os.replace` uses `MOVEFILE_REPLACE_EXISTING`. Passing `dir=cache_path.parent` to `mkstemp` ensures same volume.
- **If wrong:** Cache corruption is possible on interrupted writes — the whole point of this change is defeated.
- **Verdict:** Well-justified. `os.replace` atomicity on NTFS is well-established.

### A4: `comment_id` is stable and globally unique within a repo
- **Type:** Implicit, foundational
- **Evidence:** Research doc states "GitHub comment IDs are immutable and globally unique per repo." This is correct per GitHub API docs — comment IDs are monotonically increasing integers assigned by GitHub.
- **If wrong:** Deduplication breaks — comments could be missed or duplicated.
- **Verdict:** Well-justified. This is a core GitHub API guarantee.

### A5: Existing 12 tests are unaffected by the changes
- **Type:** Explicit, structural
- **Evidence:** The plan modifies `_write_cache` ÔåÆ `_write_cache_atomic` and changes `extract()` internals. Existing tests mock at the `Github` constructor level and test via the public `extract()` API.
- **If wrong:** Regression — existing tests break.
- **Concern:** The existing tests call `extractor.extract()` which internally calls `self._write_cache()`. After the change, `_write_cache` is removed and replaced by `_merge_or_write` ÔåÆ `_write_cache_atomic`. Since tests mock the `Github` class (not `_write_cache`), they should pass — they exercise the public API, not internal method names. However, the new `GithubRetry` import in `__init__` changes the `Github()` constructor call signature. Tests patch `github_pr_kb.extractor.Github`, so the mock will absorb the new `retry=` kwarg silently. **This is fine.**
- **Verdict:** Sound reasoning. Low risk.

### A6: `_collect_comments` can raise `RetryError` mid-iteration
- **Type:** Implicit, structural
- **Evidence:** `_collect_comments` calls `pr.get_review_comments()` and `pr.get_issue_comments()`, which are lazy paginated API calls. `GithubRetry` retries on each page request. If a page triggers rate limiting after 5 retries, `RetryError` propagates up through `_collect_comments` to the `for pr in pulls` loop's try/except.
- **If wrong:** If `RetryError` is raised *inside* `_merge_or_write` (after partial comment collection but before atomic write), the PR's cache might not be updated. But this is actually fine — the atomic write hasn't happened yet, so the existing cache (if any) is untouched, and the PR will be re-fetched on resume.
- **Verdict:** Sound. The try/except around the `for pr in pulls` loop correctly catches `RetryError` from any API call within the loop body.

### A7: The plan assumes `RetryError` will be raised during PR iteration, not during `repo.get_pulls()`
- **Type:** Implicit, peripheral
- **Evidence:** `self.repo.get_pulls()` returns a `PaginatedList` which is lazy — the first page is fetched on first iteration. If rate limiting hits on the very first API call, `RetryError` could be raised when entering the `for pr in pulls:` loop, which IS inside the try/except. So this works.
- **Verdict:** No issue — the try/except covers this case.

---

## 3. Ipcha Mistabra — Devil's Advocacy

### 3a. Inversions

**Claim: "Merge-based re-runs are safer than overwrite-based re-runs."**

*Inversion:* Merge-based re-runs introduce a subtle data integrity risk that overwrite doesn't have. If a comment is edited on GitHub between runs, the merge path preserves the *old* version (because `comment_id` already exists in the set). Overwrite would capture the updated body. The plan's dedup-by-ID approach silently keeps stale comment bodies. For a "knowledge base" application, stale data could be worse than duplicate data — at least duplicates are visible.

**Assessment:** This is a genuine trade-off, but the plan's approach is correct for the stated requirements. CORE-05 says "re-running does not duplicate cached data" — the requirement prioritizes no-duplication over freshness. A future enhancement could compare `updated_at` timestamps per comment, but that's out of scope. **Low severity, noted for future.**

**Claim: "Atomic writes prevent all cache corruption."**

*Inversion:* Atomic writes prevent corruption from *interrupted writes*. They do NOT prevent corruption from other sources: disk full (temp file created but `os.replace` fails?), filesystem bugs, or concurrent processes writing to the same cache directory. The plan has no file locking — if two `extract()` calls run simultaneously on the same repo, they could both read the same cache file, both compute merges independently, and the last `os.replace` wins (losing the other's additions).

**Assessment:** Concurrent extraction is not a stated use case, and the tool appears to be a single-user CLI. **Low probability, but worth documenting as a known limitation.**

### 3b. The Little Boy from Copenhagen

**A new engineer joining next month:** The plan is well-structured. One thing that might confuse a newcomer: `_merge_or_write` is called for ALL PRs, not just previously-cached ones. The name suggests "merge or write" but it always writes — the "or" refers to whether it merges with existing data or writes fresh. The naming is adequate but could be clearer.

**An SRE on-call at 3 AM:** The `RateLimitExhaustedError` message includes "Re-run the same command to resume" — this is helpful. However, there's no indication of *which* PRs were processed or which PR triggered the failure. The `processed` count is included but not the total or the failing PR number. On a large repo, knowing "Extracted 12 PRs" is less useful than "Extracted 12/450 PRs, failed on PR #347."

**Assessment:** The plan includes `processed` in the message but the D-08 requirement says "Extracted 12/45 PRs" — with a total. The plan's implementation says `f"Extracted {processed} PRs before rate limit exhaustion."` without a total denominator. This is because `get_pulls()` returns a `PaginatedList` whose `totalCount` requires an additional API call, and we might be rate-limited. **The plan correctly avoids this — you can't fetch `totalCount` when you're already rate-limited.** The message is slightly less informative than D-08's ideal but is the pragmatic choice.

### 3c. Failure of Imagination

**Scenario: `json.JSONDecodeError` vs `ValidationError` in corrupt cache handling.**
The plan's Task 2 says `_merge_or_write` catches `ValidationError` for corrupt files. But what about `json.JSONDecodeError`? If the file contains `"{corrupt"`, `json.loads()` will raise `json.JSONDecodeError`, not `ValidationError`. The plan's action section mentions both (`ValidationError` or `json.JSONDecodeError`), but the task description only mentions `ValidationError`. The implementation must catch both.

**Assessment:** The research doc Pattern 3 only catches `ValidationError` in the code sample, but the plan's Task 2 action section does say "On `ValidationError` or `json.JSONDecodeError`." **This is a discrepancy between the pattern example and the task spec. The task spec is correct; the executor must catch both.** If only `ValidationError` is caught, the `test_corrupt_cache_full_fetch` test will fail (it writes `"{corrupt"` which triggers `JSONDecodeError`).

**Scenario: What if `_collect_comments` partially succeeds?**
If `pr.get_review_comments()` returns 5 comments but `pr.get_issue_comments()` raises `RetryError` mid-page, the collected review comments are lost (never written). The PR will be re-fetched on resume, which will re-collect all comments. This is correct behavior but means some API calls are "wasted." Not a bug, just an efficiency observation.

---

## 4. Risk Register

| Risk ID | Category | Description | Trigger | Probability | Severity | Priority | Detection | Mitigation | Contingency | Assumption |
|---------|----------|-------------|---------|-------------|----------|----------|-----------|------------|-------------|------------|
| **R1** | Technical | `_merge_or_write` catches only `ValidationError` but not `json.JSONDecodeError`, causing crash on truly corrupt (non-JSON) cache files | Corrupt cache file from pre-Phase-3 interrupted write | Medium | Medium | **Medium** | `test_corrupt_cache_full_fetch` fails in RED phase if only `ValidationError` caught | Plan Task 2 action explicitly lists both exceptions — executor must follow the action spec, not just the research code sample | Remove corrupt file manually; re-run | A3 |
| **R2** | Operational | `RetryError` message says "rate limit" when actual cause is network failure | Network outage or DNS failure during extraction | Low | Low | **Low** | User reports confusing error message | Keep message generic: "GitHub API call failed after retries" | User investigates network; re-runs | A2 |
| **R3** | Technical | Edited comments retain stale body text after merge | Comment edited on GitHub between extraction runs | Medium | Low | **Low** | Compare cache file comment bodies with API output on manual inspection | Document as known limitation; future enhancement could check `updated_at` per comment | Manual cache deletion forces full re-fetch | — |
| **R4** | Operational | Concurrent `extract()` calls on same repo lose data (last writer wins) | Two terminals running extract simultaneously | Very Low | Medium | **Low** | Missing comments in cache after concurrent runs | Document as unsupported; single-user CLI | Re-run extraction | — |
| **R5** | Technical | `mkstemp` leaves `.tmp` orphan files if process is killed between `os.fdopen` and `os.replace` | `SIGKILL` or power loss during write | Very Low | Low | **Very Low** | `.tmp` files accumulate in cache dir | `test_atomic_write_no_partial_file` verifies cleanup on normal path; orphans are harmless (ignored by merge logic) | Manual cleanup or glob-delete `.tmp` files | A3 |

**Known Knowns:** R1 (test will catch it), R2 (documented in research), R3 (accepted trade-off)
**Known Unknowns:** R4 (concurrency not tested)
**Unknown Unknowns surfaced:** None of critical severity. The plan and research are unusually thorough for this scope.

---

## 5. Verdict & Recommendations

**Overall Risk Level: Low**

This is a well-researched, tightly-scoped plan with strong evidence backing its key assumptions. The research phase verified critical behaviors (GithubRetry, os.replace on Windows) by inspecting source code locally rather than relying on documentation alone.

### Top 3 Risks

1. **R1 — JSONDecodeError not caught in merge path.** This is the most likely implementation mistake. The plan's action spec is correct, but the research code sample omits `JSONDecodeError`. An executor following the sample rather than the spec would produce a bug. **Mitigation: the `test_corrupt_cache_full_fetch` test will catch this in the REDÔåÆGREEN cycle.**

2. **R3 — Stale comment bodies after merge.** Accepted trade-off per CORE-05, but worth a one-line comment in the code explaining the design choice.

3. **R2 — Misleading error message on network failure.** Low severity. The "re-run to resume" advice is valid regardless of cause.

### Recommended Actions

- **Before execution:** None required. The plan is ready to execute.
- **During execution:** Ensure the executor catches both `ValidationError` and `json.JSONDecodeError` in `_merge_or_write` (R1). The task spec says this correctly — just don't follow the research code sample verbatim.
- **After execution:** Verify `test_corrupt_cache_full_fetch` writes truly invalid JSON (not just invalid Pydantic data) to exercise the `JSONDecodeError` path.

### Open Questions

- None blocking. The research addressed the two open questions (GithubRetry logger surfacing, `total=5` semantics) adequately.

### What the Plan Does Well

- **TDD structure is correct.** RED phase writes tests that import not-yet-existing `RateLimitExhaustedError` — they'll fail at import time, confirming the RED state cleanly.
- **Research-backed patterns.** Every code pattern was verified against installed source, not just documentation. The Windows-specific `os.replace` vs `os.rename` distinction is handled correctly.
- **Pitfall documentation is excellent.** Five concrete pitfalls with "what goes wrong / why / how to avoid / warning signs" — this is the kind of research that prevents implementation mistakes.
- **Minimal change surface.** Only `extractor.py` changes; models and config are untouched. The plan correctly reuses existing `PRFile`/`CommentRecord` models for the merge path.
- **The `dir=cache_path.parent` detail in `mkstemp`** prevents the cross-volume `os.replace` failure on Windows — a subtle but critical detail that many plans miss.