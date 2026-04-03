# Risk Review: Plan 02-02 — GitHub Extraction Core Implementation

**Plan reviewed:** `.planning/phases/02-github-extraction-core/02-02-PLAN.md`
**Review date:** 2026-04-03
**Reviewer:** Claude (Ipcha Mistabra analysis)

---

## 1. Plan Summary

**Purpose:** Implement the GitHub extraction layer — authenticate via PAT, iterate PRs with state/date filters, collect review and issue comments, filter noise (bots, emoji-only), and write per-PR JSON cache files to `.github-pr-kb/cache/`.

**Key components touched:**
- `src/github_pr_kb/extractor.py` (new implementation, replacing stub)
- `tests/test_extractor.py` (new, 12 test functions with mocked PyGithub)
- `.gitignore` (append `.github-pr-kb/` entry)

**Upstream dependencies:**
- `src/github_pr_kb/models.py` — provides `PRRecord`, `CommentRecord`, `PRFile` (currently a stub from Phase 1)
- `src/github_pr_kb/config.py` — provides `settings.github_token` (module-level instantiation)
- PyGithub 2.8.1, pydantic 2.12.5 (both installed and locked)

**Theory of success:** The plan succeeds if PyGithub's API behaves as the research describes, the models from Plan 02-01 are implemented before this plan runs, `settings` imports cleanly in test environments, and the mock patterns faithfully represent PyGithub's real object shapes.

**Stated assumptions:**
- All libraries are installed and version-locked
- Models are implemented by the prior plan (02-01)
- PyGithub `reactions` property returns a dict-like object
- `get_pulls(sort='updated', direction='desc')` produces a stable descending order suitable for early-stop

---

## 2. Assumptions & Evidence

### A1: `models.py` is implemented before this plan executes
- **Type:** Explicit (plan lists 02-01 as dependency)
- **Classification:** Foundational
- **Evidence:** Plan frontmatter says `depends_on: ["02-01"]`. Currently `models.py` is a docstring stub.
- **If wrong:** Every test in `test_extractor.py` fails on import. The plan cannot produce a single green test.
- **Testable?** Yes — check that Plan 02-01 has been executed. This is a **secret**, not a mystery.

### A2: `settings` import succeeds in test environments
- **Type:** Implicit — the plan never discusses this
- **Classification:** Foundational
- **Evidence:** `extractor.py` has `from github_pr_kb.config import settings` at module level. `config.py` runs `settings = Settings()` on import, which requires `GITHUB_TOKEN` in the environment or `.env`. Test files import from `extractor`, triggering this chain.
- **If wrong:** All 12 extractor tests fail with `pydantic.ValidationError` before any test body runs. This will happen in CI environments, fresh clones, or any machine without `.env`.
- **Testable?** Yes — run `GITHUB_TOKEN= uv run pytest tests/test_extractor.py` and observe the failure.
- **Blast radius:** HIGH. This blocks the entire test suite for this plan, and is silent in dev environments where `.env` exists.

### A3: `comment.reactions` is a dict-like object supporting `.get()`
- **Type:** Explicit (research claims "verified against PullRequestComment source")
- **Classification:** Structural
- **Evidence:** The research document states `comment.reactions` returns "the raw dict from GitHub's API." However, PyGithub objects frequently wrap raw API data in typed objects (e.g., `NamedUser`, `Label`). The `reactions` attribute may be a dict in PyGithub 2.8.1, or it may be a `Reactions` object with attribute access.
- **If wrong:** `_extract_reactions` calls `.get()` on a non-dict object, producing `AttributeError` at runtime. Tests pass because mocks supply a plain dict — classic mock/reality divergence.
- **Testable?** Yes — inspect the installed source: `python -c "import inspect, github.PullRequestComment; print(inspect.getsource(github.PullRequestComment.PullRequestComment))"`. This is a **secret**.

### A4: `get_pulls(sort='updated', direction='desc')` returns PRs in strictly descending `updated_at` order
- **Type:** Implicit — the early-stop logic depends on this ordering guarantee
- **Classification:** Structural
- **Evidence:** GitHub REST API docs confirm `sort=updated&direction=desc` ordering. PyGithub passes these params directly. However, the ordering is across pages, not just within a page, and GitHub's pagination implementation is the one enforcing it.
- **If wrong:** Early-stop (`break` when `pr.updated_at < since`) could skip valid PRs that appear later in a differently-ordered page. The extraction silently misses data.
- **Testable?** Yes — verify against the GitHub API docs and a small live test. This is a **secret** (the API docs confirm the ordering).

