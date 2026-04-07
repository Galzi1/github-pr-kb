# Phase 7: Fix Article Generation Quality - Research

**Researched:** 2026-04-07
**Domain:** Python / Anthropic SDK / Click CLI / Pydantic Settings
**Confidence:** HIGH

## Summary

Phase 7 replaces the raw-comment-copy generator with a Claude-powered synthesis pipeline, removes
the fake classification-failure fallback record that poisons the KB, and fixes three separate CLI
output accuracy issues. All work touches existing code that has already been read and understood;
no new libraries are required.

The Anthropic Python SDK (0.84.0, already installed) supports all required patterns — the same
`client.messages.create()` call used in `PRClassifier` is the correct API for `KBGenerator`.
The five category-specific templates (D-02) map cleanly onto Claude system-prompt instructions
with structured section headings. The min-confidence threshold (D-14) and `--regenerate` flag
(D-16) are purely new feature additions with no external dependencies.

The existing test suite (83 tests, 83% coverage) must continue to pass. Existing
`test_article_body_contains_comment` will break by design once synthesis replaces raw-copy, so it
must be updated. Several other generator tests will need mock-patching to avoid live API calls.

**Primary recommendation:** Follow the canonical refs from CONTEXT.md exactly. Replace `_build_article()` with a Claude synthesis call, remove the fallback record from `_classify_comment()`, add `_load_index()` filtering, extend `GenerateResult` with `filtered`, add two settings fields, update CLI summary strings, add `--regenerate` flag, and update tests.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Article Synthesis
- **D-01:** Claude rewrites each comment into a structured KB article during the `generate` step (not classify). KBGenerator calls Claude to synthesize each article at generation time.
- **D-02:** Category-specific article templates:
  - `gotcha` → Symptom / Root Cause / Fix or Workaround
  - `architecture_decision` → Context / Decision / Consequences
  - `code_pattern` → Pattern / When to Use / Example
  - `domain_knowledge` → Context / Key Insight / Implications
  - `other` → Context / Key Insight / Recommendation (generic)
- **D-03:** Synthesis input is the raw comment body + PR title. No other PR context.
- **D-04:** No raw comment preserved in the synthesized article — purely Claude-synthesized. Raw comment remains in cache JSON for provenance.
- **D-05:** Manifest-based dedup — existing `manifest[comment_id]` check is sufficient. No separate synthesis cache.
- **D-06:** Separate `ANTHROPIC_GENERATE_MODEL` env var for the generator model. Allows smarter model for synthesis while keeping Haiku for classification.

#### Classification Failures
- **D-07:** Remove fake fallback record on JSON parse failure. Log warning, increment `_failed_count`, return `None`.
- **D-08:** On startup, `PRClassifier._load_index()` filters out entries where `summary == 'classification failed'`. Self-healing.
- **D-09:** `classify_pr()` already overwrites classified files — cleaning index is sufficient.

#### CLI Output Accuracy
- **D-10:** Generate command reports: new / skipped / filtered / failed breakdown.
- **D-11:** Classify command reports: new / cached / need review / failed breakdown.
- **D-12:** Exit code 0 for partial failures, exit code 1 only for total pipeline failure.

#### Low-Value Filtering
- **D-13:** All categories generate articles — no category-based filtering.
- **D-14:** Min confidence threshold 0.5 (configurable via `MIN_CONFIDENCE`). >= 0.75 = normal, 0.50–0.74 = article + [review] tag, < 0.50 = filtered out. Filtered count in CLI output.

#### Synthesis Error Handling
- **D-15:** On synthesis failure skip the article, do not write, do not add to manifest. No fallback to raw comment copy.

#### Existing KB Cleanup
- **D-16:** Add `--regenerate` flag to `generate`. Clears manifest and deletes existing article files, re-synthesizes all.

#### Generator API Key
- **D-17:** Generate command requires `ANTHROPIC_API_KEY` (or generate-specific model key). Fails fast with clear error if missing.

