# Phase 6: CLI Integration - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire up Click CLI commands (`extract`, `classify`, `generate`, `run`) so users can drive the full extract -> classify -> generate pipeline from the terminal, with `--help` text, `--verbose` flag, colored output, and human-readable error messages with fix hints.

Requirements: CLI-01, CLI-02, CLI-03, CLI-04

</domain>

<decisions>
## Implementation Decisions

### Command Scope
- **D-01:** Four commands total: `extract`, `classify`, `generate` (per requirements), plus a convenience `run` command that pipelines all three in sequence.
- **D-02:** `run` command takes only `--repo` as a required flag and uses defaults for everything else. Simple one-shot for the common case.

### Flag Design
- **D-03:** `extract` exposes: `--repo` (required), `--state` (open/closed/all, default "all"), `--since` (optional ISO date), `--until` (optional ISO date). Matches CORE-02 and the extractor's existing parameters.
- **D-04:** `classify` and `generate` expose no directory flags. Cache dir and KB output dir remain config-only (via `.env` / Settings). Less flag clutter for the common case.

### Output & Feedback
- **D-05:** Silent by default — no per-item logging during normal operation. Always print a summary line at the end (e.g., "12 PRs extracted, 47 comments cached").
- **D-06:** `--verbose` / `-v` flag on all commands enables detailed per-item output during execution.
- **D-07:** Colored output using `click.style()`. Click handles terminal detection automatically (no color when piped to a file).

### Error Handling
- **D-08:** Lazy import of Settings inside each command function (not at cli.py module level). Catch `ValidationError` and print a friendly message like "Missing GITHUB_TOKEN -- set it in .env or as an environment variable".
- **D-09:** Runtime errors (bad repo name, API failures, rate limits) print the error plus a one-line fix hint. E.g., "Repository not found: owner/repo -- check the name or verify your token has access". No raw tracebacks.

### Pipeline Behavior
- **D-10:** `run` command fails fast on mid-pipeline errors. If extract succeeds but classify fails, print what succeeded and what failed, then exit non-zero. Cached data from earlier steps is preserved for re-runs.

### Claude's Discretion
- Help text detail level (flag descriptions, example usage per CLI-04)
- Whether `--verbose` wires into Python logging or controls CLI-level prints
- Click group structure (click.Group vs subcommands)
- Exact summary message format for each command

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` -- CLI-01 through CLI-04 define the CLI requirements

### Existing Code
- `src/github_pr_kb/cli.py` -- Current stub (`cli = None`). Entry point wired in pyproject.toml as `github_pr_kb.cli:cli`
- `src/github_pr_kb/extractor.py` -- `GitHubExtractor.extract(state, since, until)` returns `list[Path]`. Constructor takes `repo_name` and optional `cache_dir`
- `src/github_pr_kb/classifier.py` -- `PRClassifier.classify_all()` returns `list[Path]`, `.print_summary()` prints stats. Constructor takes `cache_dir`, `model`, `api_key`
- `src/github_pr_kb/generator.py` -- `KBGenerator.generate_all()` returns `GenerateResult(written, skipped, failed)`. Constructor takes `cache_dir`, `kb_dir`
- `src/github_pr_kb/config.py` -- `Settings` class with `github_token`, `anthropic_api_key`, `kb_output_dir`. Module-level `settings = Settings()` instantiation

### Project Configuration
- `pyproject.toml` -- `[project.scripts]` entry: `github-pr-kb = "github_pr_kb.cli:cli"`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GitHubExtractor`: Already handles rate limits, caching, dedup. CLI just instantiates and calls `.extract()`
- `PRClassifier`: Already handles content-hash dedup, API calls, `.classify_all()` + `.print_summary()`
- `KBGenerator`: Already handles manifest-based dedup, `.generate_all()` returns a structured `GenerateResult`
- `RateLimitExhaustedError`: Custom exception in extractor.py -- CLI should catch this for a friendly message

### Established Patterns
- Lazy import of `settings` inside class constructors (classifier, generator) to avoid import-time crashes in tests. CLI should follow the same pattern
- `click>=8.3.1` already in runtime dependencies
- All three modules use `logging.getLogger(__name__)` -- `--verbose` could configure log levels

### Integration Points
- `cli.py` stub with `cli = None` -- replace with actual Click group
- `pyproject.toml [project.scripts]` points to `github_pr_kb.cli:cli` -- the Click group must be named `cli`
- Each command instantiates the corresponding class and calls its entry-point method

</code_context>

<specifics>
## Specific Ideas

- User wants `run` to be a simple `--repo owner/name` one-liner for the common case
- Summary line should always print, even when not in verbose mode
- Error messages should include actionable fix hints, not just the error itself
- `run` should report what succeeded before the failure point

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 06-cli-integration*
*Context gathered: 2026-04-06*