### A5: `MagicMock` faithfully represents PyGithub iteration patterns
- **Type:** Implicit
- **Classification:** Structural
- **Evidence:** The mock helper functions set attributes directly (e.g., `pr.number = 42`). `MagicMock` auto-creates attribute chains, so `comment.user.login` works. However, `get_review_comments().return_value = [list]` means iteration returns a plain list, not a `PaginatedList`. The real `PaginatedList` has different memory and timing characteristics.
- **If wrong:** Tests pass but real-world behavior differs. This is the standard mock fidelity tradeoff — acceptable for unit tests, but it means these tests cannot catch pagination-related bugs.
- **Testable?** Partially — integration tests against the real API would catch divergences, but those are out of scope for this phase.

### A6: The `is_noise` heuristic correctly separates signal from noise
- **Type:** Explicit
- **Classification:** Peripheral
- **Evidence:** The regex `[a-zA-Z]{4,}` requires at least one 4+ character English word. This filters emoji-only and "LGTM" (4 chars exactly — wait, "LGTM" IS 4 chars and would PASS the filter). The plan's test says `test_noise_filter_skips_emoji_only: Comment body "LGTM" (single word) is filtered out` — but `_SUBSTANTIVE_RE.search("LGTM")` matches because "LGTM" is 4 characters.
- **If wrong:** "LGTM" and similar short approval comments are kept when the plan intends them filtered. Minor data quality issue.
- **Blast radius:** Low — these are low-value comments but won't break anything.

### A7: The `SKIP_BOT_LOGINS` set covers the important bots
- **Type:** Explicit (plan says "can start with common ones and be extended")
- **Classification:** Peripheral
- **Evidence:** Covers dependabot, github-actions, codecov, renovate, auto-labeler, stale. Omits: `sonarcloud[bot]`, `snyk-bot`, `mergify[bot]`, `allcontributors[bot]`, `netlify[bot]`, `vercel[bot]`.
- **If wrong:** Some bot noise leaks through. Easy to extend later.
- **Testable?** The list is maintainable. Not a blocker.

---

## 3. Ipcha Mistabra — Devil's Advocacy

### 3a. Inversions

**Inversion 1: "Module-level `settings` import is clean and fail-fast" → It is fragile and test-hostile.**

The plan frames `from github_pr_kb.config import settings` as a feature ("fail-fast before any CLI logic runs"). But this makes the module un-importable without a valid `GITHUB_TOKEN`. Every test file that imports from `extractor.py` must have the token available — not for the test to use, but for the import to succeed.

The existing `test_config.py` carefully avoids importing `settings` by recreating `IsolatedSettings`. The extractor tests cannot use this workaround because they need to import `GitHubExtractor`, which imports `settings` in its module body.

**Strength of inversion:** Strong. This is likely to cause real test failures in CI. The plan's test template has no mention of setting up `GITHUB_TOKEN` in a conftest or via environment variables.

**Inversion 2: "Mocked tests validate extraction correctness" → Mocked tests validate mock correctness.**

The 12 tests all use `MagicMock` to simulate PyGithub. None hit a real API. This means the tests verify that the extractor code correctly processes objects shaped like what the developer *believes* PyGithub returns. If the belief is wrong (e.g., `reactions` is not a dict, `get_review_comments` returns a different shape), tests pass and production fails.

**Strength of inversion:** Moderate. The research claims the PyGithub shapes were "verified against installed source," which partially mitigates this. But the mocks are still a translation of that understanding, and translations can introduce errors.

**Inversion 3: "Early-stop makes extraction efficient" → Early-stop makes extraction fragile.**

