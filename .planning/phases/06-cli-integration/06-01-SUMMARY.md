---
phase: 06-cli-integration
plan: 01
subsystem: cli
tags: [click, cli, pydantic, pytest, CliRunner]

# Dependency graph
requires:
  - phase: 02-github-extraction-core
    provides: GitHubExtractor class with .extract() method
  - phase: 04-claude-classifier
    provides: PRClassifier class with .classify_all() method
  - phase: 05-kb-generator
    provides: KBGenerator class with .generate_all() method and GenerateResult model
provides:
  - Click CLI group named `cli` with four commands: extract, classify, generate, run
  - Full pipeline wiring from CLI flags to existing backend classes
  - TDD test suite covering all four commands (12 tests)
affects: [07-github-action, any future CLI extension]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Lazy imports inside command bodies to prevent import-time ValidationError
    - Shared _run_* helpers called by both individual commands and the run pipeline command
    - Monkey-patch print_summary=lambda: None to suppress duplicate classifier output
    - ClickException with actionable hints for all runtime errors
    - click.style(fg="green") for all success summary lines

key-files:
  created:
    - src/github_pr_kb/cli.py
    - tests/test_cli.py
  modified: []

key-decisions:
  - "Lazy imports of all backend modules inside command function bodies prevent --help from crashing when GITHUB_TOKEN is missing"
  - "Shared _run_extract/_run_classify/_run_generate helpers eliminate duplication between individual commands and run pipeline"
  - "PRClassifier.print_summary suppressed via monkey-patch (classifier.print_summary = lambda: None) before classify_all() to prevent duplicate stdout output"
  - "CliRunner() used without mix_stderr= parameter — removed in Click 8.2; stderr always separate in Click 8.3.x"
  - "test_extract_missing_token patches GitHubExtractor directly with ValidationError side_effect — settings singleton cached in sys.modules cannot be re-triggered via env= kwarg"

patterns-established:
  - "Pattern: All Click commands use _configure_logging(verbose) helper for uniform -v/--verbose wiring to Python logging"
  - "Pattern: All error paths raise click.ClickException (exit 1) or click.UsageError (exit 2), never sys.exit() directly"
  - "Pattern: run command wraps each _run_* call in try/except click.ClickException and re-raises with step name for fail-fast"

requirements-completed: [CLI-01, CLI-02, CLI-03, CLI-04]

# Metrics
duration: 5min
completed: 2026-04-06
---

# Phase 6 Plan 01: CLI Integration Summary

**Click group with extract/classify/generate/run commands wired to existing backend classes via lazy imports, green summary lines, and actionable ClickException error messages.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-06T13:01:43Z
- **Completed:** 2026-04-06T13:06:33Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Replaced `cli = None` stub with a full Click group exposing four subcommands
- 12 CliRunner tests cover help text, usage errors, happy paths, full pipeline, fail-fast, and config errors
- All commands use lazy imports — `github-pr-kb --help` works even when GITHUB_TOKEN is unset

## Task Commits

Each task was committed atomically:

1. **Task 1: Create CliRunner test suite stubs (TDD RED)** - `7e8e1bd` (test)
2. **Task 2: Implement cli.py with all four Click commands (TDD GREEN)** - `3e46d16` (feat)

**Plan metadata:** (docs commit — see final_commit below)

## Files Created/Modified

- `src/github_pr_kb/cli.py` - Full Click CLI (replace stub): group + extract, classify, generate, run commands with lazy imports, helpers, error handling
- `tests/test_cli.py` - 12 CliRunner tests for all commands and error paths

## Decisions Made

- CliRunner used without `mix_stderr=False` — that parameter was removed in Click 8.2; stderr is always separate in Click 8.3.x (Rule 3 deviation, auto-fixed)
- Suppress `PRClassifier.print_summary` via monkey-patch (`classifier.print_summary = lambda: None`) before `classify_all()` — simpler than `contextlib.redirect_stdout`
- `test_extract_missing_token` patches `GitHubExtractor` with `ValidationError` as `side_effect` rather than relying on env var replacement — settings singleton is cached at module level and cannot be re-instantiated via CliRunner's `env=` kwarg

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed unsupported `mix_stderr=False` from CliRunner constructor**
- **Found during:** Task 1 (test creation and initial collection run)
- **Issue:** Plan specified `CliRunner(mix_stderr=False)` but Click 8.2+ removed that parameter — the signature only accepts `charset`, `env`, `echo_stdin`, `catch_exceptions`
- **Fix:** Changed fixture to `CliRunner()` — stderr is automatically separated in Click 8.3.x; `result.stderr` still accessible
- **Files modified:** tests/test_cli.py
- **Verification:** Test collection succeeds; all 12 tests pass in GREEN phase
- **Committed in:** `7e8e1bd` (part of Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking issue)
**Impact on plan:** Necessary fix for Click 8.3.x compatibility. No scope creep.

## Issues Encountered

None beyond the `mix_stderr` removal documented as deviation above.

## Known Stubs

None. All commands are fully wired to their backend classes.

## Next Phase Readiness

- CLI is fully functional — `github-pr-kb extract --repo owner/name`, `classify`, `generate`, `run` all work end-to-end
- Entry point `github-pr-kb = "github_pr_kb.cli:cli"` in pyproject.toml is now live
- Ready for Phase 07: GitHub Action for automated extraction

---
*Phase: 06-cli-integration*
*Completed: 2026-04-06*
