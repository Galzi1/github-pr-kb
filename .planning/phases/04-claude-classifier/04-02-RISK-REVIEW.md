# Plan Risk Review: 04-02 — PRClassifier Implementation

**Reviewed:** 2026-04-05
**Plan:** `.planning/phases/04-claude-classifier/04-02-PLAN.md`
**Overall Risk Level:** Moderate

---

## 1. Plan Summary

**Purpose:** Implement the `PRClassifier` class that reads cached PR comment files (`pr-N.json`), classifies each comment via the Claude API using Haiku, deduplicates via SHA-256 body hashing, writes `classified-pr-N.json` output files and a `classification-index.json` index, and flags low-confidence results for review.

**Key components touched:**
- `src/github_pr_kb/classifier.py` — full implementation (currently a one-line stub)
- `tests/test_classifier.py` — 7 tests (file does not yet exist)
- Reads from `models.py` (ClassifiedComment, ClassifiedFile — expected from Plan 01)
- Reads from `config.py` (anthropic_api_key — expected from Plan 01)
- External dependency: Anthropic Python SDK (`anthropic==0.84.0`)

**Plan's own stated assumptions:**
- Plan 01 has already been executed (models and config changes in place)
- The Anthropic SDK's `messages.create()` API is stable across 0.84.0–0.89.0
- `claude-3-5-haiku-latest` is sufficient for 5-category classification
- One API call per comment is the right granularity

**Theory of success:** If Claude reliably returns parseable JSON with valid categories and float confidence values, and if the SHA-256 index prevents redundant calls, then the classifier will be cheap, fast, and correct.

---

## 2. Assumptions & Evidence

### A1: Plan 01 has been executed (FOUNDATIONAL)
- **Status: NOT YET TRUE.** `models.py` lacks `ClassifiedComment` and `ClassifiedFile`. `config.py` still has `anthropic_api_key` commented out. `tests/test_classifier.py` does not exist.
- **Evidence:** Direct file reads confirm Plan 01 artifacts are absent.
- **Blast radius if wrong:** Plan 02 cannot even begin — every import will fail. The `depends_on: ["04-01"]` is correctly declared but the dependency is **not yet satisfied**.
- **Testable?** Yes — it's a secret, not a mystery. Run Plan 01 first.

### A2: `anthropic_api_key` will be `str | None = None` in Settings (STRUCTURAL)
- **Status: Ambiguous.** The RESEARCH doc's Open Question 1 recommends `str | None = None` with a `ValueError` in `PRClassifier.__init__`, but the same document's "Config Extension" pattern shows `anthropic_api_key: str` (required). Plan 02 assumes `str | None = None` (its `__init__` raises `ValueError` if None).
- **Evidence:** Plan 02 Task 1 explicitly codes `if settings.anthropic_api_key is None: raise ValueError(...)`, consistent with the optional approach.
- **Blast radius if wrong:** If Plan 01 made it required (`str`), then tests that don't set `ANTHROPIC_API_KEY` will fail at import time with `ValidationError`, not at classifier construction time. The `ValueError` check in `__init__` becomes dead code. However, the conftest pattern (`os.environ.setdefault`) should cover this either way.
- **Testable?** Yes — check what Plan 01 actually does. This is a coordination gap between the two plans.

### A3: Claude returns valid JSON when instructed (STRUCTURAL)
- **Status: Justified with mitigation.** The plan includes a fallback to `{"category": "other", "confidence": 0.0, "summary": "classification failed"}` on parse failure. This is the correct defense.
- **Evidence:** Research doc Pitfall 2 documents this risk and the mitigation.
- **Blast radius if wrong:** Individual comments get `other/0.0` — low impact. The `needs_review` flag will catch these.

### A4: SHA-256 body hash is sufficient for dedup (PERIPHERAL)
- **Status: Justified.** SHA-256 is collision-resistant. Identical bodies produce identical hashes. No fuzzy matching needed per D-04.
- **Blast radius if wrong:** Negligible — SHA-256 collision probability is astronomically low.

### A5: Per-comment atomic index writes are acceptable at PR comment scale (STRUCTURAL)
- **Status: Justified.** Tens to hundreds of comments per run. One `mkstemp + os.replace` per comment is negligible I/O overhead.
- **Blast radius if wrong:** Performance degradation on very large repos. Mitigated by the dedup cache itself — second runs are zero-cost.

