---
phase: 06-cli-integration
verified: 2026-04-06T14:00:00Z
status: passed
score: 8/8 must-haves verified
gaps: []
human_verification:
  - test: "Run github-pr-kb extract --repo pallets/click with a real GITHUB_TOKEN"
    expected: "Exits 0 and prints a green 'Extracted N PRs, M comments cached.' line"
    why_human: "Requires live GitHub API; mocked in tests but network path unverified"
  - test: "Run github-pr-kb --help with no env vars set"
    expected: "Exits 0 and prints top-level help without any traceback"
    why_human: "Lazy-import guard is unit-tested but end-to-end shell invocation not verifiable without a real install"
---

# Phase 6: CLI Integration Verification Report

**Phase Goal:** A user can drive the full extract -> classify -> generate pipeline through named CLI commands with clear help text and actionable error messages.
**Verified:** 2026-04-06T14:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can run `github-pr-kb extract --repo owner/name` and see a green summary line | VERIFIED | `test_extract_runs` passes; cli.py line 205 echoes green-styled "Extracted N PRs, M comments cached." |
| 2 | User can run `github-pr-kb classify` and see a green summary line | VERIFIED | `test_classify_runs` passes; cli.py line 230 echoes green-styled "Classified N comments (X new, Y cached)." |
| 3 | User can run `github-pr-kb generate` and see a green summary line | VERIFIED | `test_generate_runs` passes; cli.py line 255 echoes green-styled "Generated N articles (X new, Y skipped)." |
| 4 | User can run `github-pr-kb run --repo owner/name` and all three steps execute in sequence | VERIFIED | `test_run_pipelines` passes; cli.py lines 285-303 call all three `_run_*` helpers in order |
| 5 | All four commands respond to --help with description and all options listed | VERIFIED | All four `test_*_help` tests pass; spot-checks confirmed --repo, --state, --since, --until, --verbose, and docstrings all present |
| 6 | Missing GITHUB_TOKEN prints a human-readable error, not a traceback | VERIFIED | `test_extract_missing_token` passes; `_handle_config_error` at line 41 raises `ClickException` with "Configuration error" hint |
| 7 | Bad --since format prints a usage error with exit code 2 | VERIFIED | `test_extract_bad_date` passes; `_parse_iso_date` raises `click.UsageError` with "ISO date" text; exit code 2 confirmed via spot-check |
| 8 | `run` command fails fast if a mid-pipeline step errors | VERIFIED | `test_run_fails_fast` passes; `mock_classify_cls.assert_not_called()` and `mock_generate_cls.assert_not_called()` both pass |

**Score:** 8/8 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/github_pr_kb/cli.py` | Click group with extract, classify, generate, run commands; min 100 lines | VERIFIED | 303 lines; contains `@click.group()` on `cli`, four `@cli.command()` decorators, `_parse_iso_date`, `_configure_logging`, `_handle_config_error`, `_run_extract`, `_run_classify`, `_run_generate` |
| `tests/test_cli.py` | CliRunner tests for all commands; min 80 lines | VERIFIED | 240 lines; 12 test functions collected and passing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/github_pr_kb/cli.py` | `src/github_pr_kb/extractor.py` | `from github_pr_kb.extractor import GitHubExtractor, RateLimitExhaustedError` inside `_run_extract` | VERIFIED | Line 67 — lazy import inside function body, not module level |
| `src/github_pr_kb/cli.py` | `src/github_pr_kb/classifier.py` | `from github_pr_kb.classifier import PRClassifier` inside `_run_classify` | VERIFIED | Line 101 — lazy import inside function body, not module level |
| `src/github_pr_kb/cli.py` | `src/github_pr_kb/generator.py` | `from github_pr_kb.generator import KBGenerator` inside `_run_generate` | VERIFIED | Line 129 — lazy import inside function body, not module level |

All three backend links are lazy: no module-level `from github_pr_kb.*` imports exist in cli.py. This confirms `github-pr-kb --help` can work without any env vars set.

### Data-Flow Trace (Level 4)

