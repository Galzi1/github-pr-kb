# Risk Review: 07-01-PLAN.md

**Overall risk level: Moderate.** `07-01-PLAN.md` is directionally good, but it has **two high-priority plan defects** that should be fixed before execution: it targets the **wrong file/contract for `GenerateResult`**, and its **test/verification story is internally inconsistent**.

## 1. Plan Summary

**Purpose:** establish the Phase 7 foundation by fixing classifier failure handling, self-healing the classification index, and adding config/result-model support needed by later generator and CLI work.

**Key components touched:** `classifier.py`, `config.py`, `generator.py` / `GenerateResult`, `models.py`, `tests/test_classifier.py`, `tests/test_config.py`, `tests/test_generator.py`, and indirectly `tests/test_cli.py`.

**Plan's stated assumptions:**
- D-07/D-08 can be completed inside `classifier.py`.
- New settings belong in `config.py`.
- `GenerateResult` should be extended in `models.py`.
- Task 2 covers classifier fixes **and** new config fields.
- Verifying `test_classifier.py` and `test_generator.py` is sufficient.

**Theory of success:** if classifier failures stop polluting the index, stale failures are pruned on load, config exposes new knobs, and the generation result model can represent `filtered`, then Plans 02 and 03 can build synthesis and honest CLI reporting safely on top.

## 2. Assumptions & Evidence

| ID | Assumption | Explicit? | Evidence | Status | Blast radius if wrong | How to test/resolve |
|---|---|---:|---|---|---|---|
| A1 | `GenerateResult` lives in `models.py` and should be changed there | Explicit | Live code defines `GenerateResult` in `src\github_pr_kb\generator.py:87-95`; `models.py` does not contain it | **False** | High: executor edits wrong file; downstream tests/imports drift | Decide ownership now. **Recommended:** keep `GenerateResult` in `generator.py` for 07-01 and update the plan accordingly |
| A2 | Plan 01 does not need generator/CLI-adjacent updates | Implicit | `tests\test_generator.py` and `tests\test_cli.py` import `GenerateResult` from `github_pr_kb.generator` | **Weak** | High: changing/moving the type breaks later surfaces or forces unplanned refactor | If moving the type is intentional, explicitly add `generator.py` and `tests/test_cli.py` import rewiring to the plan |
| A3 | Task 2 covers "new config fields" | Explicit | Task 2 names `tests/test_config.py`, but the action and acceptance criteria only add classifier tests | **False/incomplete** | High: config fields may ship untested while the plan claims coverage | Add concrete `tests/test_config.py` cases and include them in verification |
| A4 | Current verification is enough | Explicit | Verification runs `tests/test_classifier.py tests/test_generator.py`, not `tests/test_config.py` | **False/incomplete** | Medium-High: plan can "pass" without validating new settings | Update `<verify>`, `<verification>`, and success criteria |
| A5 | Fixing `JSONDecodeError` is sufficient to harden classifier output handling | Implicit | Current code can still fail on parseable-but-invalid JSON, e.g. non-float `confidence` | **Partially justified** | Medium: malformed Claude output can still crash classification | Either expand scope to handle invalid parsed payloads, or mark it explicitly out of scope |

## 3. Ipcha Mistabra - Devil's Advocacy

### Inversion test

The plan says this is a clean "foundation" change. **The opposite is more likely:** this plan will leak into generator and CLI contracts unless the `GenerateResult` ownership issue is resolved first. Right now the plan pretends the result model is isolated in `models.py`, but the repository treats it as a generator-local contract.

### Little boy from Copenhagen

A new engineer following this plan literally would:
1. edit `models.py`,
2. wonder why `GenerateResult` is still imported from `generator.py`,
3. pass some tests but leave the codebase conceptually split.

That is exactly the kind of plan drift that creates messy follow-on fixes in later phases.

### Failure of imagination

The plan assumes "bad classifier output" means invalid JSON. A credible failure mode is **valid JSON with invalid schema**:

```json
{"category": "other", "confidence": "high", "summary": []}
```

That bypasses the D-07 fix but can still explode at `float(...)` / `str(...)` handling. If the phase goal is "stop classifier garbage/failure modes from poisoning the pipeline," this is a gap.

## 4. Risk Register