### A6: `anthropic.APIError` is the correct exception to catch after retries exhaust (STRUCTURAL)
- **Status: Likely correct but not verified.** The SDK documentation says `max_retries` controls retry behavior and raises after exhaustion. The specific exception class needs verification.
- **Evidence:** Research doc states this but flags it as "SDK built-in retry" without citing the exact exception hierarchy.
- **Blast radius if wrong:** Unhandled exception crashes the classify run mid-flight. All progress for the current PR is lost (though the per-comment index writes save prior work).
- **Testable?** Yes — inspect `anthropic` exception hierarchy in the SDK.

### A7: `response.content[0].text` is always accessible (PERIPHERAL)
- **Status: Justified for text-only responses.** With `max_tokens=256` and no tool use, the response will always have at least one `TextBlock`.
- **Blast radius if wrong:** `IndexError` on empty content list. Extremely unlikely with a valid prompt.

### A8: The plan assumes Windows filesystem behavior for `os.replace` and `tempfile.mkstemp` (PERIPHERAL)
- **Status: Justified.** The same pattern is already working in `extractor.py` on this Windows machine.
- **Evidence:** Plan explicitly reuses the existing `_write_cache_atomic` pattern.

---

## 3. Ipcha Mistabra — Devil's Advocacy

### 3a. The Inversion Test

**Claim: "One comment per API call is simple, reliable, and easy to cache."**

*Inversion:* One-call-per-comment is actually the **most expensive and slowest** approach. A PR with 50 comments means 50 separate API calls, each with the overhead of the system prompt re-sent. Batching 5-10 comments per call would reduce costs by 3-5x (system prompt amortization) and latency by the same factor. The per-comment caching advantage is real but marginal — in practice, truly identical comments across PRs are rare (different file paths, different context). The dedup index may have a very low hit rate, making the "easy to cache" argument weaker than it sounds.

**Assessment:** The inversion is credible but the plan's approach is the right call for a first implementation. The simplicity/debuggability trade-off is valid at this scale. However, the plan should acknowledge that batch classification is a natural optimization for Phase 6+ if the tool sees real usage.

---

**Claim: "SHA-256 body hash dedup prevents redundant API calls."**

*Inversion:* The dedup only works for **byte-identical** comment bodies. In practice, the same conceptual comment rarely appears verbatim across PRs. The index will grow unboundedly but provide diminishing returns. The real value of the index is **re-run idempotency** (running classify twice on the same PR), not cross-PR dedup. The plan conflates these two use cases.

**Assessment:** The inversion is partially correct. The primary value is re-run safety (confirmed by the test `test_cache_hit_no_api_call` which re-classifies the *same* PR). Cross-PR dedup is a bonus, not the main benefit. This framing difference doesn't change the implementation, but understanding it matters for future design decisions.

---

### 3b. The Little Boy from Copenhagen

**A new engineer joining next month** would ask: "Why does `classify_all` not return any indication of which PRs succeeded vs. failed? It returns `list[Path]` but I don't know which PRs were skipped due to `FileNotFoundError`." Good question — the return type hides partial failures.

**An SRE at 3 AM** would ask: "If I accidentally run `classify_all` on 500 PRs with an invalid API key, how long before I notice? The `ValueError` on init is good, but what if the key is valid but rate-limited?" The SDK's `max_retries=2` will retry, but if the account is out of credits, every comment will fail with a WARNING log, the `failed_count` will climb, and the run will complete silently with zero useful output. The summary message at the end is the only signal.

**A cost-conscious manager** would ask: "Is there a dry-run mode? Can I see how many API calls *would* be made before committing?" The plan has no dry-run capability. For a first implementation this is acceptable, but it's a natural feature for Phase 6 CLI.

### 3c. Failure of Imagination Check

**Scenario: Classification-index.json corruption.** If the JSON file is corrupted (e.g., truncated write despite atomic pattern — possible on network-mounted Windows drives with aggressive caching), the classifier will fall back to an empty dict on `JSONDecodeError` and **re-classify every comment**, incurring the full API cost again. The plan handles this gracefully (empty dict fallback), but doesn't log a WARNING when it happens — the user won't know their index was lost.

**Scenario: Claude model deprecation.** The plan hardcodes `claude-3-5-haiku-latest`. If Anthropic deprecates this model alias, the classifier will fail on every API call. The `latest` suffix mitigates this somewhat, but model naming conventions have changed before. The `model` parameter on `__init__` makes this configurable, which is good.

**Scenario: Extremely long comment bodies.** The plan sends `comment.body` as the entire user message. If a PR has a comment with 100K characters (e.g., an auto-generated changelog), this will consume significant input tokens and may hit context limits. No truncation or size guard exists.

---

## 4. Risk Register

