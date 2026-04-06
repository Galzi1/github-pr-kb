---
phase: 05-kb-generator
plan: 02
subsystem: kb-generator
tags: [index-generation, tdd, kb-03, kb-04]
dependency_graph:
  requires: ["05-01"]
  provides: ["kb/INDEX.md generation", "_generate_index method", "KB-03 complete", "KB-04 finalized"]
  affects: ["06-cli (calls generate_all which now produces INDEX.md)"]
tech_stack:
  added: []
  patterns:
    - "YAML frontmatter line-by-line parsing (no third-party YAML library)"
    - "rglob scan for index rebuild (D-14 full regeneration)"
    - "needs_review parsed as string comparison to avoid bool coercion bugs (R3 mitigation)"
    - "category.replace('_', ' ').title() for display names (D-12)"
key_files:
  created: []
  modified:
    - src/github_pr_kb/generator.py
    - tests/test_generator.py
decisions:
  - "needs_review field parsed via string comparison (value.strip().lower() == 'true') not bool cast — R3 risk mitigation to avoid silent [review] marker loss"
  - "_parse_article_metadata extracted as private helper for single-responsibility and testability"
  - "INDEX.md produced even when KB is empty (just title, no headings) — R3 mitigation for empty-run robustness"
metrics:
  duration: "4 min"
  completed: "2026-04-06T06:56:55Z"
  tasks_completed: 1
  files_modified: 2
---

# Phase 05 Plan 02: Index Generation Summary

**One-liner:** KB/INDEX.md generation with category groupings, article counts, markdown links, and [review] markers — regenerated from scratch on every generate_all() call.

## Tasks Completed

| # | Task | Commit | Status |
|---|------|--------|--------|
| 1 | Index generation tests + implementation | f443056 (impl), 487805f (tests) | DONE |

## What Was Built

### `_generate_index(self) -> None` in `KBGenerator`

Scans all `.md` files in `kb/` subdirectories (one level deep, excluding `INDEX.md`), parses each article's YAML frontmatter using a line-by-line approach (no third-party YAML library), groups entries by category, and writes `kb/INDEX.md` atomically.

**Index format:**
```
# Knowledge Base Index

## Code Pattern (1)

- [Use dependency injection to avoid tight coupling](code_pattern/use-dependency-injection.md)

## Gotcha (1)

- [Avoid circular imports in middleware](gotcha/avoid-circular-imports-in-middleware.md) [review]
```

Key behaviors:
- Category headings: `## {Category Name Title-Cased} ({count})` — e.g., "## Architecture Decision (3)"
- Articles sorted alphabetically by filename within each category
- Categories sorted alphabetically
- `needs_review=true` articles get ` [review]` appended after the markdown link
- Empty KB produces INDEX.md with title only (no category headings) — R3 robustness mitigation
- INDEX.md regenerated from scratch every run (not incrementally appended) — D-14

### `_parse_article_metadata(self, text: str) -> tuple[dict[str, str] | None, str]`

Private helper that parses YAML frontmatter and extracts the first `# ` heading (used as summary in the index). Returns `None` for the dict if frontmatter delimiters not found (Pitfall 5 handling — log warning, skip file).

### `generate_all()` updated

Calls `self._generate_index()` after `self._save_manifest()` and before returning `GenerateResult`. This ensures INDEX.md is always regenerated even when no new articles were written (D-14, D-16).

## Tests Added (7 new tests)

| Test | Behavior Verified |
|------|-------------------|
| `test_index_file_created` | INDEX.md exists after generate_all() (D-11) |
| `test_index_grouped_by_category` | "## Gotcha (1)" heading present (D-12) |
| `test_index_review_marker` | [review] on needs_review=True entry line (D-13) |
| `test_index_regenerated_on_rerun` | Two runs produce identical INDEX.md (D-14) |
| `test_index_multiple_categories` | Two ## headings for two categories |
| `test_index_entry_has_summary_and_link` | Markdown link format `- [summary](cat/slug.md)` |
| `test_index_empty_kb` | Title only when no articles exist (R3 mitigation) |

Full suite: **71 passed, 6 skipped** (6 skipped = integration tests needing real GitHub token).

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — INDEX.md content is fully wired from real article frontmatter.

## Self-Check: PASSED

- `src/github_pr_kb/generator.py` — contains `def _generate_index`, `self._generate_index()`, `INDEX.md`, `.replace("_", " ").title()`
- `tests/test_generator.py` — contains all 7 required test functions
- Commits exist: 487805f (tests RED), f443056 (implementation GREEN)
- Full test suite: 71 passed, 0 failures
