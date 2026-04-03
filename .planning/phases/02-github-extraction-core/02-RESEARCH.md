# Phase 2: GitHub Extraction Core - Research

**Researched:** 2026-04-02
**Domain:** PyGithub 2.x API, Pydantic v2 models, file-based JSON caching
**Confidence:** HIGH

## Summary

Phase 2 implements the extraction layer: authenticate to GitHub via PAT, iterate over PRs in a repository, collect review comments and issue comments per PR, pre-filter noise, and write each PR's results to a per-PR JSON file under `.github-pr-kb/cache/`. The stack is entirely locked by previous decisions — PyGithub 2.8.1 (installed), pydantic 2.12.5 (installed), stdlib pathlib and json for cache I/O, and `unittest.mock` for tests (no new dependencies required).

The PyGithub 2.x API uses `Auth.Token` for PAT authentication rather than the old positional string argument. `repo.get_pulls()` returns a lazily-paginated `PaginatedList`, making early-stop on date boundary efficient — breaking out of iteration prevents unnecessary page fetches. Both `PullRequestComment` (review comments) and `IssueComment` have a `reactions` property that returns the raw dict from GitHub's API (keys: `+1`, `-1`, `laugh`, `hooray`, `confused`, `heart`, `rocket`, `eyes`, `total_count`).

Pydantic v2's `model_dump(mode='json')` serializes `datetime` fields to ISO 8601 strings, enabling clean JSON file writes without custom serializers. `model_validate_json()` handles round-trip deserialization correctly. `.github-pr-kb/` is NOT currently in `.gitignore` and must be added in this phase.

**Primary recommendation:** Use `Auth.Token` + `Github(auth=auth)` for authentication; iterate `repo.get_pulls(state=X, sort='updated', direction='desc')` with early-stop on `updated_at`; use pydantic v2 BaseModel for `PRRecord` and `CommentRecord`; write via `model_dump(mode='json')` into `pathlib.Path`-managed cache files; mock with `unittest.mock.MagicMock`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Storage Format**
- D-01: Per-PR JSON files in `.github-pr-kb/cache/` directory (e.g., `.github-pr-kb/cache/pr-42.json`)
- D-02: Each file contains one PR's metadata + all its extracted comments
- D-03: No single monolithic JSON file — avoids bloat and redundancy as the cache grows
- D-04: `.github-pr-kb/` is the tool's working directory at project root (gitignored); `cache/` subdirectory holds extraction data

**Data Model Shape**
- D-05: PR model (lean + description): number, title, description/body, state, URL
- D-06: Comment model (rich): comment ID, author login, body text, created_at timestamp, URL, file path + diff hunk (for review comments), reaction counts
- D-07: Diff context fields (file path, diff hunk) are populated for review comments, null/empty for issue comments
- D-08: Reaction counts stored as a simple dict (e.g., `{"thumbs_up": 3, "heart": 1}`) — may signal comment importance to classifier

**Extraction Scope**
- D-09: Extract two comment types: review comments (inline on code) and issue comments (PR thread). These are the two highest-signal sources.
- D-10: Do NOT extract: review summaries (often empty/"LGTM"), PR body as a classifiable comment (stored as PR metadata only)
- D-11: Pre-filter obvious noise: skip generic bot comments (CI bots, dependabot, codecov, auto-labelers), skip single-word/emoji-only replies
- D-12: Preserve comments from code review agents (Copilot reviewer, CodeRabbit, etc.) — heuristic: skip known automation bot accounts, keep anything with substantive text content regardless of bot/human authorship

