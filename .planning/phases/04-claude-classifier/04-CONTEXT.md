# Phase 4: Claude Classifier - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Classify cached PR comments into categories (architecture_decision, code_pattern, gotcha, domain_knowledge, other) using Claude AI, with confidence scoring, content-hash dedup to avoid redundant API calls, and review flagging for low-confidence results.

</domain>

<decisions>
## Implementation Decisions

### Classification Storage
- **D-01:** Classification results are stored in **separate files** (`classified-pr-N.json`) alongside the existing extraction cache (`pr-N.json`) in the same `.github-pr-kb/cache/` directory. This keeps extraction and classification data independent.
- **D-02:** A new `ClassifiedComment` Pydantic model holds: `comment_id`, `category`, `confidence`, `summary`, `classified_at`, `needs_review`.

### API Call Strategy
- **D-03:** **One comment per Claude API call.** Simple, reliable, easy to cache and retry individually. Aligns with CLASS-03 per-comment caching and the existing comment_id-based dedup philosophy.

### Content Hash Dedup (CLASS-03)
- **D-04:** **SHA-256 hash of comment body** for cross-PR dedup. Only truly identical comments share a classification result — no fuzzy matching.
- **D-05:** A single **`classification-index.json`** file in the cache directory maps `body_hash -> {category, confidence, summary, classified_at}`. Loaded once at the start of a classify run, checked before each API call, appended with new entries after each successful classification.

### Review Flagging (CLASS-02)
- **D-06:** `needs_review: bool` field on `ClassifiedComment` — set to `true` when `confidence < 0.75`.
- **D-07:** The classify command prints a summary at the end showing total classified, cache hits, and how many items need review.

### Claude's Discretion
- Prompt design (system prompt, output format, structured output vs free-text parsing)
- Claude model selection (haiku for cost, sonnet for quality — Claude decides based on classification complexity)
- Error handling strategy for failed API calls (retry logic, partial failure behavior)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — CLASS-01 through CLASS-04 define the classification requirements

### Existing Code
- `src/github_pr_kb/models.py` — Existing CommentRecord, PRRecord, PRFile models (classification model must reference comment_id from CommentRecord)
- `src/github_pr_kb/config.py` — Settings class where `anthropic_api_key` needs to be added (placeholder comment already exists at line 15)
- `src/github_pr_kb/classifier.py` — Empty stub file where classifier implementation goes
- `src/github_pr_kb/extractor.py` — GitHubExtractor with cache write patterns (atomic writes, merge logic) to follow as reference

### Project Decisions
- `.planning/STATE.md` §Decisions — Cache invalidation strategy, stack decisions, prior phase patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Pydantic BaseModel pattern**: All data models use `ConfigDict(extra="ignore")` for forward compatibility — new ClassifiedComment should follow this pattern
- **Atomic file writes**: `_write_cache_atomic` in extractor.py (mkstemp + os.replace) — classifier should use the same pattern for classified-pr-N.json and classification-index.json
- **Cache directory**: `DEFAULT_CACHE_DIR = Path(".github-pr-kb/cache")` — classifier reads from and writes to the same directory

### Established Patterns
- **Module-level Settings()**: Config validated at import time — adding `anthropic_api_key` follows the same fail-fast pattern
- **Logging**: `logger = logging.getLogger(__name__)` used throughout — classifier should log classification progress and cache hits
- **Type enforcement**: `Literal` types for enums (comment_type, state) — category should use `Literal["architecture_decision", "code_pattern", "gotcha", "domain_knowledge", "other"]`

### Integration Points
- **Input**: Classifier reads `pr-N.json` files from cache directory (PRFile model)
- **Output**: Writes `classified-pr-N.json` files (new ClassifiedFile model) and updates `classification-index.json`
- **Config**: `anthropic_api_key` added to Settings in config.py
- **CLI**: Phase 6 will wire up `github-pr-kb classify` command that calls the classifier

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for prompt design and Claude model selection.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-claude-classifier*
*Context gathered: 2026-04-05*
