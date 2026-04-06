# Phase 5: KB Generator - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Transform classified PR comments (from `classified-pr-N.json` files) into an organized markdown knowledge base with per-category subdirectories, YAML frontmatter, an index file, and incremental merge so re-runs don't duplicate content.

Requirements: KB-01, KB-02, KB-03, KB-04

</domain>

<decisions>
## Implementation Decisions

### Article Content & Format
- **D-01:** Each KB article contains the AI one-line summary as the heading, followed by the full original comment body below it.
- **D-02:** YAML frontmatter always includes: PR link, PR title, comment author, date, category, confidence score, needs_review flag, and comment_id.
- **D-03:** For review comments that have a `diff_hunk`, embed it in the article body (below the comment) so code context is visible. Issue comments (no diff_hunk) omit this section.
- **D-04:** needs_review articles (confidence < 75%) are included in the KB like normal articles, with `needs_review: true` in frontmatter. No separate directory.
- **D-05:** "other" category comments are included in `kb/other/` — not excluded.

### File Naming & Structure
- **D-06:** One article per classified comment (not grouped by PR).
- **D-07:** File names are slugified from the AI summary. E.g., `avoid-circular-imports.md`.
- **D-08:** Slug rules: lowercase, ASCII-only (transliterate unicode), hyphens for spaces/special chars, max 60 characters, truncate at word boundary.
- **D-09:** Slug collisions resolved with `-N` numeric suffix. E.g., `avoid-circular-imports-2.md`.
- **D-10:** Category subdirectories created on demand (only when first article in that category is written). No empty dirs.

### Index File
- **D-11:** Index lives at `kb/INDEX.md`.
- **D-12:** Index grouped by category with `## Category Name (count)` headings. Each entry is a link + one-line summary.
- **D-13:** needs_review articles appear inline in their category with a `[review]` marker.
- **D-14:** Index is fully regenerated from all existing .md files on every run (not incrementally appended).

### Incremental Merge
- **D-15:** Dedup via manifest file at `kb/.manifest.json` mapping comment_id -> relative file path.
- **D-16:** On each run: load manifest, skip known comment_ids, write new articles, update manifest, then regenerate INDEX.md.
- **D-17:** KB output directory is configurable via `kb_output_dir` field in Settings (config.py), defaulting to `kb/`.

### Error Handling
- **D-18:** Malformed classified JSON files or unprocessable comments log a warning (identifying the problem file/comment and failure type), continue processing remaining items.
- **D-19:** Failures are tracked explicitly with their type — not silently skipped. Generator returns a result summary distinguishing successful articles from failed entries (with failure reason).

### Claude's Discretion
- Exact YAML frontmatter field ordering
- Slug generation implementation details (stop words, edge cases beyond the rules above)
- Exact warning/log message format for failures
- Internal class/function structure of the generator module

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Data Models
- `src/github_pr_kb/models.py` -- Defines ClassifiedComment, ClassifiedFile, PRRecord, CommentRecord, CategoryLiteral. These are the input data structures the generator consumes.

### Classifier (Upstream)
- `src/github_pr_kb/classifier.py` -- PRClassifier.classify_pr() writes `classified-pr-N.json` files. Generator reads these. Shows atomic write pattern (mkstemp + os.replace) to reuse.

### Configuration
- `src/github_pr_kb/config.py` -- Settings class where `kb_output_dir` field will be added (D-17).

### Generator Stub
- `src/github_pr_kb/generator.py` -- Current stub file where implementation goes.

### Requirements
- `.planning/REQUIREMENTS.md` -- KB-01 through KB-04 define acceptance criteria for this phase.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `models.py`: ClassifiedComment and ClassifiedFile are the input models -- already have comment_id, category, confidence, summary, needs_review, classified_at fields
- `models.py`: PRRecord has number, title, url, state -- used for frontmatter PR context
- `models.py`: CommentRecord has author, body, created_at, url, file_path, diff_hunk -- needed for article content
- Atomic write pattern from classifier.py (mkstemp + os.replace) can be reused for KB file writes

### Established Patterns
- `ConfigDict(extra='ignore')` on all Pydantic models -- maintain this for any new models
- Literal type aliases (not Enum) for category values
- JSON serialization via `model_dump(mode="json")` for cache/manifest files
- Settings class with pydantic-settings for environment/config

### Integration Points
- Generator reads `classified-pr-N.json` from the cache directory (same dir classifier writes to)
- Generator writes to a separate `kb/` output directory (or configured path)
- `generator.py` stub exists and will be the implementation file
- Phase 6 (CLI) will call the generator as `github-pr-kb generate`

</code_context>

<specifics>
## Specific Ideas

- User wants diff_hunk included only for review comments that have one -- not all articles, just where code context matters
- Failures should be "classified as failed" with their type, not described as "skipped" -- explicit failure tracking with reason
- Slug-based filenames chosen for human readability over deterministic IDs
- Topic aggregation (combining same-slug articles) noted as potential v2 feature

</specifics>

<deferred>
## Deferred Ideas

- **Topic aggregation / article combining** -- When multiple comments produce similar slugs, intelligently merge them into a single article. More of a v2 "smart grouping" feature than simple slug collision handling.

</deferred>

---

*Phase: 05-kb-generator*
*Context gathered: 2026-04-05*
