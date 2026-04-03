---
created: 2026-04-03T20:55:33.389Z
title: Add integration test suite for GitHub extraction
area: testing
files:
  - src/github_pr_kb/extractor.py
  - tests/test_extractor.py
---

## Problem

All existing extractor tests are unit tests using mocked PyGithub objects. There is no integration test that runs against the real GitHub API to verify the full extraction pipeline end-to-end. This means regressions in auth, pagination, or API shape changes would not be caught until runtime.

## Solution

Add a `tests/test_extractor_integration.py` suite that calls `GitHubExtractor("Galzi1/github-pr-kb")` with a real PAT and asserts on known values from PR #2 ("Phase 02: GitHub Extraction Core").

**Known expected values from PR #2** (Galzi1/github-pr-kb#2):

- PR number: `2`
- PR title: `"Phase 02: GitHub Extraction Core"`
- PR state: `"closed"`
- PR URL: `"https://github.com/Galzi1/github-pr-kb/pull/2"`
- Known review comments left by `Galzi1`:
  - "Missing type hinting for `raw_reactions`" (id: 3034151684)
  - "This code repeats itself both here and for review comments above." (id: 3034154036)
  - "The code that processes each `pr` is very long and should probably be split into a separate function" (id: 3034158911)
  - "I think it could be useful to encapsulate this logic in a function, to allow easier modifications/refactorings if needed." (id: 3034166484)
  - "I think that this line is too hard to read and understand." (id: 3034175576)
  - "You are using `Any` too much for type hinting..." (id: 3034250523)
- Known qodo-code-review bot comments should be filtered (bot login: `qodo-code-review[bot]` — not in SKIP_BOT_LOGINS, but substantive content check may vary)

**Test structure:**
- Mark tests with `@pytest.mark.integration` and skip when `GITHUB_TOKEN` is a dummy/test value
- Use `extract(state="closed")` and filter to PR #2 specifically
- Assert: PR title, state, at least one known comment author (`Galzi1`), comment_type fields are `"review"` or `"issue"`
- Assert: dependabot/codecov comments (if any) are not present
- Assert: `reactions` field is a `dict[str, int]`

**Guard:** Skip integration tests in CI unless `RUN_INTEGRATION_TESTS=1` env var is set.
