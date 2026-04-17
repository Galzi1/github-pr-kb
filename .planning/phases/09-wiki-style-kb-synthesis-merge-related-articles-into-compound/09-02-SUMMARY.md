---
phase: 09-wiki-style-kb-synthesis-merge-related-articles-into-compound
plan: "02"
subsystem: kb-generator
tags: [topic-synthesis, cross-references, tdd, in-memory-pipeline]
completed_at: "2026-04-17T10:50:00Z"
duration_min: 9
tasks_completed: 2
files_modified: 2

dependency_graph:
  requires:
    - TopicGroup/TopicPlan models (09-01)
    - _plan_topics, _sources_hash (09-01)
    - Nested manifest format (09-01)
  provides:
    - _collect_in_memory_articles: in-memory article collection (no disk writes)
    - _build_topic_synthesis_prompt: prompt builder with PR citations and cross-ref slugs
    - _build_topic_page: per-topic Claude synthesis with minimal frontmatter
    - _synthesize_topics: full orchestration with content hash skip
    - _strip_broken_links: cross-reference validation via CROSS_REF_RE
    - TOPIC_SYNTHESIS_SYSTEM_PROMPT constant
    - CROSS_REF_RE module-level regex constant
    - GenerateResult.topics_written / topics_skipped fields
  affects:
    - src/github_pr_kb/generator.py
    - tests/test_generator.py

tech_stack:
  added:
    - python-frontmatter (used via frontmatter.Post + frontmatter.dumps for topic page frontmatter)
  patterns:
    - In-memory article pipeline: classify -> collect -> plan -> synthesize (no intermediate .md files)
    - Content hash skip: _sources_hash compared against manifest["topics"][slug]["content_hash"]
    - Minimal frontmatter: only title/category/last_updated/needs_review (no pr_url/comment_id/confidence/author)
    - CROSS_REF_RE regex isolates ../category/slug.md relative links for validation

key_files:
  created: []
  modified:
    - src/github_pr_kb/generator.py
    - tests/test_generator.py

decisions:
  - _strip_broken_links uses re.Match.group(1) for display text, strips ../prefix and .md suffix to get category/slug key for valid_slugs lookup
  - _build_topic_page uses frontmatter.Post + frontmatter.dumps for reliable YAML output; H1 heading injected after closing --- delimiter if not already present
  - TopicGroup imported at module level (not local import) to satisfy F821 ruff check
  - article dict values typed as object in list[dict[str, object]] - str() casts used at prompt-build time to satisfy type checker without Any

metrics:
  duration: 9 min
  completed_date: "2026-04-17"
---

# Phase 09 Plan 02: Topic Synthesis Pass and Cross-Reference Validation Summary

**One-liner:** In-memory article collection pipeline feeding Claude-driven topic synthesis with category templates, inline PR citations, content hash skipping, and CROSS_REF_RE broken-link stripping.

## What Was Built

### Task 1: _collect_in_memory_articles, _build_topic_page, _synthesize_topics (commit ccc9e48)

Added to `generator.py`:

- `TOPIC_SYNTHESIS_SYSTEM_PROMPT`: instructs Claude to preserve all info, cite PRs inline, use cross-ref link format
- `import frontmatter` added at module level
- `TopicGroup` added to module-level imports from models
- `GenerateResult` extended with `topics_written: int = 0` and `topics_skipped: int = 0`
- `_collect_in_memory_articles()`: iterates classified files, filters by min_confidence, returns list of in-memory article dicts (key, category, summary, pr_title, pr_url, author, date, body, needs_review). Nothing written to disk (per D-06).
- `_build_topic_synthesis_prompt()`: builds user prompt with all source bodies (truncated to 10,000 chars each), category-specific section headings from `_CATEGORY_SECTIONS`, PR title/url/author/date for inline citation (per D-01, D-02), and full list of known topic slugs for cross-referencing (per D-10)
- `_build_topic_page()`: calls Claude with `TOPIC_SYNTHESIS_SYSTEM_PROMPT`, extracts body, checks source echo, builds minimal frontmatter via `frontmatter.Post` (title/category/last_updated/needs_review only, per D-03), injects `# {title}` H1 heading. Single-source topics use identical code path (per D-04).
- `_synthesize_topics()`: orchestrates full pipeline - collect articles → plan topics → for each group: compute content hash, skip if unchanged (per D-08), synthesize page, strip broken links, write to disk, update `manifest["topics"]` and `manifest["comments"]`
- Stub `_strip_broken_links()` added (pass-through) for Task 1 green phase
- 15 new tests covering all behaviors

