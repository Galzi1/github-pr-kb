---
phase: 02-github-extraction-core
verified: 2026-04-03T00:00:00Z
status: passed
score: 14/14 must-haves verified
re_verification: false
---

# Phase 02: GitHub Extraction Core — Verification Report

**Phase Goal:** A user can authenticate to GitHub and fetch PR comments from a repository, filtered by state and date range, with results written to local storage.
**Verified:** 2026-04-03
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth                                                                                                      | Status     | Evidence                                                                 |
|----|------------------------------------------------------------------------------------------------------------|------------|--------------------------------------------------------------------------|
| 1  | User can authenticate to GitHub with a PAT and fetch PR comments from a repository                         | VERIFIED   | `GitHubExtractor.__init__` uses `Auth.Token(settings.github_token)` and `client.get_repo()`; `test_extract_pr_comments` passes |
| 2  | Review comments (inline on code) and issue comments (PR thread) are both extracted                          | VERIFIED   | `extract()` calls both `pr.get_review_comments()` and `pr.get_issue_comments()`; `test_extract_pr_comments` asserts 3 comments from 2 review + 1 issue |
| 3  | Bot comments from known CI accounts (dependabot, codecov, etc.) are filtered out                           | VERIFIED   | `SKIP_BOT_LOGINS` frozenset defined; `is_noise()` returns True for matching logins; `test_noise_filter_skips_dependabot` passes |
| 4  | Comments from code review agents (Copilot, CodeRabbit) with substantive text are preserved                 | VERIFIED   | `is_noise()` only uses login-based filter for known CI bots — `github-copilot[bot]` is not in `SKIP_BOT_LOGINS`; `test_review_bot_kept` passes |
| 5  | Single-word and emoji-only comments are filtered out                                                        | VERIFIED   | `_SUBSTANTIVE_RE = re.compile(r"[a-zA-Z]{5,}")` gates on 5+ char word; `test_noise_filter_skips_emoji_only` asserts 0 comments for "👍" and "LGTM" |
| 6  | User can filter by PR state (open/closed/all)                                                               | VERIFIED   | `extract(state=...)` passes state to `get_pulls(state=state, ...)`; `test_state_filter` asserts `get_pulls` called with `state="closed"` |
| 7  | User can filter by date range using PR updated_at with early-stop on sorted results                         | VERIFIED   | `sort="updated", direction="desc"` on `get_pulls`; `break` on `since` boundary; `continue` on `until` boundary; `test_date_early_stop` and `test_upper_date_bound` pass |
| 8  | Each PR's data is written to a separate JSON file in .github-pr-kb/cache/pr-N.json                         | VERIFIED   | `cache_path = self.cache_dir / f"pr-{pr.number}.json"` written via `json.dumps(pr_file.model_dump(mode="json"), ...)`; `test_cache_write` passes |
| 9  | PRs with zero comments after filtering still produce a cache file                                           | VERIFIED   | No early-exit on empty `comments` list; `test_noise_filter_skips_dependabot` writes pr-10.json with 0 comments |
| 10 | .github-pr-kb/ directory is gitignored                                                                     | VERIFIED   | `.gitignore` line 214: `.github-pr-kb/` |
| 11 | PRRecord model validates and serializes PR metadata (number, title, body, state as Literal, url)            | VERIFIED   | `models.py` defines `PRRecord(BaseModel)` with `state: Literal["open", "closed"]`; 4 PRRecord tests pass |
| 12 | CommentRecord model captures review and issue comment data with Literal comment_type and optional diff context | VERIFIED | `CommentRecord` has `comment_type: Literal["review", "issue"]`, `file_path: Optional[str]`, `diff_hunk: Optional[str]`; 5 CommentRecord tests pass |
| 13 | PRFile envelope model round-trips through JSON without data loss                                            | VERIFIED   | `test_prfile_roundtrip_through_json` and `test_prfile_extracted_at_serializes_as_iso8601` pass |
| 14 | Reaction counts stored as dict with only non-zero keys                                                      | VERIFIED   | `_extract_reactions()` filters `{k: v for k in REACTION_KEYS if v > 0}`; `test_reactions_extracted` asserts "+1"==2, "heart"==1, "-1" absent |

**Score:** 14/14 truths verified

---

### Required Artifacts

| Artifact                           | Expected                                                       | Status   | Details                                           |
|------------------------------------|----------------------------------------------------------------|----------|---------------------------------------------------|
| `src/github_pr_kb/models.py`       | PRRecord, CommentRecord, PRFile pydantic models                | VERIFIED | 38 lines; exports all 3 classes; 100% test coverage |
| `tests/test_models.py`             | Unit tests for model validation and JSON round-trip (min 50 lines) | VERIFIED | 227 lines; 11 test functions                  |
| `src/github_pr_kb/extractor.py`    | GitHubExtractor class, is_noise, SKIP_BOT_LOGINS (min 80 lines) | VERIFIED | 153 lines; all 3 exports present; 96% coverage   |
| `tests/test_extractor.py`          | Extractor unit tests with mocked PyGithub (min 100 lines)      | VERIFIED | 335 lines; 12 test functions                      |
| `tests/conftest.py`                | Session-scoped autouse fixture setting GITHUB_TOKEN            | VERIFIED | Also sets env var at module level (more robust)   |
| `.gitignore`                       | Contains `.github-pr-kb/` entry                                | VERIFIED | Line 214: `.github-pr-kb/`                        |

---

### Key Link Verification

