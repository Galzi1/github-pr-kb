# Phase 04: Claude Classifier - Research

**Researched:** 2026-04-05
**Domain:** Anthropic Python SDK, content-hash dedup, classification prompt design, pytest mocking
**Confidence:** HIGH

## Summary

Phase 4 adds a classifier module that reads extracted PR comment cache files, classifies each comment via Claude API, and persists results in a parallel cache structure with a global content-hash index for cross-PR dedup. All locked decisions from the CONTEXT.md discussion (separate `classified-pr-N.json` files, one-call-per-comment, SHA-256 body hash index, `needs_review` flag at < 0.75 confidence) are directly implementable with the installed `anthropic==0.84.0` SDK and existing project patterns.

The Anthropic SDK is already installed (`anthropic>=0.84.0`, latest available is 0.89.0). The `messages.create()` API accepts a `system` prompt string plus `messages` list and returns a `Message` object whose content is a list of `TextBlock` items. Claude should return structured JSON in its text block; the classifier parses that with `json.loads()`. The existing `_write_cache_atomic` pattern from `extractor.py` (mkstemp + os.replace) must be reused verbatim for both `classified-pr-N.json` and `classification-index.json`.

Testing follows the established `unittest.mock.patch` pattern: patch `github_pr_kb.classifier.Anthropic` and return a real `anthropic.types.Message` object constructed from the SDK's Pydantic models (verified constructible without a live key). The `conftest.py` must be extended with a module-level `os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test...")` to prevent import-time `ValidationError` once `anthropic_api_key: str` is added to `Settings`.

**Primary recommendation:** Use `claude-3-5-haiku-latest` as the default model (cheapest, fast, sufficient for single-category classification). Return JSON with `{"category": "...", "confidence": 0.0-1.0, "summary": "one line"}` in a structured system-prompted response. Parse with `json.loads()` and fall back to `category="other"` / `confidence=0.0` on parse failure.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Classification results stored in `classified-pr-N.json` alongside `pr-N.json` in `.github-pr-kb/cache/`. Extraction and classification data stay independent.
- **D-02:** New `ClassifiedComment` Pydantic model fields: `comment_id`, `category`, `confidence`, `summary`, `classified_at`, `needs_review`.
- **D-03:** One comment per Claude API call. Simple, reliable, easy to cache and retry individually.
- **D-04:** SHA-256 hash of comment body for cross-PR dedup. Only truly identical comments share a result.
- **D-05:** Single `classification-index.json` maps `body_hash -> {category, confidence, summary, classified_at}`. Loaded once at start, checked before each API call, appended after each successful classification.
- **D-06:** `needs_review: bool` = `True` when `confidence < 0.75`.
- **D-07:** Classify command prints a summary: total classified, cache hits, how many need review.

### Claude's Discretion