### Task 2: _strip_broken_links with CROSS_REF_RE (commit 3e112ff)

Added to `generator.py`:

- `CROSS_REF_RE = re.compile(r"\[([^\]]+)\]\((\.\./[^)]+\.md)\)")`: module-level regex matching relative cross-reference links only (excludes http/https external links)
- `_strip_broken_links(body, valid_slugs)`: replaces stub - uses `CROSS_REF_RE.sub()` with inner `_replace` function that strips `../` prefix and `.md` suffix from link target, checks against `valid_slugs` set, returns plain display text for broken links and original match for valid ones
- Wired into `_synthesize_topics` after each `_build_topic_page` call, with `valid_slugs` built from all TopicGroup entries in the plan
- 6 new tests: valid link preserved, broken link stripped to plain text, external URL untouched, multiple broken links all stripped, called in _synthesize_topics, CROSS_REF_RE constant exists

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `TopicGroup` string forward reference caused F821 ruff error**
- **Found during:** Task 1 ruff check
- **Issue:** Method signatures `group: "TopicGroup"` used string annotation because TopicGroup was only imported locally inside methods. Ruff flagged F821 (undefined name in string annotation).
- **Fix:** Added `TopicGroup` to the module-level import from `github_pr_kb.models`; removed local imports; changed annotations to `group: TopicGroup` (no quotes).
- **Files modified:** src/github_pr_kb/generator.py
- **Commit:** ccc9e48

**2. [Rule 1 - Bug] Long lines and unused variable in test file**
- **Found during:** Task 1 ruff check (E501 line-too-long, F841 unused variable)
- **Issue:** Inline article dicts in tests exceeded 140-char limit; `result = gen._build_topic_page(...)` assigned but unused in one test.
- **Fix:** Reformatted all long article dicts to multi-line format; removed unused `result` assignment.
- **Files modified:** tests/test_generator.py
- **Commit:** ccc9e48

## Threat Mitigations Applied

Per threat register:

- **T-09-04** (Tampering - Claude-generated cross-ref links): `_strip_broken_links` validates all `../category/slug.md` links against `valid_slugs` set derived from the current `TopicPlan`; broken links converted to plain display text (per D-11)
- **T-09-06** (DoS - large topic groups): Source comment bodies truncated to 10,000 chars each in `_build_topic_synthesis_prompt`, matching the existing `_build_synthesis_prompt` pattern

## Known Stubs

None - `_strip_broken_links` stub from Task 1 was replaced with full implementation in Task 2. All new code paths have real implementations (stub behavior only in tests via MagicMock).

## Threat Flags

None - no new network endpoints, auth paths, file access patterns, or schema changes beyond what the plan's threat model already covers.

## Self-Check: PASSED

- `src/github_pr_kb/generator.py` - `_synthesize_topics`, `_build_topic_page`, `_collect_in_memory_articles`, `TOPIC_SYNTHESIS_SYSTEM_PROMPT`, `_strip_broken_links`, `CROSS_REF_RE`, `import frontmatter`, `topics_written` all present
- `tests/test_generator.py` - 21 new tests added across Tasks 1 and 2; 72/72 pass
- Commits ccc9e48 and 3e112ff exist in git log
- 0 ruff errors
