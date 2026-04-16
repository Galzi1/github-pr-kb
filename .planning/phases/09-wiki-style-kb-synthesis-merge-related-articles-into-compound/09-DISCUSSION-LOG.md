# Phase 9: Wiki-style KB Synthesis - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 09-wiki-style-kb-synthesis-merge-related-articles-into-compound
**Areas discussed:** Topic page structure, Synthesis behavior, Manifest & migration, Cross-references & index

---

## Topic Page Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Inline PR links | Weave PR references naturally into text | ✓ |
| Sources footer section | Dedicate a ## Sources section at the bottom | |
| Both inline + footer | PR references inline AND Sources section at bottom | |

**User's choice:** Inline PR links
**Notes:** Clean reading experience, matches chronological evolution pattern from research.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Same templates | Reuse Phase 7 category-specific templates | ✓ |
| New topic-oriented templates | Design new section headings for multi-source synthesis | |
| Category + Evolution hybrid | Category sections + always append ## Timeline section | |

**User's choice:** Same templates (Phase 7 category-specific)
**Notes:** Consistent format across the KB.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Topic-level fields | title, category, source_count, source_comment_ids, date_range, last_synthesized, needs_review | |
| Preserve original + add topic | Keep pr_url, author from primary source + add topic fields | |
| Minimal frontmatter | Just category, title, source_count | |
| Drop date_range (user refined) | title, category, last_updated, needs_review | ✓ |

**User's choice:** Reader-focused minimal: title, category, last_updated, needs_review
**Notes:** User clarified that frontmatter is for readers, not bookkeeping. No source counts, comment IDs, or PR links - provenance lives in manifest only. Inline PR links already show chronological context.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Synthesize like multi-source | Same template, same format for all topics | ✓ |
| Pass through as-is | Keep Phase 7 per-comment article unchanged for single-source | |
| Lighter synthesis | Simplified prompt that enriches rather than restructures | |

**User's choice:** Synthesize like multi-source
**Notes:** Consistent output - readers don't see two different article styles.

---

## Synthesis Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Always-on | Synthesis runs every generate call, --no-synthesize escape hatch | ✓ |
| Opt-in with --synthesize | Per-comment articles are default, --synthesize for topics | |
| Separate command | New `github-pr-kb synthesize` command | |

**User's choice:** Always-on with --no-synthesize escape hatch
**Notes:** Matches research recommendation. Pipeline stays 3 steps.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Not written to disk | Per-comment articles exist only in memory | ✓ |
| Written to staging subdir | Written to kb/.staging/ for debugging | |
| Written alongside topics | Both in the KB | |

**User's choice:** Not written to disk
**Notes:** Cleaner KB directory. Classified JSON files are the source of truth.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Same model for both | Use existing ANTHROPIC_GENERATE_MODEL for planning + synthesis | ✓ |
| Separate ANTHROPIC_SYNTHESIZE_MODEL | New env var for synthesis model | |
| Hardcode Sonnet for planning | Planning always Sonnet, synthesis uses generate model | |

**User's choice:** Same model for both
**Notes:** No new env var. Users can already override via ANTHROPIC_GENERATE_MODEL.

---

## Manifest & Migration

| Option | Description | Selected |
|--------|-------------|----------|
| Nested sub-keys | {comments: {}, topics: {}} in one manifest | ✓ |
| Separate .topics.json | New file for topic state | |
| Flat with prefixed keys | comment:id and topic:slug in flat dict | |

**User's choice:** Nested sub-keys
**Notes:** One file, two sections. Research recommended this approach.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-migrate + full rebuild | Detect old format, migrate, run full synthesis | ✓ |
| Auto-migrate, synthesize incrementally | Migrate but only synthesize on new comments | |
| Require explicit --regenerate | Refuse synthesis until user runs --regenerate | |

**User's choice:** Auto-migrate + full rebuild
**Notes:** Old per-comment articles replaced by topic pages on first run. Consistent with --regenerate behavior.

---

## Cross-references & Index

| Option | Description | Selected |
|--------|-------------|----------|
| LLM-generated links | Claude adds markdown links during synthesis, given topic slug list | ✓ |
| Post-processing link injection | Scan for topic title mentions and inject links after writing | |
| No cross-references | Topic pages are standalone, navigate via INDEX.md only | |

**User's choice:** LLM-generated links
**Notes:** Synthesis prompt receives full list of topic slugs so Claude knows what's linkable.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Same format, topic entries | INDEX.md keeps same structure but links to topic pages | ✓ |
| Enhanced with source counts | Same + show source count per entry | |
| Grouped by topic clusters | Cluster related topics instead of flat category grouping | |

**User's choice:** Same format, topic entries
**Notes:** Minimal change to index generation logic. Title from topic frontmatter used as display text.

---

| Option | Description | Selected |
|--------|-------------|----------|
| Strip broken links | Validation pass converts broken links to plain text | ✓ |
| Warn but keep | Log warning but leave broken links | |
| No validation | Trust Claude to only link to valid topics | |

**User's choice:** Strip broken links
**Notes:** Cheap validation prevents 404s in the KB.

## Claude's Discretion

- Exact synthesis prompt wording and max_tokens for topic pages
- Topic planning prompt wording and JSON structure constraints
- How to handle topics that span multiple categories
- Content hash implementation details
- How chronological evolution is phrased in topic bodies

## Deferred Ideas

None - discussion stayed within phase scope.
