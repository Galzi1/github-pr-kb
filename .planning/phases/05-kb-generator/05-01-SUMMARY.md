---
phase: 05-kb-generator
plan: 01
subsystem: generator
tags: [python, pydantic, markdown, yaml, slug, manifest, dedup, kb]

# Dependency graph
requires:
  - phase: 04-claude-classifier
    provides: "ClassifiedFile/ClassifiedComment models + classified-pr-N.json cache files"
  - phase: 02-github-extraction-core
    provides: "PRFile/CommentRecord models + pr-N.json cache files"
provides:
  - "KBGenerator class generating per-category markdown articles from classified comments"
  - "slugify() function for ASCII-safe, word-boundary-truncated file names"
  - "_yaml_str() helper for safe YAML frontmatter string quoting"
  - "GenerateResult model with written/skipped/failed counts"
  - "manifest-based incremental dedup (kb/.manifest.json, comment_id -> rel_path)"
  - "kb_output_dir config field in Settings (default: 'kb')"
  - "22 unit tests covering KB-01, KB-02, KB-04"
affects: [05-02, 06-cli, phase-6]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "KBGenerator class mirrors PRClassifier shape: constructor + private methods + public generate_all()"
    - "settings imported inside __init__ to avoid import-time ValidationError during tests"
    - "_write_atomic copied into generator.py (not imported from classifier) to avoid cross-module coupling"
    - "Manifest keys are str(comment_id) for JSON round-trip consistency (not int)"
    - "_resolve_slug checks both manifest values and filesystem for collision detection (D-09)"

key-files:
  created:
    - src/github_pr_kb/generator.py
    - tests/test_generator.py
  modified:
    - src/github_pr_kb/config.py

key-decisions:
  - "KBGenerator._resolve_slug checks both manifest and filesystem for collision — Pitfall 2 from research"
  - "generator.py copies _write_atomic from classifier.py (not imports) to avoid cross-module coupling"
  - "settings imported inside KBGenerator.__init__ (not at module level) to prevent import-time ValidationError in tests"
  - "Manifest keys stored as str(comment_id) — JSON always deserializes object keys as str, so int lookup would always miss"

patterns-established:
  - "slugify: NFKD normalize + ASCII encode + re.sub non-alphanumeric + truncate at rfind('-') word boundary"
  - "_yaml_str: double-quote wrapping with backslash/quote/newline escaping for safe YAML frontmatter"
  - "GenerateResult Pydantic model with ConfigDict(extra='ignore') for D-19 failure tracking"
  - "per-category directory created on demand (mkdir parents=True, exist_ok=True) — D-10"
  - "diff_hunk appended as fenced code block only when comment.diff_hunk is truthy — D-03"

requirements-completed: [KB-01, KB-02, KB-04]

# Metrics
duration: 6min
completed: 2026-04-06
---

# Phase 05 Plan 01: KB Generator Core Summary

**KBGenerator class that converts classified PR comments into per-category markdown articles with 9-field YAML frontmatter, diff_hunk embedding, and manifest-based incremental dedup — 22 unit tests, all green**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-06T07:39:29Z
- **Completed:** 2026-04-06T07:45:38Z
- **Tasks:** 2 (TDD RED+GREEN combined)
- **Files modified:** 3

## Accomplishments

- KBGenerator reads all `classified-pr-N.json` files and writes markdown articles into per-category subdirectories (`gotcha/`, `code_pattern/`, etc.)
- Each article has complete 9-field YAML frontmatter (pr_url, pr_title, comment_url, author, date, category, confidence, needs_review, comment_id) with correct double-quoting for string values
- Review comments with diff_hunk get the hunk embedded as a fenced code block; issue comments do not
- Manifest at `kb/.manifest.json` maps str(comment_id) -> relative path for incremental dedup — second run returns written=0, skipped=N
- Malformed classified JSON files are logged as warnings with typed failure records; generator continues processing remaining files

## Task Commits

Each task was committed atomically:

1. **Task 1: Test scaffolds + slugify + config kb_output_dir** - `bbd7a31` (feat)
   - Included full KBGenerator implementation (GREEN achieved in one commit per TDD flow)

**Plan metadata:** (docs commit follows)

_Note: Both TDD tasks executed in a single GREEN commit since generator.py was written holistically after RED phase for all 22 tests._

## Files Created/Modified

- `src/github_pr_kb/generator.py` - KBGenerator class, GenerateResult model, slugify(), _yaml_str(), _write_atomic(), DEFAULT_CACHE_DIR (343 lines)
- `tests/test_generator.py` - 22 unit tests covering KB-01, KB-02, KB-04 (538 lines)
- `src/github_pr_kb/config.py` - Added kb_output_dir: str = "kb" field to Settings

## Decisions Made

- **str(comment_id) manifest keys:** JSON always deserializes object keys as str; int lookup would always miss (Pitfall 1 from research). Enforced consistently throughout.
- **_resolve_slug checks both manifest and filesystem:** Slug collision detection must handle both previously-written articles (in manifest) and filesystem files (for portability). Checks both per Pitfall 2.
- **settings imported inside __init__:** Avoids import-time ValidationError in test contexts where only a subset of env vars is set.
- **_write_atomic copied (not imported) from classifier.py:** Avoids cross-module coupling between classifier and generator as recommended in research.

## Deviations from Plan

None - plan executed exactly as written. Both tasks completed in the planned order with all acceptance criteria met.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Generator uses only stdlib + existing project dependencies.

## Next Phase Readiness

- KBGenerator fully functional — ready for Phase 05 Plan 02 (INDEX.md generation, KB-03)
- Phase 06 (CLI) can call `KBGenerator(cache_dir=...).generate_all()` directly
- No blockers

---
*Phase: 05-kb-generator*
*Completed: 2026-04-06*

## Self-Check: PASSED

Files verified:
- FOUND: src/github_pr_kb/generator.py (343 lines, KBGenerator class present)
- FOUND: tests/test_generator.py (538 lines, 22 tests all passing)
- FOUND: src/github_pr_kb/config.py (kb_output_dir field present)
- FOUND commit bbd7a31 in git log
- All 22 generator tests pass; full suite 64 passed, 6 skipped (integration)
