# Phase 3: Extraction Resilience & Cache - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-04
**Phase:** 03-extraction-resilience-cache
**Areas discussed:** Cache freshness policy, Rate-limit backoff, Resume behavior, Error reporting

---

## Cache Freshness Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Skip entirely | If pr-{number}.json exists, skip that PR completely — no API calls. Fastest, simplest. New comments missed until manually cleared. | |
| Merge new comments | Re-fetch the PR, compare comment IDs, append only new comments to existing cache file. Catches new review comments but costs API calls. | ✓ |
| Skip with TTL | Skip cached PRs unless cache file is older than a threshold (e.g., 7 days). Balances freshness with API cost. | |

**User's choice:** Merge new comments
**Notes:** None

### Follow-up: Merge scope

| Option | Description | Selected |
|--------|-------------|----------|
| Only updated PRs | Use since/until date filters — only re-check PRs whose updated_at falls in the window. Closed PRs outside window left alone. | ✓ |
| All cached PRs | Every cached PR gets re-checked for new comments on every run. Thorough but expensive. | |
| You decide | Claude picks based on existing extractor architecture. | |

**User's choice:** Only updated PRs (Recommended)
**Notes:** None

---

## Rate-Limit Backoff

| Option | Description | Selected |
|--------|-------------|----------|
| Exponential backoff | Custom retry wrapper: start ~1s, double each retry, cap ~60s, max 5 retries. Handles both 429 and X-RateLimit-Remaining=0. | ✓ |
| Wait for reset | Read X-RateLimit-Reset header and sleep until that time. Simpler but can mean long waits (up to 60 min). | |
| You decide | Claude picks based on PyGithub's capabilities. | |

**User's choice:** Exponential backoff (Recommended)
**Notes:** None

### Follow-up: Retry exhaustion behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Save and exit | Write all successfully-cached PRs to disk, then raise error with clear message. User can resume later. | ✓ |
| Fail immediately | Raise exception on the spot. Already-written cache files preserved but no progress summary. | |
| You decide | Claude picks based on resume behavior decisions. | |

**User's choice:** Save and exit (Recommended)
**Notes:** None

---

## Resume Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| File-exists check | Check if pr-{number}.json exists before fetching. Exists → merge, missing → fetch fresh. No extra state file. | ✓ |
| Checkpoint file | Write .checkpoint file tracking last successfully-processed PR number. More precise but adds state management. | |
| You decide | Claude picks based on merge + backoff decisions. | |

**User's choice:** File-exists check (Recommended)
**Notes:** None

### Follow-up: Partial cache files

| Option | Description | Selected |
|--------|-------------|----------|
| Atomic write | Write to temp file first, then rename. If interrupted, no partial file — next run re-fetches cleanly. | ✓ |
| Accept partial files | Write directly to pr-{number}.json. If interrupted, merge logic handles it on next run via comment ID check. | |
| You decide | Claude picks the safer approach. | |

**User's choice:** Atomic write (Recommended)
**Notes:** None

---

## Error Reporting

| Option | Description | Selected |
|--------|-------------|----------|
| Python logging | Use stdlib logging — INFO for per-PR progress, WARNING for retries, ERROR for failures. CLI controls verbosity in Phase 6. | ✓ |
| Quiet with summary | No per-PR output. Single summary at end. Clean for automation. | |
| You decide | Claude picks for best Phase 6/7 integration. | |

**User's choice:** Python logging (Recommended)
**Notes:** None

### Follow-up: Exit message on rate-limit exhaustion

| Option | Description | Selected |
|--------|-------------|----------|
| Progress + resume hint | "Extracted 12/45 PRs before rate limit exhaustion. Re-run the same command to resume." | ✓ |
| Just the error | "GitHub API rate limit exceeded after 5 retries." Standard error, no extra context. | |
| You decide | Claude picks most helpful format. | |

**User's choice:** Progress + resume hint (Recommended)
**Notes:** None

---

## Claude's Discretion

- Exponential backoff implementation details (jitter, exact timing constants)
- Whether to use PyGithub's built-in rate-limit awareness as complement
- Logging format and logger naming
- Temp file naming scheme for atomic writes

## Deferred Ideas

None — discussion stayed within phase scope