| From                              | To                            | Via                              | Status   | Details                                              |
|-----------------------------------|-------------------------------|----------------------------------|----------|------------------------------------------------------|
| `src/github_pr_kb/models.py`      | `pydantic.BaseModel`          | class inheritance                | VERIFIED | `class PRRecord(BaseModel)` (line 22)                |
| `tests/test_models.py`            | `src/github_pr_kb/models.py`  | import                           | VERIFIED | `from github_pr_kb.models import PRRecord, CommentRecord, PRFile` (line 8) |
| `src/github_pr_kb/extractor.py`   | `src/github_pr_kb/models.py`  | import PRRecord, CommentRecord, PRFile | VERIFIED | `from github_pr_kb.models import CommentRecord, PRFile, PRRecord` (line 11) |
| `src/github_pr_kb/extractor.py`   | `src/github_pr_kb/config.py`  | import settings for github_token | VERIFIED | `from github_pr_kb.config import settings` (line 10) |
| `src/github_pr_kb/extractor.py`   | `github.Github`               | Auth.Token authentication        | VERIFIED | `Github(auth=Auth.Token(settings.github_token))` (line 61) |
| `src/github_pr_kb/extractor.py`   | `.github-pr-kb/cache/`        | pathlib.Path file writes         | VERIFIED | `f"pr-{pr.number}.json"` filename pattern (line 146) |
| `tests/test_extractor.py`         | `src/github_pr_kb/extractor.py` | import                         | VERIFIED | `from github_pr_kb.extractor import SKIP_BOT_LOGINS, GitHubExtractor, is_noise` (line 9) |

---

### Data-Flow Trace (Level 4)

The extractor does not render UI — it writes JSON files. Data flow verified structurally:

| Artifact                        | Data Variable    | Source                                          | Produces Real Data | Status   |
|---------------------------------|------------------|-------------------------------------------------|--------------------|----------|
| `extractor.py` / `extract()`    | `comments`       | `pr.get_review_comments()` + `pr.get_issue_comments()` | Yes — populated from PyGithub iterables | FLOWING |
| `extractor.py` / `extract()`    | `pr_file`        | `PRFile(pr=pr_record, comments=comments, ...)`  | Yes — composed from API objects | FLOWING |
| `extractor.py` / cache write    | `cache_path`     | `json.dumps(pr_file.model_dump(mode="json"))` written to `pr-N.json` | Yes — real file write | FLOWING |

---

### Behavioral Spot-Checks

| Behavior                                      | Command                                                       | Result        | Status  |
|-----------------------------------------------|---------------------------------------------------------------|---------------|---------|
| All 26 tests pass                             | `.venv/Scripts/python.exe -m pytest tests/ -q`               | 26 passed     | PASS    |
| models.py imports succeed (with token set)    | `GITHUB_TOKEN=ghp_test python -c "from github_pr_kb.models import PRRecord, CommentRecord, PRFile"` | models OK | PASS |
| extractor.py imports succeed (with token set) | `GITHUB_TOKEN=ghp_test python -c "from github_pr_kb.extractor import GitHubExtractor, is_noise, SKIP_BOT_LOGINS"` | extractor OK | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description                                                                 | Status    | Evidence                                                                 |
|-------------|-------------|-----------------------------------------------------------------------------|-----------|--------------------------------------------------------------------------|
| CORE-01     | 02-01, 02-02 | User can extract all PR comments from a GitHub repository using a PAT     | SATISFIED | `GitHubExtractor.extract()` authenticates via `Auth.Token`, iterates PRs, collects review + issue comments; 12 extractor tests pass |
| CORE-02     | 02-02        | User can filter extraction by PR state (open/closed/all) and optional date range | SATISFIED | `extract(state=, since=, until=)` parameters wired to `get_pulls(state=, sort="updated", direction="desc")` with early-stop on `since`; `test_state_filter`, `test_date_early_stop`, `test_upper_date_bound`, `test_date_filter_uses_updated_at` all pass |

**Note on REQUIREMENTS.md traceability table:** CORE-02 is listed as "Pending" in the traceability table at the bottom of REQUIREMENTS.md, but the implementation is complete. This is a stale status in the tracking document — the code satisfies the requirement. No implementation gap exists.

**Orphaned requirements check:** No additional Phase 2 requirements found in REQUIREMENTS.md beyond CORE-01 and CORE-02.

---

### Anti-Patterns Found

No blockers or warnings found.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `extractor.py` | 52 | Uncovered branch: `return {}` in `_extract_reactions` when reactions is falsy | Info | Branch executes when `raw_reactions` is None/empty; tests pass non-empty dicts — minor coverage gap only |
| `extractor.py` | 102 | Uncovered branch: `continue` in review comment noise filter | Info | The `continue` path executes when a review comment passes `is_noise()`; noise filter tests use issue comments — minor coverage gap only |

Both uncovered lines are guard/shortcut branches, not hollow implementations. No stub patterns, placeholder returns, or hardcoded empty data found in production code.

---

### Human Verification Required

None. All phase behaviors are fully verifiable programmatically. The test suite mocks PyGithub end-to-end, eliminating the need for a live GitHub token during verification.

---

### Gaps Summary

No gaps. All 14 must-have truths are verified. All artifacts exist, are substantive, and are correctly wired. Both required requirements (CORE-01, CORE-02) are fully satisfied by the implementation. The full test suite (26 tests across test_config, test_models, test_extractor) passes with 96% coverage on extractor.py.

---

_Verified: 2026-04-03_
_Verifier: Claude (gsd-verifier)_