Breaking out of a loop when `pr.updated_at < since` assumes perfect ordering. If a single PR has an anomalous `updated_at` (e.g., a bot updates it retroactively, or GitHub's internal clocks drift), the early-stop fires too soon and silently drops valid PRs. There is no logging, no warning, and no way for the user to know data was missed.

**Strength of inversion:** Weak-to-moderate. GitHub's ordering is reliable in practice, but the "silent data loss" failure mode is worth noting.

### 3b. The Little Boy from Copenhagen

**A new engineer joining next month** would look at `extractor.py` and ask: "Where is the error handling for API failures? What happens if `get_repo()` raises a 404? What if `get_review_comments()` times out mid-page?" The plan has zero error handling for HTTP/API failures. This is acceptable for a Phase 2 MVP, but the code will be brittle against network issues.

**An SRE at 3 AM** would ask: "Where are the logs? If the extraction silently drops half the PRs because of a date parsing bug, how would anyone know?" There is no logging in the plan at all.

**A user running the tool for the first time** might set `since` as a naive datetime (without timezone), triggering `TypeError: can't compare offset-naive and offset-aware datetimes`. The pitfall is documented in RESEARCH.md, but the plan's `extract()` signature takes `Optional[datetime]` with no validation that it is tz-aware.

### 3c. Failure of Imagination

**Scenario:** PyGithub 2.8.1's `PullRequestComment.reactions` returns a `dict` today, but a minor version bump changes it to a `Reactions` object. The mocked tests continue to pass (they supply dicts), production breaks. Nobody notices until a user reports "extraction crashes on repos with reactions."

**Scenario:** A repository has 10,000+ PRs. The plan iterates lazily, which is good for page fetches, but collects `list(pr.get_review_comments())` and `list(pr.get_issue_comments())` per PR. A single PR with 500+ comments could produce a large in-memory list. This won't crash, but it's a latent memory concern for large-scale usage.

---

## 4. Risk Register

| ID | Category | Description | Trigger | Prob | Severity | Priority | Detection | Mitigation | Contingency | Assumption |
|----|----------|-------------|---------|------|----------|----------|-----------|------------|-------------|------------|
| R1 | Technical | `settings` import fails in test environments without `.env` or `GITHUB_TOKEN` | Running tests in CI, fresh clone, or without `.env` file | **High** | **Critical** | **Critical** | Tests fail with `ValidationError` on first import | Add a `conftest.py` that sets `GITHUB_TOKEN=fake` via `monkeypatch` or `os.environ` before any extractor imports; or defer `settings` access to method call time rather than import time | Patch `github_pr_kb.config.settings` in tests before importing extractor | A2 |
| R2 | Technical | `models.py` is still a stub when this plan executes | Running Plan 02-02 before Plan 02-01 completes | **Low** | **Critical** | **High** | `ImportError` on `from github_pr_kb.models import PRRecord` | Plan dependency is explicit (`depends_on: ["02-01"]`); executor should verify | Re-run Plan 02-01 first | A1 |
| R3 | Technical | `comment.reactions` is not a plain dict in PyGithub 2.8.1 | Calling `_extract_reactions(comment.reactions)` on a real PyGithub comment | **Low** | **High** | **Medium** | `AttributeError: 'Reactions' object has no attribute 'get'` at runtime | Verify by inspecting installed PyGithub source before implementing | Add `.get()` fallback or use `getattr` pattern | A3 |
| R4 | Technical | "LGTM" passes the `is_noise` filter (4 chars = matches `[a-zA-Z]{4,}`) | Any comment body containing "LGTM" or similar 4-char words | **High** | **Low** | **Low** | Comments with body "LGTM" appear in extracted data | Change regex to `{5,}` or add explicit short-comment denylist | Accept as minor noise — classifier can handle downstream | A6 |
| R5 | Operational | No error handling for API failures (404, rate limits, timeouts) | Network issues, invalid repo name, GitHub outage, rate limit hit | **Medium** | **Medium** | **Medium** | Unhandled exception crashes the extraction mid-run with a traceback | Out of scope for Phase 2; document as known limitation | User re-runs after fixing the issue; no data corruption since writes are per-PR | — |
| R6 | Operational | No logging — silent data loss if early-stop fires incorrectly | Edge case in PR ordering or tz-naive datetime passed as `since` | **Low** | **Medium** | **Low** | User notices missing PRs in cache, but has no diagnostic info | Add `logging.debug` calls for skipped/stopped PRs | Manually inspect cached files against expected PR list | A4 |
| R7 | Technical | Naive datetime passed as `since`/`until` causes `TypeError` | User (or Phase 6 CLI) passes `datetime.now()` instead of `datetime.now(timezone.utc)` | **Medium** | **Medium** | **Medium** | `TypeError` at runtime during date comparison | Validate tz-awareness in `extract()` entry point, or coerce naive datetimes to UTC | Document in docstring that datetimes must be tz-aware | — |

### Risk Classification

- **Known Knowns:** R2 (dependency ordering), R4 (LGTM filter), R5 (no error handling — documented as out of scope)
- **Known Unknowns:** R3 (reactions object shape — testable but not yet confirmed), R7 (datetime tz-awareness at integration boundaries)
- **Unknown Unknowns surfaced by review:** R1 (settings import in tests — not mentioned anywhere in the plan)

---

## 5. Verdict & Recommendations

### Overall Risk Level: **Moderate**

The plan is well-researched, well-specified, and appropriately scoped. The single critical risk (R1: settings import in tests) is straightforward to fix but will block the entire plan if missed.

### Top 3 Risks

1. **R1 — Settings import breaks tests (Critical).** This is the most likely showstopper. The plan never addresses how `test_extractor.py` will import from a module that triggers `Settings()` validation. The existing `test_config.py` pattern (using `IsolatedSettings`) is not applicable here because the extractor module itself imports `settings` at module level.

2. **R3 — Reactions object shape (Medium).** If `comment.reactions` is not a dict, the entire reactions extraction path fails at runtime while tests pass happily with mocked dicts. Quick verification against the installed source resolves this before writing code.

3. **R7 — Naive datetime comparison (Medium).** This won't surface until Phase 6 integrates the CLI with the extractor. A single defensive check at the `extract()` entry point prevents a confusing runtime error later.

### Recommended Actions

1. **Before coding:** Verify `comment.reactions` type by inspecting the installed PyGithub source. Run: `python -c "import github.PullRequestComment; help(github.PullRequestComment.PullRequestComment.reactions)"` — confirm it's a dict or adjust `_extract_reactions` accordingly.

2. **During Task 2 (tests):** Add a `conftest.py` in `tests/` (or update the existing one) that ensures `GITHUB_TOKEN` is available as a dummy value before any extractor module imports. Options:
   - `@pytest.fixture(autouse=True)` that sets `os.environ["GITHUB_TOKEN"] = "test-token-not-real"`
   - Or use `monkeypatch.setenv` in a session-scoped fixture
   - Or mock `github_pr_kb.config.settings` at the conftest level

3. **During Task 3 (implementation):** Consider whether the `is_noise` regex `[a-zA-Z]{4,}` is correct for filtering "LGTM". If "LGTM" should be noise, use `{5,}` or add a secondary check for comment length (e.g., `len(body.split()) <= 1 and len(body) < 10`).

4. **Post-implementation:** Add a brief smoke note to the summary that error handling and logging are deferred to a later phase, so this doesn't get lost.

### Open Questions

- **How does CI set up `GITHUB_TOKEN` for tests?** The plan uses mocks (no real API calls), but the config module demands the env var at import time. This needs a project-level decision.
- **Is `_SUBSTANTIVE_RE` the right heuristic?** "LGTM" (4 chars) passes it. Is that intended? The test says it should be filtered, which contradicts the regex.

### What the Plan Does Well

- **Thorough research backing.** Every pattern cites the research document with specific PyGithub source verification. This is above-average plan quality.
- **TDD approach.** Tests are written before implementation (Task 2 before Task 3), with explicit RED→GREEN progression.
- **Lazy pagination with early-stop.** The plan correctly avoids `list(get_pulls(...))` and exploits sorted-desc ordering for efficient date filtering.
- **Explicit pitfall documentation.** The RESEARCH.md captures six concrete pitfalls, and the plan addresses each one.
- **Cache isolation in tests.** Using `tmp_path` for cache directory prevents test pollution — a detail often missed.

---

*Review methodology: Five-phase critical analysis per Ipcha Mistabra doctrine — comprehension, assumption surfacing, devil's advocacy, structured risk register, honest verdict.*