- Prompt design (system prompt, output format, structured output vs free-text parsing)
- Claude model selection (haiku for cost, sonnet for quality)
- Error handling strategy for failed API calls (retry logic, partial failure behavior)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLASS-01 | User can classify PR comments into categories: architecture_decision, code_pattern, gotcha, domain_knowledge, other | `messages.create()` with system prompt + Literal type on `ClassifiedComment.category` |
| CLASS-02 | Each classification includes a confidence score; items below 75% threshold are flagged for review | `confidence: float` field; `needs_review = confidence < 0.75`; D-06 locked |
| CLASS-03 | Identical comments (matched by content hash) reuse cached classifications to minimize Claude API costs | SHA-256 on `body.encode("utf-8")` checked against `classification-index.json` before API call; D-04/D-05 locked |
| CLASS-04 | Classification output includes: original comment, category, confidence score, and one-line summary | `ClassifiedComment` model per D-02; `ClassifiedFile` wraps list of `ClassifiedComment` alongside `PRRecord` metadata |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.84.0 (installed) / 0.89.0 (latest) | Claude API calls | Already in pyproject.toml; SDK is stable |
| pydantic | >=2.12.5 | `ClassifiedComment`, `ClassifiedFile` models | Already used for all data models |
| pydantic-settings | >=2.13.1 | `anthropic_api_key` field in `Settings` | Already used in `config.py` |
| hashlib | stdlib | SHA-256 body hash | No dependency; deterministic |
| json | stdlib | JSON serialization + response parsing | Same as extraction cache layer |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| datetime | stdlib | `classified_at` timestamp | Consistent with `extracted_at` in `PRFile` |
| pathlib | stdlib | Cache file paths | Same pattern as `extractor.py` |
| logging | stdlib | Progress and cache-hit logging | Same `getLogger(__name__)` pattern |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Free-text JSON response | Tool use / structured outputs | Tool use API adds complexity; free-text JSON is sufficient given validated category Literal |
| claude-3-5-haiku-latest | claude-3-7-sonnet-latest | Sonnet 5-10x more expensive; haiku classification quality is adequate for 5-category task |
| json.loads() parse | pydantic model_validate_json | json.loads + manual field extraction is simpler; no schema definition needed for API response |

**Installation:** No new packages needed — `anthropic` is already in `pyproject.toml`.

**Version note:** Installed is 0.84.0; latest published is 0.89.0 (verified via `pip index versions`). The 0.84.0 API is stable for `messages.create()` — no version bump required for Phase 4.

---

## Architecture Patterns

### Recommended Project Structure

```
src/github_pr_kb/
├── models.py          # ADD: ClassifiedComment, ClassifiedFile models
├── config.py          # MODIFY: uncomment anthropic_api_key: str
├── classifier.py      # IMPLEMENT: Classifier class (stub exists)
└── extractor.py       # Reference only — no changes needed

tests/
├── conftest.py        # MODIFY: add ANTHROPIC_API_KEY setdefault
└── test_classifier.py # CREATE: new test file
```

### Pattern 1: One-Call-Per-Comment with Index Check

```python
# Source: D-03, D-04, D-05 from CONTEXT.md + verified SDK signature

import hashlib, json
from anthropic import Anthropic

def _body_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()

def _classify_comment(client: Anthropic, body: str, index: dict) -> dict:
    h = _body_hash(body)
    if h in index:
        return index[h]  # cache hit — zero API call

    response = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": body}],
    )
    result = json.loads(response.content[0].text)
    index[h] = result  # persist to in-memory index before returning
    return result
```

### Pattern 2: ClassifiedComment Pydantic Model

```python
# Source: D-02 from CONTEXT.md + existing models.py patterns

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

CategoryLiteral = Literal[
    "architecture_decision", "code_pattern", "gotcha", "domain_knowledge", "other"
]

class ClassifiedComment(BaseModel):
    model_config = ConfigDict(extra="ignore")

    comment_id: int
    category: CategoryLiteral
    confidence: float
    summary: str
    classified_at: datetime
    needs_review: bool  # True when confidence < 0.75


class ClassifiedFile(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pr: PRRecord          # same PRRecord as in PRFile
    classifications: list[ClassifiedComment]
    classified_at: datetime
```

### Pattern 3: Atomic Index Write

```python
# Source: _write_cache_atomic from extractor.py — identical pattern

def _write_index_atomic(index_path: Path, index: dict) -> None:
    tmp_name: str | None = None
    try:
        tmp_fd, tmp_name = tempfile.mkstemp(dir=index_path.parent, suffix=".tmp")
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, default=str)
        os.replace(tmp_name, str(index_path))
    except Exception:
        if tmp_name is not None:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
        raise
```

### Pattern 4: Config Extension

```python
# Source: config.py line 15 (placeholder comment already exists)

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    github_token: str
    anthropic_api_key: str   # Phase 4: required for classify command
```