| Risk ID | Category | Description | Trigger | Probability | Severity | Priority | Detection | Mitigation | Contingency | Assumption link |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 | Technical | Plan edits `models.py` for `GenerateResult`, but the live contract is in `generator.py` | Executor follows Task 1 literally | High | High | **High** | Import/test failures, duplicate type definitions, mismatched docs | **Fix the plan now**: either keep the type in `generator.py` or explicitly plan the move and all rewires | If already implemented wrongly, revert to single ownership and repair imports/tests | A1, A2 |
| R2 | Testing | Task 2 claims config-field coverage but never specifies config tests | Execution finishes with only classifier tests added | High | High | **High** | `tests/test_config.py` unchanged; verification still green | Add explicit config tests for `anthropic_generate_model` and `min_confidence`; run them | If missed, add a follow-up patch before Phase 02 | A3, A4 |
| R3 | Planning hygiene | Frontmatter/task metadata disagree on touched files (`tests/test_generator.py` vs `tests/test_config.py`) | GSD executor or reviewer relies on metadata | Medium | Medium | **Medium** | Confusing diffs; review comments about "unexpected files" | Align `files_modified`, task file lists, and acceptance criteria | Document deviation if execution already started | A2, A3 |
| R4 | Reliability | Classifier still crashes on parseable-but-invalid model output | Claude returns schema-wrong JSON | Medium | Medium-High | **Medium-High** | Runtime exception during classify; partial pipeline abort | Add a narrow guard/test for invalid parsed fields, or explicitly defer it | Catch and count as failed in a follow-up patch | A5 |
| R5 | Operational | New env vars are added but not documented/discoverable | Users try Phase 02/03 without knowing new knobs exist | Medium | Medium | **Medium** | Confusion, missing config usage, support churn | Update `.env.example` and possibly README when introducing new settings | If deferred, capture as explicit follow-up in later plan | A3 |

## 5. Verdict & Recommendations

**Overall assessment:** the plan is **sound on the classifier fix**, but **not yet execution-safe as written** because its file ownership and verification details drift from the real codebase.

**Top 3 risks:**
1. **Wrong `GenerateResult` location in the plan**
2. **Task 2 / verification inconsistency around config tests**
3. **Malformed-but-parseable classifier output remains unaddressed**

**Recommended actions before executing 07-01:**
1. **Fix `GenerateResult` ownership in the plan.**  
   **Recommended:** keep it in `src\github_pr_kb\generator.py` for this phase, because that matches the live code and existing tests.  
   If you intentionally want to move it to `models.py`, then the plan must also add:
   - `src\github_pr_kb\generator.py`
   - `tests\test_cli.py`
   - any import rewiring acceptance criteria

2. **Make Task 2 internally consistent.**  
   Right now it says "classifier fixes and new config fields" but only specifies classifier tests. Add explicit `tests/test_config.py` cases such as:
   - settings accepts `ANTHROPIC_GENERATE_MODEL`
   - settings parses `MIN_CONFIDENCE` as `float`

3. **Fix verification commands and success criteria.**  
   Include `tests/test_config.py` anywhere the plan currently verifies only classifier/generator tests.

4. **Optionally harden classifier malformed-output handling.**  
   Either:
   - add one test/guard for parseable-but-invalid JSON, or
   - mark that case as explicitly out of scope so later reviewers don't assume it was solved here.

5. **Keep synthesis concerns out of 07-01.**  
   Things like prompt truncation and `messages.parse()` still belong in the later generator plan, not this one.

**Open questions:**
- Is moving `GenerateResult` to `models.py` intentional, or was that copied from stale research context?
- Should documenting `ANTHROPIC_GENERATE_MODEL` and `MIN_CONFIDENCE` be part of 07-01 or deferred?
- Do you want D-07 scoped strictly to JSON decode failures, or to all malformed classifier payloads?

**What the plan does well:**
- The D-07 fix is precise and correctly prevents cache poisoning.
- The D-08 self-healing approach is elegant and low-cost.
- The phase split itself is sensible: foundation first, synthesis second, CLI third.

**Must-change items in `07-01-PLAN.md`:**
1. Correct the `GenerateResult` file/contract target.
2. Align `files_modified`, task file lists, and acceptance criteria.
3. Add explicit config tests and include them in verification.