**Filter Behavior**
- D-13: Date range filters on PR `updated_at` — catches PRs with recent activity even if created long ago
- D-14: API-level filtering via PyGithub's `get_pulls(state=X, sort='updated', direction='desc')`, stopping when past the date boundary — fewer API calls, faster
- D-15: State filter supports: open, closed, all (maps directly to PyGithub's state parameter)

### Claude's Discretion

- Exact JSON schema field names and nesting (as long as the fields above are present)
- Whether to use pydantic models for serialization/deserialization or plain dicts
- How to handle edge cases: PRs with zero comments, deleted comments, very long comment bodies
- Whether to add `pytest-mock` to dev deps in this phase or use `unittest.mock`
- The specific list of bot accounts to pre-filter (can start with common ones and be extended)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CORE-01 | User can extract all PR comments from a GitHub repository using a personal access token | PyGithub `Auth.Token` + `Github(auth=auth)` + `repo.get_pulls()` + `pr.get_review_comments()` + `pr.get_issue_comments()` — all verified against installed PyGithub 2.8.1 |
| CORE-02 | User can filter extraction by PR state (open/closed/all) and optional date range | `get_pulls(state=X, sort='updated', direction='desc')` supports state='all'; early-stop on `pr.updated_at < since` exploits lazy PaginatedList pagination — verified |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| PyGithub | 2.8.1 (installed) | GitHub REST API client | Already installed, locked decision, `Auth.Token` pattern for PAT |
| pydantic | 2.12.5 (installed) | Data models + JSON serialization | Already installed; `model_dump(mode='json')` handles datetime → ISO 8601 cleanly |
| pathlib | stdlib | Cache directory + file I/O | Portable path handling; `mkdir(parents=True, exist_ok=True)` for cache dir creation |
| json | stdlib | JSON file writes | `json.dumps` + pathlib write_text for cache files |
| unittest.mock | stdlib | Mocking PyGithub in tests | MagicMock correctly simulates PaginatedList iteration and PR/comment attributes |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| datetime | stdlib | Date range filtering | `timezone.utc`-aware comparisons against `pr.updated_at` |
| re | stdlib | Bot detection heuristic | Simple regex for single-word/emoji-only comment bodies |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `unittest.mock` | `pytest-mock` | pytest-mock adds convenience (`mocker` fixture) but adds a dependency; `unittest.mock` is sufficient for the PyGithub mock patterns needed here |
| plain dicts | pydantic BaseModel | Pydantic adds schema validation + clean serialization; plain dicts are simpler but lose type safety for downstream phases |

**Installation:**

No new dependencies required. All needed libraries are stdlib or already installed. If the team prefers `pytest-mock`, add it:

```bash
uv add --dev pytest-mock
```

**Version verification (confirmed against installed lock):**

- `PyGithub`: 2.8.1 (uv.lock, uploaded 2025-09-02)
- `pydantic`: 2.12.5 (uv.lock)
- `pydantic-settings`: 2.13.1 (uv.lock)

---

## Architecture Patterns

### Recommended Project Structure

```
src/github_pr_kb/
├── config.py        # Settings (Phase 1) — import settings from here
├── models.py        # PRRecord + CommentRecord pydantic models (Phase 2, NEW)
└── extractor.py     # GitHubExtractor class (Phase 2, NEW)

.github-pr-kb/       # Gitignored tool working directory (created at runtime)
└── cache/
    ├── pr-42.json
    └── pr-101.json

tests/
├── test_config.py   # Phase 1 tests (existing)
├── test_models.py   # PRRecord / CommentRecord unit tests (Phase 2, NEW)
└── test_extractor.py # Extractor unit tests with mocks (Phase 2, NEW)
```

### Pattern 1: PyGithub 2.x PAT Authentication

**What:** Use `Auth.Token` wrapper, not the deprecated positional string argument.
**When to use:** Always for PAT-based authentication in PyGithub >= 2.0.

```python
# Source: verified against PyGithub 2.8.1 Auth module
from github import Github, Auth

auth = Auth.Token(settings.github_token)
g = Github(auth=auth)
repo = g.get_repo("owner/repo")
```

### Pattern 2: Lazy Pagination with Early-Stop

**What:** `get_pulls()` returns a `PaginatedList` that fetches pages lazily on iteration. Breaking mid-iteration skips remaining page fetches.
**When to use:** Date-bounded extraction — stop once `updated_at` passes the lower bound.

```python
# Source: verified against PyGithub 2.8.1 PaginatedList.__iter__
from datetime import datetime, timezone

def get_prs(repo, state: str, since: datetime | None, until: datetime | None):
    for pr in repo.get_pulls(state=state, sort="updated", direction="desc"):
        if since and pr.updated_at < since:
            break  # Sorted desc by updated_at — nothing older will match
        if until and pr.updated_at > until:
            continue  # Skip PRs updated after upper bound
        yield pr
```

**Important:** `pr.updated_at` is timezone-aware (`datetime` with UTC tzinfo). Pass `since` and `until` as timezone-aware datetimes to avoid comparison errors.

### Pattern 3: Collecting Review + Issue Comments

**What:** Two separate method calls per PR. `get_review_comments()` returns inline code comments; `get_issue_comments()` returns PR thread comments.
**When to use:** Always — these are the two extraction targets per D-09.

```python
# Source: verified against PyGithub 2.8.1 PullRequest methods
review_comments = list(pr.get_review_comments())   # PullRequestComment objects
issue_comments  = list(pr.get_issue_comments())     # IssueComment objects
```

### Pattern 4: Reaction Count Extraction

**What:** `comment.reactions` returns the raw GitHub API dict (e.g., `{'+1': 3, 'heart': 1, 'total_count': 4, ...}`). Per D-08, store as a simple count dict.
**When to use:** For both review comments and issue comments.

```python
# Source: verified against PullRequestComment source — reactions is a raw dict property
REACTION_KEYS = ["+1", "-1", "laugh", "hooray", "confused", "heart", "rocket", "eyes"]

def extract_reactions(comment) -> dict[str, int]:
    raw = comment.reactions or {}
    return {k: raw.get(k, 0) for k in REACTION_KEYS if raw.get(k, 0) > 0}
    # Returns only non-zero keys to keep storage compact
```

### Pattern 5: Pydantic v2 JSON Serialization to File

**What:** `model_dump(mode='json')` serializes datetime fields as ISO 8601 strings. Wrap in a `PRFile` envelope containing PR metadata + comment list.
**When to use:** Writing per-PR cache files.

```python
# Source: verified against pydantic 2.12.5
import json
from pathlib import Path

cache_dir = Path(".github-pr-kb/cache")
cache_dir.mkdir(parents=True, exist_ok=True)

pr_file = PRFile(pr=pr_record, comments=comment_records)
path = cache_dir / f"pr-{pr_record.number}.json"
path.write_text(json.dumps(pr_file.model_dump(mode="json"), indent=2))
```

### Pattern 6: unittest.mock for PyGithub

**What:** `MagicMock()` creates PyGithub-compatible fake objects. Attributes can be set directly; `get_review_comments()` / `get_issue_comments()` return lists of mock comment objects.
**When to use:** All extractor tests — never make live GitHub API calls in tests.

```python
# Source: verified by running locally
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

def make_mock_pr(number=42, state="open", updated_at=None):
    pr = MagicMock()
    pr.number = number
    pr.title = "Test PR"
    pr.body = "PR description"
    pr.state = state
    pr.html_url = f"https://github.com/owner/repo/pull/{number}"
    pr.updated_at = updated_at or datetime(2024, 1, 15, tzinfo=timezone.utc)
    return pr

def make_mock_review_comment(comment_id=1001, login="alice"):
    c = MagicMock()
    c.id = comment_id
    c.user.login = login
    c.body = "This is a substantive review comment"
    c.created_at = datetime(2024, 1, 15, tzinfo=timezone.utc)
    c.html_url = "https://github.com/owner/repo/pull/42#discussion_r1001"
    c.path = "src/foo.py"
    c.diff_hunk = "@@ -1,3 +1,4 @@\n context\n+new line"
    c.reactions = {"+1": 2, "heart": 0, "total_count": 2}
    return c
```

### Anti-Patterns to Avoid

- **Positional PAT in Github():** `Github("my_token")` is deprecated in 2.x. Always use `Auth.Token`.
- **Timezone-naive datetime comparisons:** `pr.updated_at` is tz-aware. Compare with `datetime.now(timezone.utc)` not `datetime.now()`.
- **Storing PR body as a comment:** D-10 explicitly forbids this. Store in PR metadata only.
- **Calling `list()` on get_pulls() before filtering:** This fetches all pages before any early-stop can occur. Always iterate lazily with `for pr in repo.get_pulls(...)`.
- **Not handling `pr.body is None`:** PRs with no description return `None` for `body`. Model must use `Optional[str]`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GitHub REST pagination | Custom page-offset loop | PyGithub `PaginatedList` lazy iteration | Handles cursor tokens, per_page, retry on 429 |
| JSON datetime serialization | `str(dt)` or custom encoder | Pydantic `model_dump(mode='json')` | Produces standard ISO 8601; handles None; round-trips via `model_validate_json` |
| Directory creation with races | Manual `os.makedirs` with try/except | `pathlib.mkdir(parents=True, exist_ok=True)` | Atomic, cross-platform, readable |
| Mock object hierarchies | Nested dict/class fakes | `unittest.mock.MagicMock()` | Auto-creates attribute chains; works with `pr.user.login`-style access |

**Key insight:** PyGithub already wraps every edge case in the GitHub REST API (pagination, auth headers, retries). The only custom logic needed is the date early-stop and the bot-filter heuristic.

---

## Common Pitfalls

### Pitfall 1: Timezone-Naive Datetime Comparison

**What goes wrong:** `TypeError: can't compare offset-naive and offset-aware datetimes` at runtime.
**Why it happens:** `pr.updated_at` from PyGithub is tz-aware (UTC). User-supplied `since`/`until` may be parsed as tz-naive.
**How to avoid:** Always parse date inputs with `timezone.utc`. Example: `datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)`.
**Warning signs:** `AttributeError: tzinfo` or `TypeError` in date comparison logic during tests.

### Pitfall 2: `pr.body` is None

**What goes wrong:** `TypeError: argument of type 'NoneType' is not iterable` when accessing PR body.
**Why it happens:** PRs with no description have `body = None`.
**How to avoid:** Model field must be `Optional[str] = None`. Serialization automatically handles None.
**Warning signs:** Crash on first PR that has no description.

### Pitfall 3: `comment.user` Can Be None (Deleted Accounts)

**What goes wrong:** `AttributeError: 'NoneType' object has no attribute 'login'` on deleted GitHub accounts.
**Why it happens:** If a GitHub user deletes their account, `comment.user` is None rather than a NamedUser object.
**How to avoid:** Use `comment.user.login if comment.user else "[deleted]"` when extracting login.
**Warning signs:** Fails on any repo with deleted-account comments.

### Pitfall 4: `.github-pr-kb/` Not Gitignored

**What goes wrong:** Cache files committed to git; sensitive PR content in version control.
**Why it happens:** `.gitignore` exists but does not yet include `.github-pr-kb/` (verified — it is absent).
**How to avoid:** Add `.github-pr-kb/` to `.gitignore` as part of Phase 2 setup (Wave 0 task).
**Warning signs:** `git status` shows `.github-pr-kb/` as untracked after first extraction run.

### Pitfall 5: Reacting to `reactions` Dict Inconsistency

**What goes wrong:** `KeyError` or wrong counts when accessing reaction keys.
**Why it happens:** GitHub only includes reaction keys with non-zero counts in some API responses, but the `reactions` property in PyGithub includes the full dict from the raw API response (always has all keys + `total_count`). Use `.get(key, 0)` defensively anyway.
**How to avoid:** Always use `.get(key, 0)` when reading individual reaction counts.
**Warning signs:** Tests pass with mocks but fail against live API.

### Pitfall 6: Test Coverage Misconfiguration

**What goes wrong:** Coverage report shows 0% for new modules even when tests exist.
**Why it happens:** Current `pyproject.toml` has `--cov=github_pr_kb` but `test_config.py` imports use `IsolatedSettings`, so module was never imported. New modules will be covered once test files import them directly.
**How to avoid:** Ensure `test_models.py` and `test_extractor.py` import from `github_pr_kb.models` and `github_pr_kb.extractor` respectively.
**Warning signs:** `CoverageWarning: Module github_pr_kb was never imported` in pytest output.

---

## Code Examples

### Full Authentication + Repo Access

```python
# Source: verified against PyGithub 2.8.1 Auth.Token and Github.__init__
from github import Github, Auth
from github_pr_kb.config import settings

def create_github_client() -> Github:
    auth = Auth.Token(settings.github_token)
    return Github(auth=auth)

def get_repo(client: Github, repo_name: str):
    """repo_name = 'owner/repo'"""
    return client.get_repo(repo_name)
```

### PRRecord + CommentRecord Pydantic Models

```python
# Source: pydantic 2.12.5 BaseModel patterns; field names per decisions D-05 through D-08
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CommentRecord(BaseModel):
    comment_id: int
    comment_type: str          # "review" | "issue"
    author: str                # GitHub login, or "[deleted]"
    body: str
    created_at: datetime
    url: str
    file_path: Optional[str] = None    # review comments only
    diff_hunk: Optional[str] = None    # review comments only
    reactions: dict[str, int] = {}     # non-zero reaction counts only

class PRRecord(BaseModel):
    number: int
    title: str
    body: Optional[str] = None
    state: str
    url: str

class PRFile(BaseModel):
    pr: PRRecord
    comments: list[CommentRecord]
    extracted_at: datetime
```

### Per-PR Cache Write

```python
# Source: pydantic model_dump(mode='json') + pathlib.Path, verified locally
import json
from pathlib import Path
from datetime import datetime, timezone

CACHE_DIR = Path(".github-pr-kb/cache")

def write_pr_cache(pr_file: PRFile) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"pr-{pr_file.pr.number}.json"
    path.write_text(
        json.dumps(pr_file.model_dump(mode="json"), indent=2),
        encoding="utf-8",
    )
    return path
```

### Bot Detection Heuristic

```python
# Source: derived from decisions D-11, D-12
import re

# Known CI/automation bot accounts to skip entirely
SKIP_BOT_LOGINS = frozenset({
    "dependabot[bot]", "dependabot",
    "github-actions[bot]", "github-actions",
    "codecov[bot]", "codecov",
    "renovate[bot]", "renovate",
    "auto-labeler[bot]",
    "stale[bot]",
})

# Minimum substantive content check
_SUBSTANTIVE_RE = re.compile(r"[a-zA-Z]{4,}")  # at least one 4+ char word

def is_noise(login: str, body: str) -> bool:
    """Return True if this comment should be skipped."""
    if login in SKIP_BOT_LOGINS:
        return True
    if not _SUBSTANTIVE_RE.search(body):
        return True   # emoji-only / single-word / blank
    return False
```

---

## Runtime State Inventory

Step 2.5: SKIPPED — this is a greenfield implementation phase (no rename/refactor/migration involved).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | Package management | Yes | 0.8.13 | — |
| Python | Runtime | Yes | 3.14.2 (via uv venv) | — |
| PyGithub | GitHub API extraction | Yes | 2.8.1 (locked in uv.lock) | — |
| pydantic | Data models | Yes | 2.12.5 (locked in uv.lock) | — |
| pytest | Test runner | Yes | >=9.0.2 (dev dep) | — |
| GITHUB_TOKEN | Live API calls (tests use mocks) | Required at runtime | n/a | Tests mocked; extraction requires real token in `.env` |

**Missing dependencies with no fallback:** None.

**Note:** `pytest-mock` is NOT installed. Tests use `unittest.mock` from stdlib — no installation step needed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest >= 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_models.py tests/test_extractor.py -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CORE-01 | `PRRecord` and `CommentRecord` models validate and serialize correctly | unit | `uv run pytest tests/test_models.py -x` | Wave 0 |
| CORE-01 | `GitHubExtractor` authenticates and fetches review + issue comments (mocked) | unit | `uv run pytest tests/test_extractor.py::test_extract_pr_comments -x` | Wave 0 |
| CORE-01 | `write_pr_cache()` creates `.github-pr-kb/cache/pr-N.json` with correct structure | unit | `uv run pytest tests/test_extractor.py::test_cache_write -x` | Wave 0 |
| CORE-01 | Bot comment pre-filter skips `dependabot[bot]` and emoji-only bodies | unit | `uv run pytest tests/test_extractor.py::test_noise_filter -x` | Wave 0 |
| CORE-01 | CodeRabbit/Copilot comments with substantive text are preserved | unit | `uv run pytest tests/test_extractor.py::test_review_bot_kept -x` | Wave 0 |
| CORE-02 | State filter `open`/`closed`/`all` maps to `get_pulls(state=X)` | unit | `uv run pytest tests/test_extractor.py::test_state_filter -x` | Wave 0 |
| CORE-02 | Date range early-stop: PRs past lower bound are skipped without full page fetch | unit | `uv run pytest tests/test_extractor.py::test_date_early_stop -x` | Wave 0 |
| CORE-02 | `updated_at` used for date filtering (not `created_at`) | unit | `uv run pytest tests/test_extractor.py::test_date_filter_uses_updated_at -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_models.py tests/test_extractor.py -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_models.py` — covers CORE-01 model validation and JSON round-trip
- [ ] `tests/test_extractor.py` — covers CORE-01 extraction, CORE-02 filtering, bot detection, cache write

*(No framework config gaps — pytest already configured in pyproject.toml)*

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Github("token")` positional | `Github(auth=Auth.Token("token"))` | PyGithub 2.0 | Old form still works but deprecated; use new form |
| `pydantic` v1 `.dict()` | pydantic v2 `.model_dump(mode='json')` | Pydantic 2.0 | `.dict()` removed in v2; `mode='json'` required for datetime serialization |

**Deprecated/outdated:**
- `Github(login_or_token="token")`: Still accepted but deprecated. Use `Auth.Token`.
- `model.dict()`: Removed in pydantic v2. Use `model.model_dump()`.

---

## Open Questions

1. **`pytest-mock` vs `unittest.mock`**
   - What we know: Both work for PyGithub mocking. `pytest-mock` adds `mocker` fixture for auto-reset between tests.
   - What's unclear: Team preference for fixture style.
   - Recommendation: Use `unittest.mock` (no dependency needed). If tests get complex, add `pytest-mock` later.

2. **Cache directory location relative to CWD**
   - What we know: `.github-pr-kb/cache/` is always relative to the working directory where the CLI is invoked.
   - What's unclear: What happens when the user runs from a subdirectory? Phase 6 (CLI) will likely need to walk up to find project root.
   - Recommendation: For Phase 2, hardcode `Path(".github-pr-kb/cache")`. Phase 6 adds root detection.

---

## Sources

### Primary (HIGH confidence)

- PyGithub 2.8.1 source (installed locally) — inspected `Auth`, `Github`, `PullRequest`, `PullRequestComment`, `IssueComment`, `PaginatedList`, `Repository.get_pulls` signatures and implementations
- pydantic 2.12.5 (installed locally) — `model_dump(mode='json')`, `model_validate_json()` round-trip behavior verified by running code
- Python stdlib — `unittest.mock.MagicMock`, `pathlib.Path`, `datetime.timezone` behaviors verified

### Secondary (MEDIUM confidence)

- `.planning/phases/02-github-extraction-core/02-CONTEXT.md` — locked decisions D-01 through D-15
- `.planning/phases/01-project-foundation/01-01-SUMMARY.md` — confirmed installed stack versions

### Tertiary (LOW confidence)

- None.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries inspected from installed source; versions from uv.lock
- Architecture: HIGH — patterns verified by running code locally
- Pitfalls: HIGH — timezone and None-body issues confirmed by inspection; gitignore gap confirmed by file check

**Research date:** 2026-04-02
**Valid until:** 2026-05-02 (stable libraries; PyGithub 2.x API stable)