The `anthropic_api_key` should be `str` (required, not optional) — the classifier has no fallback if the key is absent. The fail-fast import-time pattern already in `config.py` will surface a `ValidationError` immediately if the key is missing, which is the correct behavior.

### Pattern 5: Test Mock Construction

```python
# Source: verified via .venv/Scripts/python.exe introspection — Message is constructible

from unittest.mock import patch
import anthropic

def make_mock_message(json_text: str) -> anthropic.types.Message:
    return anthropic.types.Message(
        id="msg_test",
        content=[anthropic.types.TextBlock(text=json_text, type="text")],
        model="claude-3-5-haiku-latest",
        role="assistant",
        stop_reason="end_turn",
        type="message",
        usage=anthropic.types.Usage(input_tokens=120, output_tokens=40),
    )


def test_classify_comment_calls_api(tmp_path):
    json_resp = '{"category": "gotcha", "confidence": 0.92, "summary": "Always set X"}'
    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        MockAnthropic.return_value.messages.create.return_value = make_mock_message(json_resp)
        # ... call classifier and assert
```

### Anti-Patterns to Avoid

- **Free-form string category values:** The category must be validated as one of the 5 Literals. If Claude returns an unexpected string (e.g., "code-pattern" with a hyphen), a fallback to `"other"` is safer than a `ValidationError`.
- **Storing raw API response text in the index:** Only `{category, confidence, summary, classified_at}` go in `classification-index.json` per D-05. Do not store the full response.
- **Loading `classification-index.json` per comment:** Load once at classifier init, write atomically at the end of each successful classification (or batch, per implementation choice).
- **Mutable dict default for `reactions` pattern:** The `ClassifiedComment` model has no dict fields requiring this care, but follow the same Pydantic v2 immutability practices as existing models.
- **Using `json.dumps(classified_file.model_dump())` without `mode="json"`:** `datetime` fields serialize as Python objects without `mode="json"`. Always use `model_dump(mode="json")`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry on transient API failure | Custom retry loop | `anthropic.Anthropic(max_retries=2)` constructor param | SDK has built-in retry with exponential backoff; `max_retries` defaults to 2 |
| JSON parsing with fallback | Custom string extraction | `json.loads()` + `except json.JSONDecodeError` | Claude almost always returns valid JSON when explicitly instructed; catch-and-fallback is enough |
| Content hashing | Custom fingerprint | `hashlib.sha256(body.encode("utf-8")).hexdigest()` | stdlib, collision-resistant, deterministic, 64-char hex |
| Atomic file write | Manual temp+rename logic | Copy `_write_cache_atomic` from `extractor.py` verbatim | Already battle-tested in this codebase |

**Key insight:** The SDK's built-in `max_retries` parameter handles all transient HTTP failures. The only custom error handling needed is `json.JSONDecodeError` on response parsing and an `anthropic.APIError` guard to handle partial-run failures gracefully.

---

## Common Pitfalls

### Pitfall 1: Import-Time ValidationError for ANTHROPIC_API_KEY in Tests

**What goes wrong:** Once `anthropic_api_key: str` is added to `Settings` (not `str | None`), any test file that imports from `github_pr_kb` will raise `ValidationError` at collection time unless the env var exists.

**Why it happens:** `settings = Settings()` executes at module import time (by design per [Phase 02-01] decision).

**How to avoid:** Add `os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test000000000000000000000000000fake")` to the top of `tests/conftest.py` at module level — the same pattern already used for `GITHUB_TOKEN`.

**Warning signs:** `pydantic_settings.env_settings_source.SettingsError: field required` appearing on `pytest --collect-only`.

---

### Pitfall 2: Claude Returning Non-JSON or Malformed JSON

**What goes wrong:** If the system prompt isn't explicit enough, Claude may wrap the JSON in backticks, add explanation text, or return `None` for confidence. The `json.loads()` call raises `JSONDecodeError`.

**Why it happens:** LLMs sometimes add "friendly" formatting even when instructed to return only JSON.

