# Phase 5: KB Generator - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 05-kb-generator
**Areas discussed:** Article content & format, File naming & structure, Index file design, Incremental merge strategy, Slug generation rules, KB output directory init, Error handling

---

## Article Content & Format

### How much content should each KB article contain?

| Option | Description | Selected |
|--------|-------------|----------|
| Summary + full body | YAML frontmatter with metadata, one-line summary as heading, full original comment body below | :heavy_check_mark: |
| Summary only | Just the one-line AI summary in the article body | |
| Full body only | Original comment as-is, with metadata in frontmatter only | |

**User's choice:** Summary + full body (Recommended)
**Notes:** None

### How much PR context should each article include?

| Option | Description | Selected |
|--------|-------------|----------|
| PR link + title + author | Frontmatter includes PR URL, PR title, comment author, and date | :heavy_check_mark: |
| Minimal -- PR link only | Just the PR URL in frontmatter | |
| Rich -- include diff hunk | Also embed the diff_hunk for review comments | |

**User's choice:** Custom -- PR link + title + author always in frontmatter, plus diff_hunk only for review comments where it exists
**Notes:** User specified diff_hunk should only be included when it's critical for understanding, which maps to review comments that have a diff_hunk attached.

### Should needs_review articles be handled differently?

| Option | Description | Selected |
|--------|-------------|----------|
| Flag in frontmatter only | Add needs_review: true to YAML frontmatter, appear normally in KB | :heavy_check_mark: |
| Separate directory | Put needs_review articles in kb/needs_review/ | |
| Exclude from KB | Don't generate articles for low-confidence classifications | |

**User's choice:** Flag in frontmatter only (Recommended)
**Notes:** None

### Should 'other' category comments be included?

| Option | Description | Selected |
|--------|-------------|----------|
| Include in kb/other/ | Generate articles for 'other' category too | :heavy_check_mark: |
| Skip entirely | Don't generate KB articles for 'other' category | |

**User's choice:** Include in kb/other/ (Recommended)
**Notes:** None

---

## File Naming & Structure

### How should KB article files be named?

| Option | Description | Selected |
|--------|-------------|----------|
| pr{N}-c{ID}.md | Deterministic from data, sortable by PR | |
| Slug from summary | Human-friendly slugified summary | :heavy_check_mark: |
| Date + comment ID | Chronologically sortable | |

**User's choice:** Slug from summary
**Notes:** User preferred human-readable filenames over deterministic IDs.

### Slug collision handling?

| Option | Description | Selected |
|--------|-------------|----------|
| Append -N suffix | E.g. avoid-circular-imports-2.md | :heavy_check_mark: |
| Combine into one article | Merge same-slug comments | |

**User's choice:** Separate with -N suffix
**Notes:** User initially asked about combining articles. After discussing trade-offs (muddy frontmatter, complex incremental merge, edge case frequency), agreed that combining is better as a v2 topic-aggregation feature. Chose -N suffix for MVP.

### Article granularity?

| Option | Description | Selected |
|--------|-------------|----------|
| One article per comment | Each classified comment becomes its own .md file | :heavy_check_mark: |
| One article per PR | All classified comments from same PR grouped together | |

**User's choice:** One article per comment (Recommended)
**Notes:** None

---

## Index File Design

### How should the index file be structured?

| Option | Description | Selected |
|--------|-------------|----------|
| Grouped by category | Sections per category with article links and summaries | :heavy_check_mark: |
| Flat table | Single markdown table with all articles | |
| Both | Category sections + flat table | |

**User's choice:** Grouped by category (Recommended)
**Notes:** None

### How should needs_review articles appear in the index?

| Option | Description | Selected |
|--------|-------------|----------|
| Inline with marker | Appear in category section with [review] marker | :heavy_check_mark: |
| Separate section at bottom | Dedicated Needs Review section | |

**User's choice:** Inline with marker (Recommended)
**Notes:** None

### Where should the index file live?

| Option | Description | Selected |
|--------|-------------|----------|
| kb/INDEX.md | Inside KB output directory | :heavy_check_mark: |
| kb/README.md | Named README.md for GitHub rendering | |

**User's choice:** kb/INDEX.md (Recommended)
**Notes:** None

---

## Incremental Merge Strategy

### How to track existing articles for dedup?

| Option | Description | Selected |
|--------|-------------|----------|
| Scan frontmatter for comment_id | Parse YAML frontmatter of existing .md files | |
| Manifest file | kb/.manifest.json mapping comment_id -> filename | :heavy_check_mark: |
| Always overwrite | Regenerate all articles from scratch | |

**User's choice:** Manifest file
**Notes:** None

### Should index be regenerated or incrementally updated?

| Option | Description | Selected |
|--------|-------------|----------|
| Full regeneration | Rebuild INDEX.md completely from all .md files each run | :heavy_check_mark: |
| Incremental append | Only add new entries | |

**User's choice:** Full regeneration (Recommended)
**Notes:** None

### Where should KB output directory default to?

| Option | Description | Selected |
|--------|-------------|----------|
| kb/ in project root | Simple default, CLI can override later | |
| Configurable via Settings | Add kb_output_dir field to Settings | :heavy_check_mark: |

**User's choice:** Configurable via Settings
**Notes:** None

---

## Slug Generation Rules

### Max slug length?

| Option | Description | Selected |
|--------|-------------|----------|
| 60 characters | Descriptive enough, avoids filesystem issues | :heavy_check_mark: |
| 40 characters | Shorter, more truncation | |
| No limit | Risk of long filenames on Windows | |

**User's choice:** 60 characters (Recommended)
**Notes:** None

### Unicode handling?

| Option | Description | Selected |
|--------|-------------|----------|
| Strip to ASCII | Transliterate unicode to ASCII | :heavy_check_mark: |
| Allow unicode in filenames | Keep unicode characters | |

**User's choice:** Strip to ASCII (Recommended)
**Notes:** None

---

## KB Output Directory Init

### Category subdirectory creation?

| Option | Description | Selected |
|--------|-------------|----------|
| On demand | Create only when first article in category is written | :heavy_check_mark: |
| Upfront for all categories | Create all 5 category dirs at start | |

**User's choice:** On demand (Recommended)
**Notes:** None

---

## Error Handling

### Behavior on malformed input?

| Option | Description | Selected |
|--------|-------------|----------|
| Log warning, skip, continue | Warning + skip + summary at end | |
| Fail fast | Raise error on first bad entry | |
| Skip silently | Ignore bad entries with no output | |

**User's choice:** Custom -- Log warnings and continue, but track failures explicitly as "failed" (not "skipped"), classified by failure type. Generator returns result summary distinguishing successes from failures with reasons.
**Notes:** User emphasized that problematic items should be "correctly classified as failed" with their respective failure type, not described as skipped.

---

## Claude's Discretion

- YAML frontmatter field ordering
- Slug implementation details (stop words, edge cases)
- Warning/log message format
- Internal class/function structure

## Deferred Ideas

- **Topic aggregation** -- Combining articles with similar slugs into merged articles. Noted as v2 feature after user initially asked about combining collisions.
