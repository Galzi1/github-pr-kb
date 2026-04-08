# Risk Review: 07-03-PLAN.md

**Overall risk: High.** `07-03-PLAN.md` is directionally right, but it is **not execution-safe on the current tree** because it relies on contracts from `07-01` and `07-02` that are not present in `src\github_pr_kb\generator.py`, and it treats a few semantics as solved when they are still ambiguous or wrong.

## 1. Plan Summary

**Purpose:** make the CLI report classify/generate outcomes honestly, add `--regenerate` to `generate`, and fail fast with a clear message when article generation lacks API credentials.

**Key components touched:** `src\github_pr_kb\cli.py`, `tests\test_cli.py`, with hard runtime coupling to `src\github_pr_kb\generator.py` and `src\github_pr_kb\classifier.py`.

**Plan’s stated assumptions:**
- `KBGenerator.generate_all(regenerate=...)` already exists.
- `GenerateResult.filtered` already exists.
- `KBGenerator()` now raises a `ValueError` for missing `ANTHROPIC_API_KEY`.
- `classifier._review_count` and `classifier._failed_count` are the right numbers to expose to users.
- Existing exit-code behavior already satisfies D-12.

**Theory of success:** if the CLI surfaces the right counters, wires `--regenerate`, and maps config failures clearly, users will finally see truthful pipeline outcomes and can intentionally rebuild articles.

## 2. Assumptions & Evidence

| ID | Assumption | Explicit? | Evidence | Status | Blast radius if wrong | Validate before execution |
|---|---|---:|---|---|---|---|
| A1 | `07-01` foundation changes landed | Yes | Current `src\github_pr_kb\generator.py` still has `GenerateResult(written, skipped, failed)` only; no `filtered`. `classifier.py` still writes `"classification failed"` fallback entries. Referenced `07-01-SUMMARY.md` is missing. | **False on current tree** | High | Verify `07-01` actually merged or fold missing work into downstream plans |
| A2 | `07-02` generator API landed | Yes | Current `KBGenerator.__init__` has no API key/model args, and `generate_all(self)` takes no `regenerate` parameter. `07-03` still references “From Plan 02” contracts. | **False on current tree** | High | Add `07-02` as a real prerequisite and verify code, not plan text |
| A3 | `classifier._review_count` means “all items needing review in this run” | Implicit | In `classifier.py`, `_review_count` increments only for newly classified low-confidence items; cache hits do not increment it even if `needs_review=True`. | **Weak / likely misleading** | Medium-High | Decide whether cached low-confidence items belong in the CLI review count |
| A4 | Existing exit-code behavior already meets D-12 | Yes | The proposed CLI only special-cases constructor/config failure. It does not address “no cache” or “all generation failed” paths, both called out by D-12. | **Incomplete** | High | Define total-failure semantics precisely and test them |
| A5 | Using `getattr(..., 0)` on private classifier counters is safe | Implicit | This avoids crashes, but it can silently report false zeroes if classifier internals drift. That is the opposite of “honest reporting.” | **Weak** | High | Expose a public summary contract or fail loudly when required counters are absent |
| A6 | CLI-only tests are enough to prove behavior | Implicit | The tests are mock-heavy and can pass even when the real generator/classifier contracts are still incompatible with this plan. | **Weak** | Medium-High | Add at least one contract-level test around real current signatures/semantics |

## 3. Ipcha Mistabra — Devil’s Advocacy

### Inversion test

The plan says this will make CLI output more honest. **The opposite is plausible:** it may make output *more confidently wrong*. If `_review_count` undercounts cached review items, and `getattr(..., 0)` silently masks missing counters, the CLI will produce neat summaries that look trustworthy while misrepresenting what happened.

The plan says `--regenerate` is just a CLI exposure of existing behavior. **The opposite is plausible:** it exposes a code path that does not yet exist on the current branch, so the CLI phase can become the first place dependency drift turns into a user-visible failure.

The plan says exit-code behavior is already correct. **The opposite is plausible:** the CLI will still return `0` for some “everything effectively failed” scenarios, especially empty/no-cache inputs or runs where every synthesis attempt fails inside `generate_all()` rather than at construction time.

### Little boy from Copenhagen

A new engineer would immediately ask why `07-03` depends only on `07-01` while its interface section explicitly relies on `07-02` (`generate_all(regenerate=...)`). That mismatch is not cosmetic; it affects execution ordering.

An on-call engineer would ask: “If every article synthesis fails but the process stays up, do I get a non-zero exit so automation notices?” The plan does not answer that.

A user would ask: “Does `need review` include cached low-confidence items or only newly classified ones?” The plan assumes the answer without defining it.

### Failure of imagination check

The most likely surprise failure is **not** a crash; it is a **successful-looking lie**:
- classify reports too few “need review” items,
- generate reports zeros because a private attr moved,
- the command exits `0`,
- and downstream automation treats the run as healthy.