**How to avoid:** (1) Instruct explicitly: "Respond with ONLY a JSON object, no other text, no backticks." (2) Wrap `json.loads()` in `try/except json.JSONDecodeError` and fall back to `{"category": "other", "confidence": 0.0, "summary": "classification failed"}`. (3) Log the raw response at DEBUG level before parsing.

**Warning signs:** `json.JSONDecodeError` in test runs even against mocked responses (indicates mock text itself is malformed).

---

### Pitfall 3: Category Value Not in Literal

**What goes wrong:** Claude may return `"code-pattern"` (hyphen) instead of `"code_pattern"` (underscore), or `"architecture"` instead of `"architecture_decision"`. Pydantic raises `ValidationError` on `ClassifiedComment` construction.

**Why it happens:** The model generalizes from its training data and may not precisely reproduce the exact string.

**How to avoid:** Include the exact category strings in the system prompt using a numbered list. Additionally, add a normalization step before model construction: `VALID_CATEGORIES = {"architecture_decision", ...}; category = result.get("category", "other") if result.get("category") in VALID_CATEGORIES else "other"`.

**Warning signs:** `ValidationError: value is not a valid enumeration member` during classify runs.

---

### Pitfall 4: Index File Written Inconsistently on Partial Runs

**What goes wrong:** If a classify run is interrupted (keyboard interrupt, exception mid-loop), the in-memory index may have new entries that were never flushed to `classification-index.json`. On re-run, those comments are sent to the API again.

**Why it happens:** Writing the index only at the end of the full run means partial progress is lost.

**How to avoid:** Write the index atomically after each successful individual classification. This is slightly slower (one atomic write per comment) but keeps the index consistent with actual API costs. Given the scale (PR comment sets), this is acceptable.

**Warning signs:** Re-running classify after an interruption shows more API calls than expected.

---

### Pitfall 5: Confidence Value Outside [0.0, 1.0]

**What goes wrong:** Claude may return `confidence: 85` (integer 0-100 scale) or `confidence: "0.85"` (string). Both cause silent logic bugs — `0.85 < 0.75` is False but `85 < 0.75` is also False (both would be flagged or both would be missed).

**Why it happens:** Ambiguity in the prompt about the expected scale.

**How to avoid:** Explicitly state in the prompt: "Return confidence as a float between 0.0 and 1.0 (e.g. 0.85 means 85% confident)." Add a validation step: `confidence = float(result.get("confidence", 0.0)); confidence = max(0.0, min(1.0, confidence))`.

---

## Code Examples

### Minimal messages.create() Call

```python
# Source: verified from .venv/Scripts/python.exe introspection of anthropic 0.84.0

import anthropic

client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2)

response = client.messages.create(
    model="claude-3-5-haiku-latest",
    max_tokens=256,
    system="You are a classifier. Respond with ONLY a JSON object: {\"category\": ..., \"confidence\": ..., \"summary\": ...}",
    messages=[{"role": "user", "content": comment_body}],
)
text = response.content[0].text
result = json.loads(text)
```

### Constructing a Real Message Object for Tests

```python
# Source: verified constructible via SDK introspection (anthropic.types.Message is a Pydantic model)

import anthropic

msg = anthropic.types.Message(
    id="msg_test123",
    content=[anthropic.types.TextBlock(
        text='{"category": "gotcha", "confidence": 0.92, "summary": "Always set retry on client"}',
        type="text"
    )],
    model="claude-3-5-haiku-latest",
    role="assistant",
    stop_reason="end_turn",
    type="message",
    usage=anthropic.types.Usage(input_tokens=120, output_tokens=40),
)
# msg.content[0].text  →  '{"category": ...}'
# msg.usage.input_tokens  →  120
```

### SHA-256 Content Hash