| ID | Category | Description | Trigger | Prob | Severity | Priority | Detection | Mitigation | Contingency | Assumption |
|----|----------|-------------|---------|------|----------|----------|-----------|------------|-------------|------------|
| R1 | Schedule | Plan 01 not executed — Plan 02 cannot start | Attempting to import ClassifiedComment, ClassifiedFile | High | Critical | **Critical** | Import error on first line | Execute Plan 01 before Plan 02 | None — hard blocker | A1 |
| R2 | Technical | `anthropic_api_key` type mismatch between Plan 01 and Plan 02 (required vs optional) | Tests pass but `ValueError` in `__init__` is dead code, or conftest `setdefault` is insufficient | Medium | Low | **Medium** | Test coverage of the ValueError path | Verify Plan 01's implementation before coding Plan 02 | Adjust whichever is wrong | A2 |
| R3 | Technical | Exception class `anthropic.APIError` may not be the correct catch-all after retry exhaustion | SDK raises a different exception subclass | Low | Medium | **Medium** | Unhandled exception during classify run | Verify SDK exception hierarchy via introspection | Broaden catch to `anthropic.APIError` base class (likely correct) | A6 |
| R4 | Operational | Very long comment bodies consume excessive tokens or hit context limits | Auto-generated comments, bot-generated changelogs | Low | Medium | **Low** | Unexpected API cost spike; `APIError` on context overflow | Add a body length guard (e.g., truncate at 10K chars) | Catch the error and skip the comment | — |
| R5 | Operational | Index corruption goes unnoticed — full re-classification cost | Corrupted `classification-index.json` | Low | Medium | **Low** | Sudden increase in API calls on a re-run | Log WARNING when `JSONDecodeError` on index load | Index rebuild is the correct behavior; the cost is the risk | A5 |
| R6 | Technical | `classify_all` returns `list[Path]` but doesn't actually collect paths | Implementation doesn't build the return list correctly | Low | Low | **Low** | Return value is empty or wrong | Verify in tests | Minor — summary output is the primary signal | — |

**Known Knowns:** R1 (Plan 01 dependency), R2 (config type question)
**Known Unknowns:** R3 (exact exception hierarchy), R4 (comment body size distribution)
**Unknown Unknowns surfaced:** R5 (silent index corruption)

---

## 5. Verdict & Recommendations

### Overall Risk Level: Moderate

The plan is well-structured, detailed, and follows established codebase patterns. The single critical risk (R1) is a sequencing issue, not a design flaw. The remaining risks are low-to-medium and have reasonable mitigations.

### Top 3 Risks

1. **R1 — Plan 01 not executed.** This is a hard blocker. The `depends_on: ["04-01"]` is correctly declared, but the dependency is demonstrably not yet satisfied. Execute Plan 01 first.

2. **R2 — Config type coordination.** Plan 02 assumes `anthropic_api_key: str | None = None` and guards with a `ValueError`. If Plan 01 makes it required (`str`), the guard is dead code and the test setup may differ. Low severity but worth aligning before implementation.

3. **R3 — Exception class uncertainty.** The `anthropic.APIError` catch is likely correct (it's the base class for all API errors in the SDK), but hasn't been verified via introspection. A quick `python -c "import anthropic; print(anthropic.APIError.__mro__)"` would resolve this.

### Recommended Actions

- **Before starting:** Confirm Plan 01 is complete. If not, execute it first.
- **Quick verification:** Run `python -c "from github_pr_kb.models import ClassifiedComment"` to confirm models exist.
- **Consider adding:** A `WARNING` log when `classification-index.json` fails to parse (currently silent empty-dict fallback).
- **Future consideration (not this phase):** Body length guard on comment input, dry-run mode for `classify_all`.

### Open Questions

- The plan specifies `classify_all` should "collect output paths" but the implementation detail of *how* (append to list after each `classify_pr` call) is implicit. This is minor but could lead to a bug where the list isn't built correctly.
- The plan doesn't address whether `classify_pr` should skip comments with empty bodies. An empty body produces a valid SHA-256 hash and a valid (if useless) API call.

### What the Plan Does Well

- **Excellent pitfall coverage.** The research document identifies and mitigates every major failure mode (JSON parse errors, category normalization, confidence clamping, import-time validation).
- **Per-comment index writes.** This is the right call — it trades negligible I/O overhead for crash-safe progress.
- **Atomic writes throughout.** Reusing the proven `mkstemp + os.replace` pattern prevents partial writes.
- **Defensive normalization.** Category validation against `VALID_CATEGORIES`, confidence clamping to `[0.0, 1.0]`, summary truncation at 200 chars — these are all good guards against LLM output variability.
- **Clear test expectations.** 7 specific tests with exact assertions make the GREEN phase straightforward.