### Claude's Discretion
- Synthesis prompt engineering — exact prompt wording, max_tokens, and temperature
- Error message wording for missing API key in generate command
- How `--regenerate` cleans up existing files (delete category dirs vs. individual files)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

---

## Standard Stack

### Core (already installed — no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.84.0 | Claude API client — synthesis calls | Already used in classifier.py; same client pattern |
| pydantic-settings | (existing) | Settings with env var parsing | Already used in config.py |
| click | (existing) | CLI flags (`--regenerate`) | Already used for all CLI commands |
| pytest | (existing) | Test coverage | Project standard |

**No new packages required.** All libraries are already present in the venv.

### Verified versions
```
anthropic   0.84.0   (confirmed via .venv/Scripts/python.exe -c "import anthropic; print(anthropic.__version__)")
```

### Alternatives Considered
None applicable — all decisions are locked.

---

## Architecture Patterns

### Pattern 1: Claude API call in KBGenerator (mirrors PRClassifier)

`PRClassifier.__init__` initializes `self._client = Anthropic(api_key=..., max_retries=2)`.
`KBGenerator.__init__` must do exactly the same. The existing lazy-import pattern from
`PRClassifier` applies: import `settings` inside `__init__` (not at module level) to prevent
import-time `ValidationError` in tests.

```python
# Source: src/github_pr_kb/classifier.py (existing pattern to replicate)
from github_pr_kb.config import settings       # lazy — inside __init__
if api_key is None:
    api_key = settings.anthropic_generate_model_api_key  # new field
if api_key is None:
    raise ValueError("ANTHROPIC_API_KEY is required for generate...")
self._client = Anthropic(api_key=api_key, max_retries=2)
```

### Pattern 2: Category-specific synthesis prompts

The synthesis system prompt should define the category template inline, selected by category
string at call time. A clean approach is a `dict[str, str]` mapping category → section headers,
used when building the user message. The system prompt stays generic; the section structure is
injected per-call.

```python
_CATEGORY_SECTIONS: dict[str, str] = {
    "gotcha": "## Symptom\n\n## Root Cause\n\n## Fix or Workaround",
    "architecture_decision": "## Context\n\n## Decision\n\n## Consequences",
    "code_pattern": "## Pattern\n\n## When to Use\n\n## Example",
    "domain_knowledge": "## Context\n\n## Key Insight\n\n## Implications",
    "other": "## Context\n\n## Key Insight\n\n## Recommendation",
}
```

The user prompt then includes: PR title, comment body, category, and the required section
headings. Claude is instructed to fill in each section.

### Pattern 3: _build_article replacement

Current `_build_article()` is synchronous and pure — it takes PR/comment/classification and
returns a `str`. The new version should keep the same signature but call the Anthropic API
instead of concatenating raw text.