```python
# Source: stdlib hashlib — verified via python -c

import hashlib

def body_hash(body: str) -> str:
    """64-char hex SHA-256 of comment body for cross-PR dedup (D-04)."""
    return hashlib.sha256(body.encode("utf-8")).hexdigest()
```

### Patching Anthropic in Tests

```python
# Source: mirrors existing patch("github_pr_kb.extractor.Github") pattern in test_extractor.py

from unittest.mock import patch

def test_classify_cache_miss_calls_api(tmp_path):
    json_body = '{"category": "gotcha", "confidence": 0.88, "summary": "Use retry"}'
    with patch("github_pr_kb.classifier.Anthropic") as MockAnthropic:
        mock_client = MockAnthropic.return_value
        mock_client.messages.create.return_value = make_mock_message(json_body)

        classifier = PRClassifier(cache_dir=tmp_path)
        result = classifier.classify_pr(1)

    mock_client.messages.create.assert_called_once()
    assert result[0].category == "gotcha"
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `anthropic.Anthropic(api_key=...)` positional | Keyword-only `api_key=` | anthropic v0.20+ | No positional args accepted |
| `response.completion` (v0 API) | `response.content[0].text` | anthropic v0.20+ | Old attribute no longer exists |
| `Auth.Token(token)` positional (PyGithub v1) | Keyword in v2 | PyGithub v2.0 | Already handled in extractor.py |

**Deprecated / outdated:**

- `anthropic.Claude`: Removed in SDK v0.20+. Use `anthropic.Anthropic()` client.
- `response.completion`: Replaced by `response.content[0].text`. The `content` list is now the canonical response accessor.

---

## Open Questions

1. **Should `anthropic_api_key` be required (`str`) or optional (`str | None`) in `Settings`?**
   - What we know: The classifier cannot function without it. The existing pattern is fail-fast required fields.
   - What's unclear: If the user only runs `extract` (not `classify`), they'd need to set the key even without using Claude.
   - Recommendation: Make it required (`str`). The CLI in Phase 6 can provide a clear error message. Alternatively, make it `str | None = None` and raise a `ValueError` in the `Classifier.__init__` if it is None. This avoids breaking `extract`-only users.

2. **Write `classification-index.json` per-comment or at-end-of-run?**
   - What we know: Per D-05, the index is "appended with new entries after each successful classification." This implies per-comment writes.
   - What's unclear: "After each" could mean per-comment or per-batch.
   - Recommendation: Per-comment atomic writes. At PR comment scale (tens to hundreds), the overhead is negligible and consistency is higher.

3. **How should partial failure (one comment fails) be handled?**
   - What we know: Claude's SDK retries 2x by default. After retries, an `anthropic.APIError` is raised.
   - Recommendation: Log the failure at WARNING level, skip the comment (don't write a classification), continue to the next comment. The summary at the end should include a "failed" count alongside "classified" and "cache hits."

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| anthropic SDK | Claude API calls | Yes | 0.84.0 (latest: 0.89.0) | — |
| ANTHROPIC_API_KEY | Live API calls (tests: mocked) | Not checked — user-provided | — | Test env uses `sk-ant-test` fake |
| hashlib | Content hashing | Yes (stdlib) | stdlib | — |
| pytest | Tests | Yes | >=9.0.2 | — |

**Missing dependencies with no fallback:** None — all required packages are already installed.

**Note on SDK version:** 0.84.0 is installed; 0.89.0 is current. No breaking changes to `messages.create()` between these versions. No version bump required for Phase 4, but `>=0.84.0` in pyproject.toml already permits auto-upgrade.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_classifier.py -x` |
| Full suite command | `.venv/Scripts/python.exe -m pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLASS-01 | Comment is classified into one of 5 categories | unit | `.venv/Scripts/python.exe -m pytest tests/test_classifier.py::test_classify_returns_valid_category -x` | Wave 0 |
| CLASS-02 | `needs_review=True` when confidence < 0.75 | unit | `.venv/Scripts/python.exe -m pytest tests/test_classifier.py::test_needs_review_flag -x` | Wave 0 |
| CLASS-03 | Cached hash hit = zero API calls on re-run | unit | `.venv/Scripts/python.exe -m pytest tests/test_classifier.py::test_cache_hit_no_api_call -x` | Wave 0 |
| CLASS-04 | Output includes comment_id, category, confidence, summary | unit | `.venv/Scripts/python.exe -m pytest tests/test_classifier.py::test_classified_comment_fields -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/Scripts/python.exe -m pytest tests/test_classifier.py -x`
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest tests/`
- **Phase gate:** Full suite green (currently 35 pass, 6 skipped integration) before `/gsd:verify-work`

