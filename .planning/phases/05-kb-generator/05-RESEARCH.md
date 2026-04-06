# Phase 5: KB Generator - Research

**Researched:** 2026-04-05
**Domain:** Python file generation, YAML frontmatter, slug generation, incremental manifest-based dedup
**Confidence:** HIGH

## Summary

Phase 5 is a pure Python file-generation phase with no new external API dependencies. The generator reads `classified-pr-N.json` files from the cache directory (written by Phase 4's `PRClassifier`), assembles one markdown article per classified comment, and writes them into a `kb/` directory organized by category. A `kb/.manifest.json` tracks `comment_id -> relative path` so incremental re-runs skip already-generated articles. `kb/INDEX.md` is regenerated from scratch on every run by scanning all existing `.md` files.

The codebase already has all the patterns this phase needs: the `_write_atomic` function from `classifier.py` handles safe file writes, `ClassifiedFile` / `ClassifiedComment` / `CommentRecord` / `PRRecord` are the input models, and `pydantic-settings` handles the new `kb_output_dir` config field. No new packages are needed.

The one non-trivial algorithm is slug generation (D-07/D-08/D-09): lowercase, ASCII-only, hyphen-separated, max 60 chars truncated at word boundary, with `-N` numeric suffix for collisions. This is straightforwardly implemented with `unicodedata.normalize` + `re.sub` — no third-party library needed.

**Primary recommendation:** Implement in a single `KBGenerator` class in `generator.py`, mirroring the `PRClassifier` class shape. Keep slug generation as a standalone module-level function so it can be unit-tested directly.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Article Content & Format**
- D-01: Each KB article contains the AI one-line summary as the heading, followed by the full original comment body below it.
- D-02: YAML frontmatter always includes: PR link, PR title, comment author, date, category, confidence score, needs_review flag, and comment_id.
- D-03: For review comments that have a `diff_hunk`, embed it in the article body (below the comment) so code context is visible. Issue comments (no diff_hunk) omit this section.
- D-04: needs_review articles (confidence < 75%) are included in the KB like normal articles, with `needs_review: true` in frontmatter. No separate directory.
- D-05: "other" category comments are included in `kb/other/` — not excluded.

**File Naming & Structure**
- D-06: One article per classified comment (not grouped by PR).
- D-07: File names are slugified from the AI summary. E.g., `avoid-circular-imports.md`.
- D-08: Slug rules: lowercase, ASCII-only (transliterate unicode), hyphens for spaces/special chars, max 60 characters, truncate at word boundary.
- D-09: Slug collisions resolved with `-N` numeric suffix. E.g., `avoid-circular-imports-2.md`.
- D-10: Category subdirectories created on demand (only when first article in that category is written). No empty dirs.

**Index File**
- D-11: Index lives at `kb/INDEX.md`.
- D-12: Index grouped by category with `## Category Name (count)` headings. Each entry is a link + one-line summary.
- D-13: needs_review articles appear inline in their category with a `[review]` marker.
- D-14: Index is fully regenerated from all existing .md files on every run (not incrementally appended).

**Incremental Merge**
- D-15: Dedup via manifest file at `kb/.manifest.json` mapping comment_id -> relative file path.
- D-16: On each run: load manifest, skip known comment_ids, write new articles, update manifest, then regenerate INDEX.md.
- D-17: KB output directory is configurable via `kb_output_dir` field in Settings (config.py), defaulting to `kb/`.

**Error Handling**
- D-18: Malformed classified JSON files or unprocessable comments log a warning (identifying the problem file/comment and failure type), continue processing remaining items.
- D-19: Failures are tracked explicitly with their type — not silently skipped. Generator returns a result summary distinguishing successful articles from failed entries (with failure reason).

### Claude's Discretion
- Exact YAML frontmatter field ordering
- Slug generation implementation details (stop words, edge cases beyond the rules above)
- Exact warning/log message format for failures
- Internal class/function structure of the generator module

### Deferred Ideas (OUT OF SCOPE)
- **Topic aggregation / article combining** — When multiple comments produce similar slugs, intelligently merge them into a single article. More of a v2 "smart grouping" feature than simple slug collision handling.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| KB-01 | User can generate a markdown knowledge base organized into per-category subdirectories | D-10 — subdirs created on demand; existing `Path.mkdir(parents=True, exist_ok=True)` pattern |
| KB-02 | Each KB article includes YAML frontmatter: PR link, author, date, category, confidence score | D-02 — full frontmatter spec; rendered via simple f-string (no YAML library needed at this scale) |
| KB-03 | Generator produces an index file listing all topics with article counts and summaries | D-11/D-12/D-13/D-14 — full index spec; regenerated from filesystem scan on every run |
| KB-04 | Incremental KB generation merges new content without duplicating existing entries (PR+comment ID dedup) | D-15/D-16 — manifest at `kb/.manifest.json`, keyed by `comment_id`; atomic manifest write |
</phase_requirements>

---

## Standard Stack

### Core (no new packages needed)
| Library | Version (pyproject) | Purpose | Why Standard |
|---------|---------------------|---------|--------------|
| pydantic v2 | >=2.12.5 | Input model validation (ClassifiedFile, ClassifiedComment) | Already in project; `model_validate_json` for safe deserialization |
| pydantic-settings | >=2.13.1 | `kb_output_dir` config field in Settings | Already in project; Settings class extended in config.py |
| Python stdlib: `pathlib` | Python 3.14 | All file I/O and directory creation | `Path.mkdir(parents=True, exist_ok=True)` handles subdirs on demand |
| Python stdlib: `unicodedata` | Python 3.14 | Unicode normalization for slug generation (NFKD + ASCII encoding) | No third-party needed; `unicodedata.normalize('NFKD', text).encode('ascii', 'ignore')` |
| Python stdlib: `re` | Python 3.14 | Slug character stripping (non-word chars to hyphens) | Sufficient for slug rules without extra dependency |
| Python stdlib: `json` | Python 3.14 | Manifest read/write, classified JSON read | Consistent with classifier.py pattern |
| Python stdlib: `logging` | Python 3.14 | Warning logs for D-18/D-19 | Consistent with existing logger usage |
| Python stdlib: `tempfile` + `os` | Python 3.14 | Atomic writes (reuse `_write_atomic` from classifier.py) | Established project pattern |

### What to Reuse from Phase 4

| Asset | Location | Reuse Approach |
|-------|----------|----------------|
| `_write_atomic` | `classifier.py` lines 57-69 | Move to shared utility or copy into `generator.py` — avoids cross-module coupling |
| `ClassifiedFile`, `ClassifiedComment`, `PRRecord`, `CommentRecord` | `models.py` | Import directly; these are the full input data structures |
| `DEFAULT_CACHE_DIR` constant | `classifier.py` line 24 | Generator needs same cache dir default — define its own constant or import |
| `ConfigDict(extra='ignore')` pattern | all models | Apply to any new Pydantic models in generator |

**Installation:** No new packages. All dependencies already in pyproject.toml.

---

## Architecture Patterns

### Recommended Project Structure (additions only)
```
src/github_pr_kb/
└── generator.py          # KBGenerator class + slugify() function

tests/
└── test_generator.py     # TDD tests for generator (new file)

kb/                       # Generated output (runtime, not source)
├── .manifest.json        # comment_id -> relative path dedup map
├── INDEX.md              # Regenerated on every run
├── architecture_decision/
│   └── avoid-circular-imports.md
├── code_pattern/
│   └── use-retry-for-external-apis.md
├── gotcha/
│   └── pydantic-v2-no-optional-shorthand.md
├── domain_knowledge/
│   └── pr-review-bot-excluded-from-extraction.md
└── other/
    └── minor-style-comment.md
```

### Pattern 1: KBGenerator Class Structure

Mirrors `PRClassifier` shape (constructor, private methods, public `generate` method):

```python
# Source: classifier.py — established project pattern
class KBGenerator:
    def __init__(
        self,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        kb_dir: Path | None = None,
    ) -> None:
        self._cache_dir = cache_dir
        self._kb_dir = kb_dir or Path(settings.kb_output_dir)
        self._manifest: dict[str, str] = self._load_manifest()
        self._written = 0
        self._skipped = 0
        self._failed: list[dict[str, str]] = []  # D-19: explicit failure tracking

    def generate_all(self) -> GenerateResult:
        """Read all classified-pr-N.json files, write new articles, regenerate index."""
        ...
```

### Pattern 2: Article Markdown Format

```markdown
---
pr_url: https://github.com/owner/repo/pull/42
pr_title: "Refactor authentication middleware"
comment_url: https://github.com/owner/repo/pull/42#comment-101
author: alice
date: 2026-01-15T10:30:00+00:00
category: gotcha
confidence: 0.85
needs_review: false
comment_id: 101
---

# Avoid mutating shared state in middleware chains

Always copy request context before modifying it in middleware to avoid
subtle bugs when multiple request handlers share state objects.

```python
# diff_hunk (only for review comments with D-03)
@@ -12,3 +12,3 @@
-    ctx.user = user
+    ctx = ctx.copy(update={"user": user})
```
```

**YAML frontmatter field ordering (Claude's discretion):** Recommended order from most-identifying to least: `pr_url`, `pr_title`, `comment_url`, `author`, `date`, `category`, `confidence`, `needs_review`, `comment_id`. This puts navigation fields first and metadata fields last.

**Note on YAML library:** No third-party YAML library is needed. Frontmatter is simple key-value with known fields — a manually constructed f-string is safer than PyYAML (no risk of YAML injection or unexpected multiline quoting). String values that may contain special chars should be double-quoted.

### Pattern 3: Slug Generation

```python
import re
import unicodedata

def slugify(text: str, max_len: int = 60) -> str:
    """Convert AI summary text to a URL-safe, filesystem-safe slug (D-08)."""
    # 1. Normalize unicode to ASCII
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    # 2. Lowercase
    lowered = ascii_text.lower()
    # 3. Replace non-alphanumeric with hyphens
    slugged = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    # 4. Truncate at word boundary (don't cut mid-word)
    if len(slugged) > max_len:
        truncated = slugged[:max_len]
        # Back up to the last hyphen to avoid cutting mid-word
        last_hyphen = truncated.rfind("-")
        slugged = truncated[:last_hyphen] if last_hyphen > 0 else truncated
    return slugged or "untitled"
```

### Pattern 4: Manifest Load/Save

```python
def _load_manifest(self) -> dict[str, str]:
    """Load kb/.manifest.json; keys are str(comment_id), values are relative paths."""
    path = self._kb_dir / ".manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        logger.warning("kb/.manifest.json is corrupt — rebuilding from scratch")
        return {}
```

### Pattern 5: Index Regeneration (D-14)

Index is rebuilt by scanning all `.md` files in `kb/` (excluding `INDEX.md`) and reading their YAML frontmatter to extract `category`, `needs_review`, `comment_id`, and `summary`. Sorted per category, alphabetically by filename within each category.

**Implementation approach:** Parse frontmatter by reading lines until the closing `---` delimiter. No full YAML parser needed — the frontmatter values are simple scalars set by this generator.

### Anti-Patterns to Avoid

- **Do not use PyYAML or ruamel.yaml** — adding a dependency just for YAML serialization of known fixed fields is unnecessary overhead.
- **Do not scan filesystem for index rebuild instead of using manifest** — the manifest already has the canonical comment_id -> path map; use it for dedup, but scan filesystem for index rebuild to catch any files written outside normal flow.
- **Do not fail the entire run on a single bad classified file** — D-18 requires continue-on-error with warning logging.
- **Do not use `open()` with `'w'` mode directly for article writes** — reuse the `_write_atomic` pattern to prevent partial files on crash.
- **Do not store absolute paths in the manifest** — store paths relative to `kb_dir` so the KB is portable (e.g., `architecture_decision/avoid-circular-imports.md`).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file writes | Custom temp+rename logic | Reuse `_write_atomic` from classifier.py | Already handles `mkstemp`, `os.replace`, cleanup on exception |
| Unicode slug generation | Full transliteration table | `unicodedata.normalize('NFKD')` + `.encode('ascii', 'ignore')` | Stdlib handles all Unicode decomposition cases |
| Pydantic model deserialization | Manual `json.loads` + dict unpacking | `ClassifiedFile.model_validate_json(content)` | Validates on parse, handles `extra='ignore'`, raises `ValidationError` on bad data |
| Category directory names | Hard-coded `if/else` | `classified_comment.category` value directly (it IS the dir name) | `CategoryLiteral` values are already filesystem-safe lowercase strings |

**Key insight:** The classified comment's `category` field value (`architecture_decision`, `code_pattern`, etc.) is already a valid, filesystem-safe directory name — no mapping table needed.

---

## Common Pitfalls

### Pitfall 1: Manifest Key Type — int vs. str
**What goes wrong:** `json.loads` always produces string keys in JSON objects. If the manifest is loaded as `dict[str, str]` but the code looks up `manifest[comment.comment_id]` (an `int`), lookups always miss, causing duplicate articles on every run.
**Why it happens:** Python `dict` is type-strict for keys. `101 != "101"`.
**How to avoid:** Store and look up manifest keys as `str(comment_id)` consistently.
**Warning signs:** Every run writes the same articles instead of skipping known ones.

### Pitfall 2: Slug Collision in Incremental Runs
**What goes wrong:** On a second run, a new comment produces the same slug as an existing article. The generator checks the manifest (no match), tries to write `avoid-circular-imports.md`, but that file already exists for a different comment.
**Why it happens:** Slug collision detection must check both the manifest (for dedup by comment_id) and the filesystem (for slug uniqueness).
**How to avoid:** After slug generation, check if the target path already exists in the manifest's values. If so, append `-2`, `-3`, etc. Keep a per-run `set[str]` of slugs used in this invocation plus slugs in the manifest.

### Pitfall 3: `ConfigDict(extra='ignore')` missing on GenerateResult
**What goes wrong:** If a new `GenerateResult` model omits `ConfigDict(extra='ignore')`, future schema additions break deserialization of stored results.
**How to avoid:** Apply `ConfigDict(extra='ignore')` to every Pydantic model per established project pattern (STATE.md decision `[Phase 02-01]`).

### Pitfall 4: YAML Frontmatter Quoting
**What goes wrong:** PR titles or comment authors containing `:`, `#`, or `"` break YAML parsing if not quoted. A manually-built frontmatter string can produce invalid YAML.
**How to avoid:** Always double-quote string values in frontmatter. Use a helper like `_yaml_str(value: str) -> str` that wraps in double quotes and escapes internal double quotes with `\"`.

### Pitfall 5: Index Rebuild Reads Frontmatter Incorrectly
**What goes wrong:** Index rebuild scans `.md` files and parses frontmatter. If any article has a malformed frontmatter (e.g., from a file written by an older version), the index rebuild crashes.
**How to avoid:** Index rebuild should be resilient — log a warning and skip unparseable files rather than crashing (consistent with D-18/D-19).

### Pitfall 6: `kb/` Directory Not in `.gitignore`
**What goes wrong:** The generated `kb/` output directory gets accidentally committed, conflicting with incremental runs and bloating git history.
**Recommendation:** The planner should include a task to check whether `kb/` should be in `.gitignore` (user intent: is the KB output supposed to be committed?). The CONTEXT.md doesn't specify — this is a deferred question to surface.

---

## Code Examples

### Verified Pattern: Reading All Classified Files

```python
# Source: classifier.py classify_all() — established project pattern
def _find_classified_files(self) -> list[int]:
    pr_numbers: list[int] = []
    for p in self._cache_dir.glob("classified-pr-*.json"):
        stem = p.stem  # e.g. "classified-pr-42"
        try:
            pr_numbers.append(int(stem.split("-")[-1]))
        except ValueError:
            logger.warning("Unexpected classified file name: %s — skipping", p.name)
    return pr_numbers
```

### Verified Pattern: Directory Creation on Demand (D-10)

```python
# Source: Python stdlib — Path.mkdir is idempotent with exist_ok=True
category_dir = self._kb_dir / classified_comment.category
category_dir.mkdir(parents=True, exist_ok=True)
```

### Verified Pattern: Model Deserialization with Error Handling (D-18)

```python
# Source: classifier.py classify_pr() — established project pattern
try:
    content = path.read_text(encoding="utf-8")
    classified_file = ClassifiedFile.model_validate_json(content)
except (OSError, ValidationError) as exc:
    logger.warning("Could not read classified file %s: %s", path.name, exc)
    self._failed.append({"file": path.name, "reason": type(exc).__name__, "detail": str(exc)})
    continue
```

### Verified Pattern: Frontmatter String Construction

```python
def _build_frontmatter(self, pr: PRRecord, comment: CommentRecord, classified: ClassifiedComment) -> str:
    def _yaml_str(value: str) -> str:
        return '"' + value.replace('"', '\\"') + '"'

    lines = [
        "---",
        f"pr_url: {pr.url}",
        f"pr_title: {_yaml_str(pr.title)}",
        f"comment_url: {comment.url}",
        f"author: {_yaml_str(comment.author)}",
        f"date: {comment.created_at.isoformat()}",
        f"category: {classified.category}",
        f"confidence: {classified.confidence}",
        f"needs_review: {str(classified.needs_review).lower()}",
        f"comment_id: {comment.comment_id}",
        "---",
    ]
    return "\n".join(lines)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Optional[str]` from `typing` | `str \| None` (PEP 604) | Python 3.10+ | Use union shorthand per python-typing.md rules |
| `List[str]`, `Dict[str, int]` from `typing` | `list[str]`, `dict[str, int]` | Python 3.9+ | Use built-in generics per python-typing.md rules |
| `from __future__ import annotations` for forward refs | Not needed | Python 3.11+ | Project targets Python 3.11+; no `from __future__` needed |

**Deprecated/outdated:**
- `typing.Optional` — use `str | None` per project's python-typing.md rule
- `typing.Union` — use `int | str` per project's python-typing.md rule

---

## Open Questions

1. **Should `kb/` be committed to git?**
   - What we know: The CONTEXT.md doesn't address this. The KB is generated output, like a build artifact.
   - What's unclear: User intent — is the KB meant to be committed alongside code (as persistent knowledge) or generated on demand?
   - Recommendation: Add `.gitignore` entry for `kb/` by default. Planner should surface this as a decision point with a note that the user can remove the ignore if they want versioned KB output.

2. **Should `_write_atomic` be extracted to a shared utility?**
   - What we know: The function currently lives in `classifier.py`. Generator needs it too.
   - What's unclear: Whether to import from classifier (creating a dependency) or copy into generator.
   - Recommendation: Copy into `generator.py` (or extract to a private `_utils.py` if a third phase also needs it). Avoid cross-module coupling between classifier and generator.

3. **What is the `cache_dir` for the generator's classifier data?**
   - What we know: `DEFAULT_CACHE_DIR = Path(".github-pr-kb/cache")` in classifier.py. Generator reads from the same location.
   - What's unclear: The generator should share or import this constant.
   - Recommendation: Define `DEFAULT_CACHE_DIR` in `generator.py` matching classifier's value, or move it to `config.py` as a settings field for DRY consistency.

---

## Environment Availability

Step 2.6: SKIPPED — Phase 5 is a pure Python file-generation module with no external API dependencies beyond what is already installed (pydantic, pydantic-settings). No new CLI tools, databases, or services are required.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-cov |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_generator.py -x` |
| Full suite command | `.venv/Scripts/python.exe -m pytest tests/` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| KB-01 | Running generate creates per-category subdirectories | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_generate_creates_category_subdirs -x` | Wave 0 |
| KB-01 | Each article is written to the correct category subdir | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_article_written_to_category_subdir -x` | Wave 0 |
| KB-02 | Article YAML frontmatter includes all required fields | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_article_frontmatter_fields -x` | Wave 0 |
| KB-02 | Review comment with diff_hunk includes hunk in article body | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_diff_hunk_in_review_comment -x` | Wave 0 |
| KB-02 | Issue comment without diff_hunk omits hunk section | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_no_diff_hunk_for_issue_comment -x` | Wave 0 |
| KB-03 | Index file is produced at kb/INDEX.md | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_index_file_created -x` | Wave 0 |
| KB-03 | Index groups by category with ## headings | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_index_grouped_by_category -x` | Wave 0 |
| KB-03 | needs_review articles marked with [review] in index | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_index_review_marker -x` | Wave 0 |
| KB-04 | Second run with same data skips already-generated articles | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_incremental_no_duplicate -x` | Wave 0 |
| KB-04 | Second run with new classified file adds new articles only | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_incremental_adds_new_articles -x` | Wave 0 |
| KB-04 | Manifest persists comment_id -> path mapping | unit | `.venv/Scripts/python.exe -m pytest tests/test_generator.py::test_manifest_written -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `.venv/Scripts/python.exe -m pytest tests/test_generator.py -x`
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_generator.py` — covers all KB-01 through KB-04 requirements (entire file is new)
- [ ] No new framework or fixture infrastructure needed — `conftest.py` already sets env vars; generator tests use `tmp_path` only

---

## Project Constraints (from CLAUDE.md)

| Directive | Impact on Phase 5 |
|-----------|-------------------|
| Always run tests with `.venv/Scripts/python.exe -m pytest tests/` — never `uv run pytest` | All test commands in plans must use this form |
| Windows environment — use forward slashes in paths only where Python handles them | Python `pathlib.Path` is safe on Windows; avoid raw string paths with backslashes |
| RTK prefix for all shell commands in plans | Shell commands in task actions should use `rtk` prefix |

---

## Sources

### Primary (HIGH confidence)
- Direct code inspection: `src/github_pr_kb/classifier.py` — atomic write pattern, class structure, logging conventions
- Direct code inspection: `src/github_pr_kb/models.py` — all input model fields confirmed
- Direct code inspection: `src/github_pr_kb/config.py` — Settings class structure confirmed
- Direct code inspection: `pyproject.toml` — dependency versions confirmed, no YAML library present
- Direct code inspection: `tests/conftest.py`, `tests/test_classifier.py` — test patterns confirmed
- Python stdlib docs: `unicodedata.normalize`, `pathlib.Path`, `re` — all confirmed in stdlib
- `.claude/rules/python-typing.md` — type annotation standards
- `.claude/rules/clean-code.md` — code quality standards

### Secondary (MEDIUM confidence)
- `.planning/phases/05-kb-generator/05-CONTEXT.md` — all decisions are user-confirmed; treated as locked

### Tertiary (LOW confidence)
- None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all stdlib + existing project deps verified
- Architecture: HIGH — all patterns derived from existing codebase and CONTEXT.md decisions
- Pitfalls: HIGH — manifest key type pitfall and slug collision are logic-derived from decisions; frontmatter quoting is a well-known YAML edge case

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (stable domain — stdlib + pydantic; no fast-moving APIs)