The frontmatter block (lines 234–246 of generator.py) is preserved as-is. Only the body after
the title heading changes: instead of `comment.body` + optional diff_hunk, the body is the
Claude-synthesized text. The diff_hunk, if present, should be appended after the synthesis body
(it's code context, not prose).

### Pattern 4: GenerateResult extension

Add a `filtered: int = 0` field to `GenerateResult`. The model uses `ConfigDict(extra="ignore")`
already, so existing serialized results will not break deserialization.

```python
class GenerateResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    written: int
    skipped: int
    filtered: int = 0      # NEW — comments below MIN_CONFIDENCE threshold
    failed: list[dict[str, str]]
```

### Pattern 5: Settings extension

Add two fields to `Settings` in config.py:

```python
anthropic_generate_model: str | None = None   # ANTHROPIC_GENERATE_MODEL env var
min_confidence: float = 0.5                   # MIN_CONFIDENCE env var
```

`min_confidence` should be a `float` (not `str`) so pydantic-settings parses the env var as a
number directly. The default 0.5 matches D-14.

### Pattern 6: _classify_comment fix (D-07 and D-08)

Current lines 162–167 in classifier.py:
```python
result = {"category": "other", "confidence": 0.0, "summary": "classification failed"}
```
Replace with:
```python
self._failed_count += 1
return None
```
The index must NOT be updated on parse failure (it currently is, since the code falls through to
line 176 after the except block). Confirm the early return prevents index write.

For D-08, in `_load_index()`, after `json.loads()` succeeds, filter the returned dict:
```python
data = {k: v for k, v in data.items() if v.get("summary") != "classification failed"}
```

### Pattern 7: --regenerate flag

Add as a boolean Click option on the `generate` command:
```python
@click.option("--regenerate", is_flag=True, help="Re-synthesize all articles from scratch.")
```

In `_run_generate()`, pass `regenerate=True/False` to `KBGenerator.generate_all()` or to
`__init__`. The cleanest approach is to call a new `_reset_kb()` method inside `generate_all()`
when the flag is set. `_reset_kb()` deletes per-category directories (not individual files) and
clears `self._manifest`. This is simpler than tracking individual files.

### Pattern 8: CLI summary string updates

**Current `_run_generate()` output (line 131):**
```
f"Generated {total} articles ({result.written} new, {result.skipped} skipped)."
```
**New output (D-10):**
```
f"Generated {result.written} new, {result.skipped} skipped, {result.filtered} filtered, {len(result.failed)} failed."
```

**Current `_run_classify()` output (line 117):**
```
f"Classified {total} comments ({classified} new, {cached} cached)."
```
**New output (D-11):**
```
f"Classified {classified} new, {cached} cached, {review} need review, {failed} failed."
```
The `_review_count` and `_failed_count` attrs already exist on PRClassifier.

### Anti-Patterns to Avoid

- **Writing raw comment text to synthesized articles:** D-04 forbids this. The synthesis result
  from Claude must replace the body entirely — do not fall back to `comment.body` on any soft
  error path.
- **Adding synthesized articles to manifest on failure:** D-15 requires that failed synthesis
  never adds to manifest. The comment will be retried on the next run.
- **Calling `_save_index()` after a failed classification:** Current code path after the except
  block falls through to `self._index[h] = {...}` and `self._save_index()`. After D-07's fix, the
  early `return None` must precede both of these.
- **Module-level settings import in generator.py:** Follow the classifier pattern — import inside
  `__init__` to prevent import-time `ValidationError`.
- **Hardcoding the generate model:** Use `settings.anthropic_generate_model` with a sensible
  default (e.g., `"claude-haiku-4-5-20251001"` to match existing classifier default) when the
  env var is absent.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var parsing for `MIN_CONFIDENCE` | Custom `os.getenv` float parsing | pydantic-settings `float` field | Validates, type-converts, handles `.env` file |
| Anthropic API retries | Custom retry loop | `Anthropic(max_retries=2)` | SDK handles rate-limit backoff |
| Atomic file writes | Direct `open()` | Existing `_write_atomic()` | Prevents partial writes on crash |
| Slug deduplication | New slug cache | Existing `_resolve_slug()` | Already handles collision detection |

---

## Runtime State Inventory

This is a code-only phase (no rename/rebrand). No runtime state inventory required.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| anthropic SDK | Article synthesis | Yes | 0.84.0 | — |
| pydantic-settings | New settings fields | Yes | (existing) | — |
| click | --regenerate flag | Yes | (existing) | — |
| pytest | Test suite | Yes | (existing) | — |

No missing dependencies. All required packages are installed in the project venv.

---

## Common Pitfalls

### Pitfall 1: Early return missing before index write in _classify_comment
**What goes wrong:** After removing the fake fallback dict and returning `None`, if the code is
not restructured carefully, execution may still reach `self._index[h] = {...}` (line 176) and
`self._save_index()` (line 182), writing a partial/wrong index entry.
**Why it happens:** The original code used `result = {fallback}` and then continued; the parse
failure was not a hard exit. Simply deleting lines 162–167 without adding `return None` leaves
the try/except body falling through.
**How to avoid:** After the `except json.JSONDecodeError` block, the new code must be:
`self._failed_count += 1; return None` — both statements, before `raw_category = result.get(...)`.
**Warning signs:** Test checking that `_failed_count` increments but classification-index stays
clean.

### Pitfall 2: Test test_article_body_contains_comment breaks by design
**What goes wrong:** `test_article_body_contains_comment` asserts `"Always copy context before
modifying"` (the raw comment body) appears in the generated article. After D-04, the raw comment
body is not in the article — Claude rewrites it.
**Why it happens:** The test was written for the old raw-copy behavior.
**How to avoid:** Update or replace the test with a mock-based assertion that the Claude API was
called and the synthesis result is used as the article body.

### Pitfall 3: KBGenerator tests hitting real Anthropic API
**What goes wrong:** After adding `self._client = Anthropic(...)` to `KBGenerator.__init__`, any
test that instantiates `KBGenerator` will make real API calls if not mocked, causing slow tests
and cost.
**Why it happens:** `test_generate_creates_category_subdirs`, `test_article_written_to_category_subdir`,
and ~15 other generator tests all call `generate_all()` which now invokes Claude.
**How to avoid:** Two options: (a) patch `anthropic.Anthropic` at the test level, or (b) add an
`anthropic_client` parameter to `KBGenerator.__init__` (like `PRClassifier`'s `api_key`
parameter) so tests can inject a mock. Option (b) aligns with the established PRClassifier
pattern and is preferable.
**Warning signs:** Tests suddenly taking 10+ seconds or failing with auth errors in CI.

### Pitfall 4: MIN_CONFIDENCE filtering vs. needs_review tag conflict
**What goes wrong:** D-14 says confidence 0.50–0.74 produces article + [review] tag. But the
existing `ClassifiedComment.needs_review` field already fires when `confidence < 0.75`. The
filtering check (< 0.50) must happen in `_process_classified_file`, before the existing
`needs_review`-based tagging in `_write_article`. The article must be skipped entirely at the
0.50 threshold, not just tagged.
**How to avoid:** Add the confidence filter check at the start of the per-classification loop in
`_process_classified_file`, incrementing `self._filtered` and `continue`-ing. The existing
`needs_review` frontmatter field and [review] index tag continue working for 0.50–0.74 range.

### Pitfall 5: --regenerate deletes files without atomic safety
**What goes wrong:** If the process crashes mid-cleanup (rare but possible), the KB is partially
deleted with no manifest, leaving an inconsistent state.
**How to avoid:** Clear the manifest and write it to disk first (empty `{}`). Then delete files.
If interrupted after manifest clear but before file deletion, the next run will re-synthesize all
articles (manifest is empty). Partially deleted file tree is harmless since `generate_all`
re-creates all category dirs.

### Pitfall 6: ANTHROPIC_GENERATE_MODEL vs ANTHROPIC_MODEL confusion
**What goes wrong:** If `anthropic_generate_model` falls back to `anthropic_model` silently,
users who set `ANTHROPIC_MODEL=haiku` for classification unexpectedly get haiku for synthesis too,
defeating D-06's purpose.
**How to avoid:** `KBGenerator` reads `settings.anthropic_generate_model` first, then falls back
to a hard-coded default model constant (not `settings.anthropic_model`). The two model settings
should be fully independent.

---

## Code Examples

### Synthesis call pattern (adapting existing classifier pattern)

```python
# Source: classifier.py lines 145–157 (existing pattern)
try:
    response = self._client.messages.create(
        model=self._model,
        max_tokens=1024,          # synthesis needs more tokens than classification
        system=SYNTHESIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )
except anthropic.APIError as exc:
    logger.warning("API error synthesizing comment %d: %s", comment.comment_id, exc)
    self._failed.append({"file": ..., "reason": type(exc).__name__, "detail": str(exc)})
    return None                   # D-15: do not write article, do not add to manifest
```

### Settings fields (pydantic-settings pattern)

```python
# Source: config.py (existing pattern)
class Settings(BaseSettings):
    ...
    anthropic_generate_model: str | None = None  # ANTHROPIC_GENERATE_MODEL env var
    min_confidence: float = 0.5                  # MIN_CONFIDENCE env var
```

### Classification index cleanup (D-08)

```python
# In PRClassifier._load_index(), after json.loads():
data = {k: v for k, v in data.items() if v.get("summary") != "classification failed"}
logger.debug("Loaded %d valid index entries (failed entries pruned)", len(data))
return data
```

### Confidence threshold filter in _process_classified_file (D-14)

```python
for classification in classified_file.classifications:
    key = str(classification.comment_id)
    if key in self._manifest:
        self._skipped += 1
        continue
    if classification.confidence < self._min_confidence:   # from settings
        self._filtered += 1
        continue
    # ... proceed to synthesize and write article
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | pyproject.toml (inferred from existing use) |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_generator.py tests/test_classifier.py tests/test_cli.py -x -q` |
| Full suite command | `.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_classifier_integration.py --ignore=tests/test_extractor_integration.py -q` |

### Phase Requirements → Test Map

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|--------------|
| D-01/D-04 | Article body is Claude-synthesized, not raw comment | unit (mock) | pytest tests/test_generator.py::test_article_body_is_synthesized -x | No — Wave 0 |
| D-02 | Category sections appear in synthesized article | unit (mock) | pytest tests/test_generator.py::test_category_sections_in_article -x | No — Wave 0 |
| D-06 | KBGenerator uses ANTHROPIC_GENERATE_MODEL | unit | pytest tests/test_generator.py::test_generate_model_env_var -x | No — Wave 0 |
| D-07 | JSON parse failure returns None, no index write | unit | pytest tests/test_classifier.py::test_parse_failure_returns_none -x | No — Wave 0 |
| D-08 | _load_index filters classification-failed entries | unit | pytest tests/test_classifier.py::test_load_index_filters_failed -x | No — Wave 0 |
| D-10 | Generate CLI reports filtered count | unit | pytest tests/test_cli.py::test_generate_cli_filtered_count -x | No — Wave 0 |
| D-11 | Classify CLI reports failed count | unit | pytest tests/test_cli.py::test_classify_cli_failed_count -x | No — Wave 0 |
| D-14 | Comments below 0.5 confidence are filtered | unit | pytest tests/test_generator.py::test_low_confidence_filtered -x | No — Wave 0 |
| D-14 | Comments 0.50–0.74 get [review] tag | unit (existing) | pytest tests/test_generator.py::test_needs_review_in_frontmatter -x | Yes |
| D-15 | Synthesis failure: no article written, not in manifest | unit (mock) | pytest tests/test_generator.py::test_synthesis_failure_skipped -x | No — Wave 0 |
| D-16 | --regenerate clears manifest and deletes articles | unit | pytest tests/test_generator.py::test_regenerate_flag -x | No — Wave 0 |
| D-17 | Generate fails fast without ANTHROPIC_API_KEY | unit | pytest tests/test_generator.py::test_generate_requires_api_key -x | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/Scripts/python.exe -m pytest tests/test_generator.py tests/test_classifier.py tests/test_cli.py -x -q`
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest tests/ --ignore=tests/test_classifier_integration.py --ignore=tests/test_extractor_integration.py -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

All new behavior requires new test functions. The existing test infrastructure is sound — only
new test functions need adding to existing test files. No new test files or framework config
needed.

- [ ] `tests/test_generator.py::test_article_body_is_synthesized` — D-01/D-04
- [ ] `tests/test_generator.py::test_category_sections_in_article` — D-02
- [ ] `tests/test_generator.py::test_generate_model_env_var` — D-06
- [ ] `tests/test_generator.py::test_low_confidence_filtered` — D-14
- [ ] `tests/test_generator.py::test_synthesis_failure_skipped` — D-15
- [ ] `tests/test_generator.py::test_regenerate_flag` — D-16
- [ ] `tests/test_generator.py::test_generate_requires_api_key` — D-17
- [ ] `tests/test_classifier.py::test_parse_failure_returns_none` — D-07
- [ ] `tests/test_classifier.py::test_load_index_filters_failed` — D-08
- [ ] `tests/test_cli.py::test_generate_cli_filtered_count` — D-10
- [ ] `tests/test_cli.py::test_classify_cli_failed_count` — D-11
- [ ] Update `tests/test_generator.py::test_article_body_contains_comment` — no longer valid after D-04; replace with mock-based synthesis assertion

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Article body = raw `comment.body` | Article body = Claude synthesis | Phase 7 | All existing articles become stale — use `--regenerate` |
| Fake fallback `{"category":"other","confidence":0.0}` on parse failure | Return `None`, increment `_failed_count` | Phase 7 | classification-failed-*.md files stop appearing |
| CLI generate summary: `Generated N articles (X new, Y skipped)` | Breakdown includes filtered count | Phase 7 | More informative output |

---

## Open Questions

1. **max_tokens for synthesis**
   - What we know: Classification uses 256 tokens. Synthesis produces multi-section articles.
   - What's unclear: Appropriate upper bound. 1024 tokens allows ~700 words of article body, which
     should be sufficient for structured KB articles.
   - Recommendation: Use 1024 as the default. This is Claude's discretion per CONTEXT.md.

2. **Temperature for synthesis**
   - What we know: Claude defaults to 1.0. Synthesis should produce factual, consistent output.
   - Recommendation: Use temperature=0.3 for consistency across runs (lower randomness). Claude's
     discretion per CONTEXT.md.

3. **Existing KB articles after phase ships**
   - What we know: The `--regenerate` flag (D-16) handles this.
   - What's unclear: Whether the planner should add a note in the CLI `--regenerate` help text
     recommending users run it after upgrading.
   - Recommendation: Add a note in `--regenerate` help: "Use after upgrading to re-synthesize all
     articles with the new Claude-powered pipeline."

---

## Project Constraints (from CLAUDE.md)

| Directive | Implication for This Phase |
|-----------|---------------------------|
| Run tests with `.venv/Scripts/python.exe -m pytest tests/` | All test commands must use this form |
| Never use `uv run pytest` | Avoid in all task instructions |
| Run `uv run ruff check src/ tests/ --fix --exit-non-zero-on-fix` after any `.py` change | Every task touching Python files ends with ruff |

**Additional project rules (from .claude/rules/):**
- `clean-code.md` — Functions should do one thing; minimal arguments; no magic numbers (use named
  constants for `MIN_CONFIDENCE` default, model name constant)
- `python-typing.md` — Use `str | None` not `Optional[str]`; `dict[str, str]` not `Dict[str, str]`;
  no `Any` without exhausting alternatives
- `ruff-after-python.md` — `uv run ruff check src/ tests/ --fix --exit-non-zero-on-fix` after
  every Python change

---

## Sources

### Primary (HIGH confidence)
- Direct code read: `src/github_pr_kb/classifier.py` — existing client init, API call pattern, index structure
- Direct code read: `src/github_pr_kb/generator.py` — `_build_article()`, `GenerateResult`, manifest dedup
- Direct code read: `src/github_pr_kb/cli.py` — `_run_generate()`, `_run_classify()`, `ConfigurationError`
- Direct code read: `src/github_pr_kb/config.py` — `Settings` fields pattern
- Direct code read: `src/github_pr_kb/models.py` — `GenerateResult` fields
- Direct code read: `tests/test_generator.py` — existing test coverage gaps
- Direct code read: `tests/test_cli.py` — existing CLI test patterns
- Runtime verification: `anthropic.__version__` = 0.84.0 in project venv
- Runtime verification: 83 tests pass, 83% coverage baseline

### Secondary (MEDIUM confidence)
- Anthropic SDK 0.84.0 `messages.create()` signature inferred from existing classifier.py usage
  (same SDK version, same call pattern)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified by reading actual source files and running python in venv
- Architecture: HIGH — all patterns are direct extrapolations of existing code in the same files
- Pitfalls: HIGH — derived from reading actual test failures, code structure, and decision
  interactions
- Test gaps: HIGH — derived from counting decisions against existing test function names

**Research date:** 2026-04-07
**Valid until:** Stable — no external dependencies that can drift; all findings based on local code
