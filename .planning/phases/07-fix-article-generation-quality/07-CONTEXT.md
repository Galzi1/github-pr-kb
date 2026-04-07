# Phase 7: Fix Article Generation Quality - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the generate pipeline so KB articles are genuinely useful, well-synthesized knowledge articles — not raw comment dumps, not misleading CLI output, not meaningless classification-failure files. This phase modifies the classifier (failure handling), generator (Claude-powered synthesis), CLI (honest reporting), and config (new settings).

</domain>

<decisions>
## Implementation Decisions

### Article Synthesis
- **D-01:** Claude rewrites each comment into a structured KB article during the `generate` step (not classify). KBGenerator calls Claude to synthesize each article at generation time.
- **D-02:** Category-specific article templates:
  - `gotcha` → Symptom / Root Cause / Fix or Workaround
  - `architecture_decision` → Context / Decision / Consequences
  - `code_pattern` → Pattern / When to Use / Example
  - `domain_knowledge` → Context / Key Insight / Implications
  - `other` → Context / Key Insight / Recommendation (generic)
- **D-03:** Synthesis input is the raw comment body + PR title. No other PR context (other comments, etc.).
- **D-04:** No raw comment preserved in the synthesized article — the article is purely the Claude-synthesized version. Raw comment remains in cache JSON for provenance.
- **D-05:** Manifest-based dedup for synthesis — existing `manifest[comment_id]` check is sufficient. No separate synthesis cache needed.
- **D-06:** Separate `ANTHROPIC_GENERATE_MODEL` env var for the generator model, distinct from the classifier's `ANTHROPIC_MODEL`. Allows users to use a smarter model (e.g., Sonnet) for synthesis while keeping Haiku for classification.

### Classification Failures
- **D-07:** Remove the fake fallback record on JSON parse failure. When Claude returns unparseable JSON, log a warning, increment `_failed_count`, and return `None` — do not create a `ClassifiedComment` with `category='other'`, `confidence=0.0`, `summary='classification failed'`.
- **D-08:** On startup, `PRClassifier._load_index()` filters out entries where `summary == 'classification failed'` from `classification-index.json`. These comments get fresh API calls on the next classify run. Self-healing behavior.
- **D-09:** `classify_pr()` already overwrites `classified-pr-N.json` with fresh results, so cleaning the index is sufficient — failed entries naturally disappear from classified files.

### CLI Output Accuracy
- **D-10:** Generate command reports detailed breakdown: new articles / skipped (already in KB) / filtered (below confidence threshold) / failed (synthesis error).
- **D-11:** Classify command reports detailed breakdown: new / cached / need review / failed.
- **D-12:** Exit code 0 for partial failures (some articles failed), exit code 1 only for total pipeline failure (missing config, no cache, API auth error). Warnings printed to stderr for partial failures.

### Low-Value Filtering
- **D-13:** All categories generate articles (including 'other') — no category-based filtering.
- **D-14:** Minimum confidence threshold of 0.5 below which no article is generated. Configurable via `MIN_CONFIDENCE` env var. Confidence >= 0.75 = normal article, 0.50-0.74 = article + [review] tag, < 0.50 = filtered out. Filtered count shown in CLI output.

### Synthesis Error Handling
- **D-15:** On synthesis failure (Claude API error or bad output), skip the article and report. Do not write any article, do not add to manifest. Comment will be retried on next run since it's not in the manifest. No fallback to raw comment copy.

### Existing KB Cleanup
- **D-16:** Add `--regenerate` flag to the `generate` command. When set, clears the manifest and deletes existing article files, then re-synthesizes all articles from scratch. Default behavior leaves existing articles alone and only processes new comments.

### Generator API Key
- **D-17:** Generate command requires `ANTHROPIC_API_KEY` (or the generate-specific model key). Fails fast with a clear error if missing, same pattern as the classify command.

### Claude's Discretion
- Synthesis prompt engineering — exact prompt wording, max_tokens, and temperature for article synthesis
- Error message wording for missing API key in generate command
- How `--regenerate` cleans up existing files (delete category dirs vs. individual files)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Core Implementation Files
- `src/github_pr_kb/generator.py` — KBGenerator class, `_build_article()` method to be replaced with Claude synthesis
- `src/github_pr_kb/classifier.py` — PRClassifier, `_classify_comment()` fallback record to remove, `_load_index()` to add cleanup
- `src/github_pr_kb/cli.py` — CLI commands, `_run_generate()` and `_run_classify()` summary strings to fix
- `src/github_pr_kb/config.py` — Settings class, needs new `anthropic_generate_model` and `min_confidence` fields
- `src/github_pr_kb/models.py` — Pydantic models, `GenerateResult` may need new fields for filtered count

### Project Standards
- `.claude/rules/clean-code.md` — Clean code standards to follow
- `.claude/rules/python-typing.md` — Python 3.13 type hinting standards
- `.claude/rules/ruff-after-python.md` — Must run ruff after any Python changes

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_write_atomic()` — Atomic file write pattern (exists in both classifier.py and generator.py)
- `slugify()` — URL-safe slug generation for article filenames
- `GenerateResult` model — Can be extended with `filtered` count field
- `ConfigurationError` in cli.py — Reusable for generate's API key requirement

### Established Patterns
- Lazy imports inside command bodies (cli.py) — prevents --help from crashing without env vars
- `PRClassifier.__init__` reads settings lazily — generator should follow same pattern for API key
- Manifest-based dedup in KBGenerator — comment_id → article path mapping
- `_write_atomic` for all file writes — must continue using this pattern

### Integration Points
- `KBGenerator._build_article()` — Replace with Claude synthesis call
- `KBGenerator.__init__()` — Needs Anthropic client initialization (like PRClassifier)
- `PRClassifier._classify_comment()` — Remove fake fallback on JSON parse failure (lines 162-167)
- `PRClassifier._load_index()` — Add filtering of "classification failed" entries
- `_run_generate()` in cli.py — Update summary string format
- `_run_classify()` in cli.py — Update summary string format
- `config.py Settings` — Add `anthropic_generate_model`, `min_confidence` fields

</code_context>

<specifics>
## Specific Ideas

- Article synthesis uses category-specific templates with distinct section headings per category (see D-02 for exact structure)
- The `--regenerate` flag on `generate` allows users to upgrade existing KB after this phase ships
- Self-healing classification: failed entries auto-retry on next run without manual intervention

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-fix-article-generation-quality*
*Context gathered: 2026-04-07*