CLI commands are wrappers that delegate to backend classes. Data-flow is verified through mocked unit tests. No static/hardcoded return values in the CLI layer itself — all summary strings are computed from actual return values of `extractor.extract()`, `classifier._classified_count/_cache_hit_count`, and `generator.generate_all()` result fields.

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `cli.py:_run_extract` | `paths` (list of Paths) | `GitHubExtractor.extract()` return value | Yes — count summed from actual JSON files | FLOWING |
| `cli.py:_run_classify` | `classified`, `cached` | `classifier._classified_count`, `classifier._cache_hit_count` | Yes — set by `classify_all()` execution | FLOWING |
| `cli.py:_run_generate` | `result` (GenerateResult) | `KBGenerator.generate_all()` return value | Yes — `result.written`, `result.skipped` from model | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `extract --help` exits 0 with all expected options | `CliRunner.invoke(cli, ['extract', '--help'])` | exit_code=0; --repo, --state, --since, --until, --verbose, "Extract and cache PR comments" all present | PASS |
| `classify --help` exits 0 with expected copy | `CliRunner.invoke(cli, ['classify', '--help'])` | exit_code=0; "Classify cached PR comments" present | PASS |
| `generate --help` exits 0 with expected copy | `CliRunner.invoke(cli, ['generate', '--help'])` | exit_code=0; "Generate markdown" present | PASS |
| `run --help` exits 0 with pipeline mention | `CliRunner.invoke(cli, ['run', '--help'])` | exit_code=0; "pipeline" present | PASS |
| Missing `--repo` exits 2 | `CliRunner.invoke(cli, ['extract'])` | exit_code=2 | PASS |
| Bad `--since` exits 2 with ISO date hint | `CliRunner.invoke(cli, ['extract', '--repo', 'owner/repo', '--since', 'not-a-date'])` | exit_code=2; "ISO date" in output | PASS |
| `cli` object is `click.core.Group` | `.venv/Scripts/python.exe -c "from github_pr_kb.cli import cli; print(type(cli))"` | `<class 'click.core.Group'>` | PASS |
| Full test suite passes | `.venv/Scripts/python.exe -m pytest tests/ -x` | 83 passed, 6 skipped | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| CLI-01 | 06-01-PLAN.md | User can run `github-pr-kb extract --repo owner/name` to extract and cache PR comments | SATISFIED | `extract` command exists, wired to `GitHubExtractor`, `test_extract_runs` passes, help text confirmed |
| CLI-02 | 06-01-PLAN.md | User can run `github-pr-kb classify` to classify cached comments via Claude | SATISFIED | `classify` command exists, wired to `PRClassifier`, `test_classify_runs` passes, print_summary suppression verified |
| CLI-03 | 06-01-PLAN.md | User can run `github-pr-kb generate` to write the markdown knowledge base | SATISFIED | `generate` command exists, wired to `KBGenerator`, `test_generate_runs` passes |
| CLI-04 | 06-01-PLAN.md | All commands provide clear `--help` output and actionable error messages | SATISFIED | All four `*_help` tests pass; `test_extract_missing_token` passes; `test_extract_bad_date` passes; `test_run_fails_fast` passes |

All four requirements from PLAN frontmatter are satisfied. No orphaned requirements — REQUIREMENTS.md traceability table marks CLI-01 through CLI-04 as mapped to Phase 6 and all are now Complete per ROADMAP.md success criteria.

**ROADMAP Success Criteria cross-check:**

| # | Criterion | Status |
|---|-----------|--------|
| 1 | `github-pr-kb extract --repo owner/name` runs extraction and writes the local cache | VERIFIED — wired to GitHubExtractor.extract() |
| 2 | `github-pr-kb classify` reads the cache and writes classification results | VERIFIED — wired to PRClassifier.classify_all() |
| 3 | `github-pr-kb generate` reads classification results and writes the markdown KB | VERIFIED — wired to KBGenerator.generate_all() |
| 4 | Every command responds to `--help` with description, all options, and example usage | VERIFIED — spot-checked all four commands |
| 5 | Errors print a human-readable message pointing to the fix, not a raw traceback | VERIFIED — ClickException with hints for ValidationError, bad dates, rate limit, generic failures |
| 6 | Tests covering this phase's components pass | VERIFIED — 12 CliRunner tests, all passing |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | No TODOs, FIXMEs, placeholders, or stub returns detected | — | — |

No `cli = None` stub remains. No `return null`/`return []`/`return {}` in CLI logic. No empty handlers. The `# pragma: no cover` comment on line 74 and 112 is a legitimate coverage annotation for unreachable defensive raises (not a stub).

### Human Verification Required

#### 1. Live GitHub API extraction

**Test:** Install the package with `pip install -e .`, set a real `GITHUB_TOKEN`, and run `github-pr-kb extract --repo pallets/click --state closed --since 2024-01-01`
**Expected:** Exits 0 with a green "Extracted N PRs, M comments cached." line; JSON files appear under the cache directory
**Why human:** Requires a real GitHub personal access token and live network; the CLI-to-extractor wiring is unit-tested with mocks but the real HTTP path is not exercised here

#### 2. --help works with no env vars

**Test:** Unset `GITHUB_TOKEN` and `ANTHROPIC_API_KEY` entirely, then run `github-pr-kb --help` and `github-pr-kb extract --help`
**Expected:** Both exit 0 with clean help text; no ValidationError traceback
**Why human:** The lazy-import guard is proven by unit tests, but running in a real shell without the installed package and without the conftest.py env setup confirms the guard holds end-to-end

### Gaps Summary

No gaps found. All eight observable truths are verified. All artifacts are substantive, wired, and data-flowing. All four requirement IDs are satisfied. The test suite is fully green (83 passed, 6 skipped integration). The CLI object is a proper `click.core.Group`.

The two items in Human Verification Required are standard live-environment checks that cannot be automated without credentials and a real network path. They do not block phase completion.

---

_Verified: 2026-04-06T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
