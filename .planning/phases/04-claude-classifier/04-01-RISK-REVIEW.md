# Plan Risk Review: 04-01 (Classification Data Contracts & Test Scaffolds)

**Reviewed:** 2026-04-05
**Plan:** `.planning/phases/04-claude-classifier/04-01-PLAN.md`
**Overall Risk Level:** Low (with one critical clarification needed)

---

## 1. Plan Summary

**Purpose:** Establish the Pydantic data contracts (`ClassifiedComment`, `ClassifiedFile`, `CategoryLiteral`) and test infrastructure (conftest env vars, test scaffolds) needed before the actual classifier implementation in Plan 02.

**Key components touched:** `models.py` (new types), `config.py` (new field), `conftest.py` (env var), `test_classifier.py` (new file).

**Theory of success:** By separating type definitions and test scaffolds from the classifier implementation, Plan 02 can be pure TDD GREEN phase -- just making pre-written tests pass.

**Stated assumptions:** Existing imports (`datetime`, `Literal`) suffice for new models. `str | None = None` avoids breaking extract-only users. Tests will fail with ImportError until Plan 02, which is intentional.

---

## 2. Assumptions & Evidence

| # | Assumption | Explicit? | Justified? | Blast Radius if Wrong |
|---|-----------|-----------|------------|----------------------|
| A1 | `Literal` is already imported in `models.py` | Explicit | **Yes** -- verified: line 3 imports `Literal` | Low -- trivial fix |
| A2 | `datetime` is already imported in `models.py` | Explicit | **Yes** -- verified: line 2 imports `datetime` | Low -- trivial fix |
| A3 | `ConfigDict` is already imported in `models.py` | Implicit | **Yes** -- verified: line 5 imports it | Low |
| A4 | Making `anthropic_api_key: str | None = None` won't break existing tests | Explicit | **Yes** -- `None` default means no env var needed. Module-level `Settings()` will succeed without it | None |
| A5 | The conftest `os.environ.setdefault` at module level runs before any `from github_pr_kb import ...` in test files | Implicit | **Mostly justified** -- pytest loads `conftest.py` before test modules during collection. However, this depends on import ordering. | **Structural** -- if wrong, all tests fail at collection |
| A6 | `anthropic.types.Message` is constructible with positional/keyword args from the SDK without a live API key | Explicit | **Yes** -- research doc says verified via introspection | Low -- affects only test mocks |
| A7 | The 7 test functions will be collectible by pytest even though they import from a module (`classifier.py`) that doesn't yet export `PRClassifier` | **Critical implicit assumption** | **Questionable** -- see Phase 3 analysis below | **Foundational** -- if tests fail to collect, the verify step fails |

### Deep Dive on A7

The plan says tests "will FAIL initially (RED phase) because `classifier.py` is still a stub." But the verify step is:
```
.venv/Scripts/python.exe -m pytest tests/test_classifier.py --collect-only -q
```

`--collect-only` **does** import the test file. If the test file has `from github_pr_kb.classifier import PRClassifier` at the **module level**, collection itself will fail with `ImportError`, not just the test execution. The plan's action says each test should "Import and instantiate `PRClassifier` from `github_pr_kb.classifier`" -- if this import is inside the test function body, collection succeeds (import error only at runtime). If it's at the top of the file, collection fails.

**This is the single most important ambiguity in the plan.** The plan text in Task 3 doesn't specify whether the import should be at module level or inside each test function.

---

## 3. Ipcha Mistabra -- Devil's Advocacy

### 3a. The Inversion Test

**Plan claim:** "Separating data contracts from implementation makes Plan 02 cleaner."

**Inversion:** Separating them makes Plan 02 *harder* because the data contracts are now frozen before the implementation reveals what they actually need. If Plan 02 discovers that `ClassifiedComment` needs an additional field (e.g., `body_hash` for tracing, or `model_used` for audit), the developer must go back and modify models already committed, breaking the clean "wave 1 ships, wave 2 builds on it" narrative.

**Assessment:** This is a real but **low-severity** risk. The models are based on locked decisions (D-01 through D-06 in CONTEXT.md), so the field set is well-defined. Adding a field to a Pydantic model in a future commit is trivial. The inversion is not compelling enough to change the approach.

### 3b. The Little Boy from Copenhagen

**A new engineer reading this plan** would ask: "Why does Task 2 say to rename `_set_dummy_github_token` to `_set_dummy_env_tokens`, but that rename would break any test that depends on the old fixture name?"

Checking the conftest: the fixture is `autouse=True`, so no test references it by name. The rename is safe. But the plan should have noted this explicitly.

**An SRE at 3 AM** perspective is irrelevant for this plan -- it's purely data contract and test scaffolding with no runtime behavior.

### 3c. Failure of Imagination

**Scenario:** The `anthropic` SDK 0.84.0's `anthropic.types.Message` constructor signature changes between 0.84.0 and a future version, making `make_mock_message()` break silently (e.g., a required field is added). Since `pyproject.toml` declares `anthropic>=0.84.0`, a `uv sync` could pull a newer version.

**Assessment:** Low probability in the 30-day validity window. The research doc notes the SDK is stable for `messages.create()`. But the test mock construction goes deeper into SDK internals (`anthropic.types.Message`, `TextBlock`, `Usage`). If the SDK adds a required field to `Usage` or `Message`, the mock breaks.

