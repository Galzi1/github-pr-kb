---
phase: 09-wiki-style-kb-synthesis-merge-related-articles-into-compound
plan: 03
status: complete
started: 2026-04-17T15:00:00Z
completed: 2026-04-17T15:45:00Z
duration_minutes: 45
---

## Summary

Wired topic synthesis into the `generate_all()` pipeline and added the `--no-synthesize` CLI escape hatch.

## Tasks Completed

| # | Task | Status |
|---|------|--------|
| 1 | Wire synthesis into generate_all() and update _generate_index() for topic pages | ✓ |
| 2 | Add --no-synthesize flag to CLI generate command | ✓ |

## Key Changes

### Task 1: Pipeline Wiring
- Added `synthesize: bool = True` parameter to `generate_all()`, `_run_generation_pass()`, `_generate_all_transactionally()`
- `_run_generation_pass(synthesize=True)` calls `_synthesize_topics()` → `_save_manifest()` → `_generate_index()` (no per-comment files written)
- `_run_generation_pass(synthesize=False)` preserves the original per-comment article flow
- Updated `_parse_article_metadata()` to use `python-frontmatter` library for robust parsing; falls back to `# heading` for legacy articles
- INDEX.md now uses frontmatter `title` field from topic pages as display text (per D-12)
- `GenerateResult` wires `topics_written` and `topics_skipped` from `_synthesize_topics()` return

### Task 2: CLI --no-synthesize Flag
- Added `--no-synthesize` flag to `generate` command (per D-05)
- `_run_generate()` accepts `synthesize` parameter, passes to `generate_all()`
- CLI output appends "Topics: N written, M unchanged." when synthesis runs
- `run` command explicitly passes `synthesize=True`
- Updated existing scenario tests to use `--no-synthesize` since they test per-comment behavior

## Key Files

### Created
(none)

### Modified
- `src/github_pr_kb/generator.py` - synthesize parameter wiring, frontmatter-based metadata parsing
- `src/github_pr_kb/cli.py` - --no-synthesize flag, topic counts in output
- `tests/test_generator.py` - 6 new tests for synthesis pipeline, existing tests updated with synthesize=False
- `tests/test_cli.py` - 4 new tests for --no-synthesize flag and default synthesis behavior
- `tests/test_phase7_uat_envs.py` - updated manifest assertion for nested format
- `tests/support/phase7_uat_envs.py` - scenario commands use --no-synthesize for per-comment tests

## Deviations

- Tasks 1 and 2 committed together because the CLI changes were required for existing tests to pass (existing scenario tests call `generate` without `--no-synthesize`, which now defaults to synthesis mode)

## Self-Check: PASSED

- [x] `generate_all(synthesize=True)` produces topic pages, not per-comment articles
- [x] `generate_all(synthesize=False)` preserves old per-comment behavior
- [x] INDEX.md uses frontmatter title for topic pages
- [x] `--no-synthesize` CLI flag works correctly
- [x] CLI output includes topic counts when synthesis runs
- [x] All 177 tests pass, ruff clean
- [x] No regressions in existing tests
