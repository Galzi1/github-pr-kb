# Phase 2: GitHub Extraction Core - Context

**Gathered:** 2026-04-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Authenticate to GitHub via PAT and fetch PR comments (review comments + issue comments) from a single repository, filtered by PR state and date range, writing results to per-PR JSON files in `.github-pr-kb/cache/`. No rate-limit handling, no caching/idempotency (Phase 3), no classification (Phase 4).

Requirements: CORE-01, CORE-02

</domain>

<decisions>
## Implementation Decisions

### Storage Format
- **D-01:** Per-PR JSON files in `.github-pr-kb/cache/` directory (e.g., `.github-pr-kb/cache/pr-42.json`)
- **D-02:** Each file contains one PR's metadata + all its extracted comments
- **D-03:** No single monolithic JSON file — avoids bloat and redundancy as the cache grows
- **D-04:** `.github-pr-kb/` is the tool's working directory at project root (gitignored); `cache/` subdirectory holds extraction data

### Data Model Shape
- **D-05:** PR model (lean + description): number, title, description/body, state, URL
- **D-06:** Comment model (rich): comment ID, author login, body text, created_at timestamp, URL, file path + diff hunk (for review comments), reaction counts
- **D-07:** Diff context fields (file path, diff hunk) are populated for review comments, null/empty for issue comments
- **D-08:** Reaction counts stored as a simple dict (e.g., `{"thumbs_up": 3, "heart": 1}`) — may signal comment importance to classifier

### Extraction Scope
- **D-09:** Extract two comment types: review comments (inline on code) and issue comments (PR thread). These are the two highest-signal sources.
- **D-10:** Do NOT extract: review summaries (often empty/"LGTM"), PR body as a classifiable comment (stored as PR metadata only)
- **D-11:** Pre-filter obvious noise: skip generic bot comments (CI bots, dependabot, codecov, auto-labelers), skip single-word/emoji-only replies
- **D-12:** Preserve comments from code review agents (Copilot reviewer, CodeRabbit, etc.) — these contain real code insights. Heuristic: skip known automation bot accounts, keep anything with substantive text content regardless of bot/human authorship.

### Filter Behavior
- **D-13:** Date range filters on PR `updated_at` — catches PRs with recent activity even if created long ago
- **D-14:** API-level filtering via PyGithub's `get_pulls(state=X, sort='updated', direction='desc')`, stopping when past the date boundary — fewer API calls, faster
- **D-15:** State filter supports: open, closed, all (maps directly to PyGithub's state parameter)

### Claude's Discretion
- Exact JSON schema field names and nesting (as long as the fields above are present)
- Whether to use pydantic models for serialization/deserialization or plain dicts
- How to handle edge cases: PRs with zero comments, deleted comments, very long comment bodies
- Whether to add `pytest-mock` to dev deps in this phase or use `unittest.mock`
- The specific list of bot accounts to pre-filter (can start with common ones and be extended)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Foundation
- `.planning/phases/01-project-foundation/01-CONTEXT.md` — Phase 1 decisions: src-layout, pydantic-settings config, module-level Settings validation
- `.planning/phases/01-project-foundation/01-01-SUMMARY.md` — Phase 1 implementation details: what was built, patterns established
- `src/github_pr_kb/config.py` — Settings class with GITHUB_TOKEN validation; Phase 2 imports `settings` from here

### Requirements
- `.planning/REQUIREMENTS.md` — CORE-01 (extract all PR comments with PAT), CORE-02 (filter by state/date range)

### Stub Files to Implement
- `src/github_pr_kb/extractor.py` — Stub from Phase 1, to be filled with extraction logic
- `src/github_pr_kb/models.py` — Stub from Phase 1, to be filled with PR/Comment data models

No external specs — requirements fully captured in decisions above.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config.py`: `Settings` class with `github_token: str` — extractor authenticates via `settings.github_token`
- PyGithub >= 2.5.0 already in `pyproject.toml` dependencies

### Established Patterns
- Module-level `settings = Settings()` for fail-fast config validation
- src-layout: all code in `src/github_pr_kb/`
- Stub modules contain only docstrings — Phase 2 replaces stub content entirely

### Integration Points
- `extractor.py` imports `settings` from `config.py` for GitHub authentication
- `models.py` defines data classes used by extractor (Phase 2), classifier (Phase 4), and generator (Phase 5)
- Per-PR JSON files in `.github-pr-kb/cache/` are the input for Phase 3 (caching/idempotency) and Phase 4 (classification)
- `pytest-mock` (or unittest.mock) needed for mocking PyGithub API calls in tests

</code_context>

<specifics>
## Specific Ideas

- Bot filtering should distinguish between generic CI bots (skip) and code review agents like Copilot/CodeRabbit (keep) — the heuristic is substantive text content, not just bot vs human authorship
- PR description is stored as PR metadata but NOT fed to the classifier as a standalone "comment" — it provides context, not classifiable content
- Reactions stored as a simple count dict — lightweight signal for downstream phases to use optionally

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-github-extraction-core*
*Context gathered: 2026-04-02*