A second overlooked failure is **dependency ghosting**: because the phase docs exist, people may assume `07-01`/`07-02` already landed even though the code does not show those contracts.

A third is **over-broad config error masking**: catching any `ValueError` from `KBGenerator()` and rewriting it as “missing environment variable” can mislabel other generator-side validation failures.

## 4. Risk Register

| Risk ID | Type | Category | Description | Trigger | Probability | Severity | Priority | Detection | Mitigation | Contingency | Assumption link |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R1 | Unknown known | Technical | `07-03` depends on `07-01` and `07-02` contracts that are absent from the current tree; `depends_on` also omits `07-02` | Execute on current branch | High | High | **High** | Signature/attribute errors, failing real runs, missing summary artifact | Verify code-level prerequisites and add `07-02` as explicit dependency | Pause `07-03` and repair dependency chain first | A1, A2 |
| R2 | Known known | Product/UX | `need review` count is likely semantically wrong because cached low-confidence items are not counted | Repeated classify runs with cache hits | High | Medium-High | **High** | Compare cached items’ `needs_review` vs CLI summary | Define the metric and compute it from actual returned items, not just `_review_count` | Reword output to “new need review” if that is the intended metric | A3 |
| R3 | Known known | Technical | `getattr(..., 0)` on private attrs can silently hide classifier contract drift and produce false-zero summaries | Internal rename/refactor or partial mocks | Medium-High | High | **High** | Suspicious zero counts despite processed work | Replace private attr scraping with a public summary API or assert required attrs exist | Fail command loudly rather than emitting dishonest output | A5 |
| R4 | Known unknown | Operational | D-12 total-failure semantics are underspecified; some full-failure states may still exit `0` | No cache, empty inputs, or all synthesis attempts fail inside generation | Medium | High | **High** | CI/scripts treat bad runs as success | Define total failure precisely and add explicit checks/tests | Return exit `1` for zero-success + non-empty failure cases if that matches product intent | A4 |
| R5 | Known known | Technical | Catching all `ValueError` as “missing ANTHROPIC_API_KEY” can misdiagnose non-config generator failures | Future generator validation also uses `ValueError` | Medium | Medium-High | **Medium-High** | Error message disagrees with underlying cause | Match on missing-key failure more narrowly or introduce a dedicated exception | Preserve original error text for non-config `ValueError`s | A4 |
| R6 | Unknown known | Testing | Mock-heavy CLI tests can pass while real contracts are still incompatible with this phase | Implement exactly as planned, mostly against mocks | High | Medium-High | **High** | Green CLI tests but broken live command behavior | Add contract-level coverage against real current generator/classifier interfaces | Treat this phase as blocked until dependency tests pass | A6 |

## 5. Verdict & Recommendations

**Overall risk level: High.** The plan is sensible as a CLI polish phase, but right now it is trying to finalize user-facing behavior on top of unverified upstream code and ambiguous summary semantics. The biggest danger is **not a hard failure**; it is **a clean-looking, misleading CLI**.

**Top 3 risks**
1. **Dependency drift:** `07-03` relies on `07-02` behavior without declaring or verifying it.
2. **Misleading classify summaries:** `need review` is not clearly the number users think it is.
3. **Incomplete failure semantics:** exit code `0` may still happen in effectively failed runs.

**Recommended actions**
1. **Block execution on verified prerequisites.** Update `depends_on` to include `07-02`, and verify the codebase actually has `GenerateResult.filtered`, `generate_all(regenerate=...)`, and generator-side API-key enforcement.
2. **Define summary semantics before wiring strings.** Decide whether `need review` means “newly classified low-confidence” or “all encountered low-confidence,” then compute that intentionally.
3. **Do not silently default missing counters to zero.** Honest reporting should fail loudly on broken contracts, or use a public summary object instead of private attrs.
4. **Tighten D-12.** Explicitly specify whether “no cache” and “all articles failed” are exit-1 states.
5. **Narrow the config error mapping.** Avoid rewriting every `ValueError` as missing `ANTHROPIC_API_KEY`.
6. **Test the contract edges, not just formatting.** The highest-value tests here are the ones that prove `07-03` actually matches the real generator/classifier behavior on the branch it will run on.

**Open questions**
- Is `07-03` allowed to proceed before `07-02` lands, or should it be strictly ordered?
- Should cached low-confidence classifications count toward `need review`?
- Should `generate` return exit `1` when every attempted article fails, even if the process itself stayed up?
- Is “no classified input to generate” a no-op success or a total pipeline failure?

**What the plan does well**
- It keeps the phase focused on the CLI surface instead of re-implementing generator logic here.
- It follows the repo’s lazy-import CLI pattern.
- It correctly distinguishes partial failures from config/setup failures at a high level.
- It preserves `run` default behavior by not making regeneration implicit.