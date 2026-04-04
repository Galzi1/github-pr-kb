# Phase 3: Extraction Resilience & Cache - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Make extraction survive GitHub rate limits and interrupted runs. Already-cached comments are never re-fetched, but PRs within the active date window get new comments merged into their cache files. PR + comment ID is the immutable dedup key.

</domain>

<decisions>
## Implementation Decisions

### Cache Freshness Policy
- **D-01:** On re-run, merge new comments into existing cache files — do not skip cached PRs entirely. Compare comment IDs; append only those not already present.
- **D-02:** Merging applies only to PRs whose `updated_at` falls within the active `since`/`until` date filter window. PRs outside the window keep their existing cache untouched.

### Rate-Limit Backoff
- **D-03:** Use exponential backoff for GitHub 429 responses and `X-RateLimit-Remaining=0`: start at ~1s, double per retry, cap at ~60s, max 5 retries.
- **D-04:** On retry exhaustion, save all successfully-cached PRs to disk, then raise an error with a clear progress + resume message (not a raw traceback).

### Resume Behavior
- **D-05:** Use file-exists check to determine resume state — if `pr-{number}.json` exists, merge new comments; if missing, fetch fresh. No separate checkpoint file.
- **D-06:** Use atomic writes (write to temp file, then rename to `pr-{number}.json`) to prevent partial/corrupt cache files on interruption.

### Error Reporting
- **D-07:** Use Python stdlib `logging` module — INFO for per-PR progress ("PR #42: 3 new comments merged"), WARNING for retries ("Rate limited, retrying in 4s"), ERROR for failures.
- **D-08:** On rate-limit exit, message includes progress count and resume hint: "Extracted 12/45 PRs before rate limit exhaustion. Re-run the same command to resume."

### Claude's Discretion
- Exponential backoff implementation details (jitter, exact timing constants)
- Whether to use PyGithub's built-in rate-limit awareness as a complement to the custom retry wrapper
- Logging format and logger naming conventions
- Temp file naming scheme for atomic writes

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Specs
- `.planning/REQUIREMENTS.md` — CORE-03 (rate limits), CORE-04 (local cache), CORE-05 (idempotency)
- `.planning/ROADMAP.md` — Phase 3 success criteria and planning notes

### Existing Implementation
- `src/github_pr_kb/extractor.py` — Current `GitHubExtractor` class, `_write_cache`, `extract()` method
- `src/github_pr_kb/models.py` — `PRFile`, `PRRecord`, `CommentRecord` Pydantic models with `ConfigDict(extra="ignore")`
- `src/github_pr_kb/config.py` — `Settings` with `github_token`, module-level instantiation

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GitHubExtractor` class (`extractor.py`): Already handles auth, PR iteration with date filters, comment collection, and per-PR JSON write. Phase 3 extends this with retry + merge logic.
- `_comment_to_record()`: Converts PyGithub comment objects to `CommentRecord` — reuse for merge path.
- `is_noise()` filter: Already filters bots and low-substance comments — applies to newly-merged comments too.
- Pydantic models with `extra="ignore"`: Forward-compatible — adding fields to cache files won't break deserialization.

### Established Patterns
- Per-PR JSON files at `.github-pr-kb/cache/pr-{number}.json`
- `model_dump(mode="json")` for serialization, enabling `json.dumps` with `indent=2`
- Date filter logic: `since` for early-stop (descending order), `until` for skip-but-continue
- Module-level `settings = Settings()` for config — fail-fast on missing env vars

### Integration Points
- `extract()` method is the entry point — retry wrapper wraps the PyGithub API calls inside it
- `_write_cache()` needs atomic write upgrade (temp file + rename)
- New merge logic sits between "fetch comments" and "write cache" — read existing file, diff comment IDs, append new ones
- Logging integrates at the `GitHubExtractor` class level (class-level logger)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-extraction-resilience-cache*
*Context gathered: 2026-04-04*