### Wave 0 Gaps

- `tests/test_classifier.py` — covers CLASS-01 through CLASS-04 (4 tests minimum)
- `tests/conftest.py` — add `os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test000000000000000000000000000fake")` at module level

*(Existing `tests/conftest.py` and `pytest` infrastructure are in place — only the new test file and env var setdefault need to be added.)*

---

## Project Constraints (from CLAUDE.md)

- **Test runner:** Always use `.venv/Scripts/python.exe -m pytest tests/` — never `uv run pytest` (resolves to wrong interpreter on this machine).
- **Type hints:** Python 3.13 style — `str | None` not `Optional[str]`, `list[X]` not `List[X]`.
- **Strict `Any` policy:** Do not use `typing.Any`; use `object`, `Protocol`, or generics instead.
- **Pydantic models:** `ConfigDict(extra="ignore")` on all new models.
- **Literal types for enums:** Use `Literal[...]` for `category` field (established pattern for `comment_type`, `state`).
- **Module-level settings:** `settings = Settings()` at import time — adding `anthropic_api_key` follows the same fail-fast pattern.
- **Atomic writes:** Use mkstemp + os.replace for all cache file mutations.
- **Logging:** `logger = logging.getLogger(__name__)` — no print() calls.

---

## Sources

### Primary (HIGH confidence)

- Anthropic SDK 0.84.0 — introspected via `.venv/Scripts/python.exe` in project venv: `messages.create()` signature, `Message`/`TextBlock`/`Usage` model fields, `max_retries` param
- `src/github_pr_kb/extractor.py` — atomic write pattern (`_write_cache_atomic`), `patch("github_pr_kb.extractor.Github")` mock pattern
- `src/github_pr_kb/models.py` — `ConfigDict(extra="ignore")`, `Literal` enum pattern
- `src/github_pr_kb/config.py` — `Settings` class with module-level instantiation, placeholder comment at line 15
- `tests/conftest.py` — `os.environ.setdefault` at module level pattern
- `pyproject.toml` — confirmed `anthropic>=0.84.0` already declared; `pytest>=9.0.2` for test runner
- `.planning/phases/04-claude-classifier/04-CONTEXT.md` — all locked decisions (D-01 through D-07)

### Secondary (MEDIUM confidence)

- `pip index versions anthropic` — confirmed 0.84.0 installed, 0.89.0 latest available (verified 2026-04-05)
- Anthropic SDK introspection: `Message` is a Pydantic model constructible without a live key — confirmed by constructing test instance in venv

### Tertiary (LOW confidence)

- Model selection rationale (haiku vs sonnet cost comparison) — based on known Claude pricing tiers; exact pricing not verified against current Anthropic pricing page but model family cost ordering is stable.

---

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — SDK already installed, introspected directly in project venv
- Architecture: HIGH — all patterns derived from locked decisions (CONTEXT.md) and verified existing code
- Pitfalls: HIGH — import-time ValidationError and JSON parsing pitfalls verified via code tracing; confidence/category normalization patterns from direct testing
- Test patterns: HIGH — `anthropic.types.Message` constructibility verified by running SDK code in venv

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable SDK; 30-day window appropriate)