**Mitigation already present:** The `make_mock_message` helper centralizes construction, so only one place needs updating.

---

## 4. Risk Register

| ID | Category | Description | Trigger | Prob | Severity | Priority | Detection | Mitigation | Contingency | Assumption |
|----|----------|-------------|---------|------|----------|----------|-----------|------------|-------------|------------|
| R1 | Technical | Test collection fails if `from github_pr_kb.classifier import PRClassifier` is at module level in `test_classifier.py` | `pytest --collect-only` runs on Wave 1 (before Plan 02 implements PRClassifier) | **High** (plan text is ambiguous) | **High** (verify step fails; plan declared broken) | **Critical** | `pytest --collect-only` will show `ImportError` | Ensure the import is inside each test function body, or use `pytest.importorskip`, or add a minimal `PRClassifier` stub to `classifier.py` | Move imports inside test functions after collection failure | A7 |
| R2 | Technical | Conftest fixture rename from `_set_dummy_github_token` to `_set_dummy_env_tokens` could cause confusion if other conftest files or fixtures reference the old name | Rename is committed | **Low** (fixture is `autouse`, unnamed references) | **Low** | **Low** | `pytest --collect-only` | Grep for the old name before renaming | Revert rename | A5 |
| R3 | Schedule | Plan 02 discovers `ClassifiedComment` needs additional fields not in the current spec | Implementation of classifier logic in Plan 02 | **Low** (decisions are locked) | **Low** (adding a Pydantic field is trivial) | **Low** | Plan 02 code review | Accept that models may evolve; this is normal | Add field in Plan 02 commit | -- |
| R4 | Technical | `anthropic` SDK version drift breaks `make_mock_message` constructor | `uv sync` pulls a version > 0.84.0 with new required fields on `Message` or `Usage` | **Low** | **Medium** (all classifier tests break) | **Medium** | CI test failures | Pin `anthropic==0.84.0` or add bounds in pyproject.toml | Update `make_mock_message` to match new SDK signature | A6 |
| R5 | Technical | `conftest.py` module-level `setdefault` may not execute before a test file that does `from github_pr_kb.config import settings` if pytest discovers files in unexpected order | Edge case with pytest plugins or `-p no:conftest` | **Very Low** | **High** (all tests fail) | **Low** (Known Unknown) | `pytest --collect-only` error referencing `ANTHROPIC_API_KEY` | This is already mitigated by making the field `str | None = None` -- even without the env var, settings loads fine | Not needed -- mitigation is sufficient | A5 |

### Known Knowns
- R2, R3: Well-understood, low impact, mitigations trivial.

### Known Unknowns
- R1: The plan is ambiguous about import placement. Resolvable by reading the plan carefully during execution.
- R4: SDK version drift is a known category of risk but timing is unknown.

### Unknown Unknowns
- R5 was surfaced by Ipcha Mistabra analysis. The interaction between `str | None = None` and the conftest `setdefault` creates a belt-and-suspenders defense, which actually *eliminates* R5 as a real concern. This is a strength of the plan.

---

## 5. Verdict & Recommendations

**Overall Risk Level: Low** -- with one critical clarification needed (R1).

### Top 3 Risks

1. **R1 (Critical): Module-level import of `PRClassifier` in test file will break collection.** The plan says tests should "Import and instantiate `PRClassifier`" but doesn't specify that this must happen inside the test function body (not at module level). If the executor puts `from github_pr_kb.classifier import PRClassifier` at the top of `test_classifier.py`, `pytest --collect-only` will fail with `ImportError` and the plan's own verify step won't pass.

2. **R4 (Medium): SDK version drift.** Minor risk given the 30-day research validity window, but worth noting.

3. **R3 (Low): Model field set may need revision in Plan 02.** Acceptable risk.

### Recommended Actions

1. **Before execution:** Clarify that `PRClassifier` imports must be **inside test function bodies**, not at module level. Alternatively, add a minimal stub to `classifier.py`:
   ```python
   class PRClassifier:
       """Stub -- implemented in Plan 02."""
       pass
   ```
   This would let top-level imports succeed during collection.

2. **No other blockers.** The plan is well-researched, scoped appropriately, and the `str | None = None` decision for `anthropic_api_key` is the right call -- it avoids breaking extract-only users while deferring validation to the classifier constructor.

### Open Questions

- The plan's Task 3 action section mentions `test_cache_hit_no_api_call` should "Call classify on the same cache_dir twice" -- but if `PRClassifier` doesn't exist yet, how is the test supposed to be structured? This is fine as long as imports are inside the function body, but the plan should be explicit.

### What the Plan Does Well

- **Belt-and-suspenders on config:** Making `anthropic_api_key` optional in Settings *and* adding the conftest `setdefault` means neither path alone is a single point of failure.
- **Clean separation of concerns:** Types in Wave 1, implementation in Wave 2 is a sound TDD strategy.
- **Thorough research backing:** Every decision references a locked decision (D-01 through D-07) or a verified code pattern. The research document verified SDK constructors by actually running code in the venv.
- **Realistic verify commands:** Each task has a concrete automated verification command, not just "looks good."

---

**Bottom line:** This plan is solid. Fix the import placement ambiguity in R1 before executing, and it should go cleanly.
