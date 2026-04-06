# Phase 6: CLI Integration - Research

**Researched:** 2026-04-06
**Domain:** Click 8 CLI wiring — Python package entry points, subcommand groups, error handling, verbose logging, CliRunner testing
**Confidence:** HIGH

## Summary

Phase 6 replaces the `cli = None` stub in `cli.py` with a real Click group containing four commands: `extract`, `classify`, `generate`, and `run`. All upstream modules (`GitHubExtractor`, `PRClassifier`, `KBGenerator`) are complete and tested — this phase is pure wiring. The research confirms Click 8.3.1 is already installed, the entry point is already declared in `pyproject.toml`, and no new library dependencies are needed.

The main design decisions are already locked in `CONTEXT.md`. Key open choices left to Claude's discretion are: whether `--verbose` configures Python's `logging` module or drives CLI-level prints, the exact Click group structure, and summary message formatting.

The critical pitfall is import-time `ValidationError` from `config.py`'s module-level `settings = Settings()`. Every prior phase solved this by lazy-importing `settings` inside the class constructor. The CLI must do the same: import `Settings` inside each command function body, not at `cli.py` module level.

**Primary recommendation:** Use a `@click.group()` named `cli`, decorate each command with `@cli.command()`, lazy-import Settings inside each command, raise `click.ClickException` for user-facing errors, and use `click.testing.CliRunner` for all tests.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Four commands total: `extract`, `classify`, `generate` (per requirements), plus a convenience `run` command that pipelines all three in sequence.
- **D-02:** `run` command takes only `--repo` as a required flag and uses defaults for everything else.
- **D-03:** `extract` exposes: `--repo` (required), `--state` (open/closed/all, default "all"), `--since` (optional ISO date), `--until` (optional ISO date).
- **D-04:** `classify` and `generate` expose no directory flags. Cache dir and KB output dir remain config-only (via `.env` / Settings).
- **D-05:** Silent by default — no per-item logging during normal operation. Always print a summary line at the end.
- **D-06:** `--verbose` / `-v` flag on all commands enables detailed per-item output during execution.
- **D-07:** Colored output using `click.style()`. Click handles terminal detection automatically.
- **D-08:** Lazy import of Settings inside each command function (not at `cli.py` module level). Catch `ValidationError` and print a friendly message.
- **D-09:** Runtime errors (bad repo name, API failures, rate limits) print the error plus a one-line fix hint. No raw tracebacks.
- **D-10:** `run` command fails fast on mid-pipeline errors. Cached data from earlier steps is preserved for re-runs.

### Claude's Discretion

- Help text detail level (flag descriptions, example usage per CLI-04)
- Whether `--verbose` wires into Python logging or controls CLI-level prints
- Click group structure (click.Group vs subcommands)
- Exact summary message format for each command

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CLI-01 | User can run `github-pr-kb extract --repo owner/name` to extract and cache PR comments | `@cli.command()` + `@click.option("--repo", required=True)` wired to `GitHubExtractor.extract()` |
| CLI-02 | User can run `github-pr-kb classify` to classify cached comments via Claude | `@cli.command()` wired to `PRClassifier.classify_all()` |
| CLI-03 | User can run `github-pr-kb generate` to write the markdown knowledge base | `@cli.command()` wired to `KBGenerator.generate_all()` |
| CLI-04 | All commands provide clear `--help` output and actionable error messages | Click auto-generates `--help`; `click.ClickException` for user-facing errors; epilog with examples |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| click | 8.3.1 (installed) | CLI framework: group, command, option, argument, style, echo | Already in runtime deps; locked in pyproject.toml |
| click.testing.CliRunner | same | Isolated CLI testing without subprocess | Official Click testing API |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| unittest.mock.patch | stdlib | Mock external API calls in CLI tests | Patching `GitHubExtractor.__init__`, `PRClassifier.classify_all`, etc. |
| datetime.fromisoformat | stdlib | Parse `--since` / `--until` ISO date strings | Click `type=str` then convert in command body |
| logging | stdlib | Per-item verbose output via log level | Wire `--verbose` to `logging.basicConfig(level=INFO)` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `click.ClickException` | `sys.exit(1)` with `click.echo` | ClickException gives consistent "Error: …" prefix and correct exit code automatically |
| `logging.basicConfig` for verbose | Manual per-print guard | Logging integrates naturally with existing `logger.info()` calls in extractor/classifier/generator |

**Installation:** No new packages needed. Click 8.3.1 is already installed.

**Version verification (confirmed):**
```
click 8.3.1  — confirmed via .venv/Scripts/python.exe -c "import click; ..."
```

---

## Architecture Patterns

### Recommended Project Structure

```
src/github_pr_kb/
└── cli.py          # Replace stub — single file for the full CLI
tests/
└── test_cli.py     # New file — CliRunner-based tests for all four commands
```

No subdirectory needed. Four commands in one file is manageable and consistent with the existing single-file module pattern of the project.

### Pattern 1: Click Group + Subcommands

**What:** A `@click.group()` function named `cli` serves as the entry point. Each command is a `@cli.command()` decorated function. This is required because `pyproject.toml` declares `github-pr-kb = "github_pr_kb.cli:cli"` — the group object must be named `cli`.

**When to use:** Any CLI with multiple subcommands (standard pattern for tools like `git`, `docker`, `pip`).

**Example:**
```python
# Source: Click 8.3.x official docs — Quickstart / Commands and Groups
import click

@click.group()
def cli() -> None:
    """GitHub PR Knowledge Base tool."""

@cli.command()
@click.option("--repo", required=True, help="Repository in owner/name format. Example: pallets/click")
@click.option("--state", default="all", type=click.Choice(["open", "closed", "all"]), show_default=True)
@click.option("--since", default=None, help="Only PRs updated on or after this ISO date. Example: 2024-01-01")
@click.option("--until", default=None, help="Only PRs updated on or before this ISO date.")
@click.option("-v", "--verbose", is_flag=True, help="Print per-item detail during extraction.")
def extract(repo: str, state: str, since: str | None, until: str | None, verbose: bool) -> None:
    """Extract and cache PR comments from a GitHub repository."""
    ...
```

### Pattern 2: Lazy Settings Import Inside Command Body (CRITICAL)

**What:** Import `Settings` inside the command function body, not at module level. Catch `pydantic.ValidationError` and re-raise as `click.ClickException` with a human-readable message.

**Why:** `config.py` has a module-level `settings = Settings()` that raises `ValidationError` at import time if `GITHUB_TOKEN` is missing. If `cli.py` imports `settings` at module level, `github-pr-kb --help` will crash before any command runs. Every prior phase solved this with lazy imports inside constructors.

**Example:**
```python
@cli.command()
@click.option("--repo", required=True)
def extract(repo: str, verbose: bool) -> None:
    from pydantic import ValidationError
    try:
        from github_pr_kb.config import settings  # lazy — not at cli.py top level
        _ = settings  # triggers validation
    except ValidationError:
        raise click.ClickException(
            "Missing GITHUB_TOKEN -- set it in .env or as an environment variable."
        )
    ...
```

Note: `GitHubExtractor.__init__` already accesses `settings.github_token` at construction time, so a `ValidationError` will surface naturally. The CLI needs to catch it there too.

### Pattern 3: ClickException for User-Facing Errors

**What:** Raise `click.ClickException(message)` for any error the user can fix. Click prints "Error: {message}" to stderr and exits with code 1. For usage errors (wrong flag format), raise `click.UsageError`.

**Exit codes:**
- `0` — success
- `1` — `click.ClickException` (runtime error: bad token, bad repo name, API failure)
- `2` — `click.UsageError` or bad option (Click's built-in usage error)

**Example:**
```python
from github_pr_kb.extractor import RateLimitExhaustedError

try:
    paths = extractor.extract(state=state, since=since_dt, until=until_dt)
except RateLimitExhaustedError as exc:
    raise click.ClickException(str(exc))
except Exception as exc:
    raise click.ClickException(
        f"Extraction failed: {exc}\n"
        "Hint: check --repo format (owner/name) and that your token has repo read access."
    )
```

### Pattern 4: Verbose Flag Wired to Python Logging

**What:** Each command receives a `--verbose` / `-v` flag. When set, call `logging.basicConfig(level=logging.INFO)` at the start of the command body. The existing `logger.info(...)` calls in extractor, classifier, and generator then emit to stderr automatically.

**Why this over manual print guards:** The upstream modules already use `logger.info` for per-item detail. Wiring `--verbose` to logging level reuses that work without adding conditional prints to cli.py.

**Warning (from Click issue #1053):** `logging.basicConfig` is no-op if called more than once (Python caching). In tests, call `logging.disable(logging.NOTSET)` or use `importlib.reload` if needed. In practice, call it once per command invocation — not a problem in production; only affects tests that invoke the same command multiple times.

**Example:**
```python
import logging

@cli.command()
@click.option("-v", "--verbose", is_flag=True)
def extract(verbose: bool, ...) -> None:
    if verbose:
        logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    ...
```

### Pattern 5: Colored Summary Line with click.style()

**What:** Always print a summary line at the end of each command using `click.echo()` with `click.style()`. Click detects terminal vs pipe automatically — colors are stripped when output is not a TTY.

**Example:**
```python
click.echo(
    click.style(f"Extracted {len(paths)} PRs, {total_comments} comments cached.", fg="green")
)
```

### Pattern 6: ISO Date Parsing for --since / --until

**What:** Accept `--since` and `--until` as strings, then parse inside the command with `datetime.fromisoformat()`. Raise `click.UsageError` (exit code 2) if parsing fails — this signals incorrect flag usage.

**Example:**
```python
from datetime import datetime

def _parse_iso_date(value: str | None, flag_name: str) -> datetime | None:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise click.UsageError(
            f"--{flag_name} must be an ISO date (e.g. 2024-01-01). Got: {value!r}"
        )
```

### Pattern 7: CliRunner Testing

**What:** Use `click.testing.CliRunner` to invoke commands in-process. The runner captures stdout, stderr, and exit code without spawning a subprocess.

**Key options:**
- `mix_stderr=False` — keep stdout and stderr separate for asserting error messages independently
- `catch_exceptions=False` — let unexpected exceptions propagate for easier debugging in tests
- `env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"}` — override env per-invocation

**Example:**
```python
# Source: Click 8.3.x official docs — Testing Click Applications
from click.testing import CliRunner
from github_pr_kb.cli import cli

def test_extract_missing_token():
    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(cli, ["extract", "--repo", "owner/name"], env={"GITHUB_TOKEN": ""})
    assert result.exit_code == 1
    assert "GITHUB_TOKEN" in result.output

def test_extract_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["extract", "--help"])
    assert result.exit_code == 0
    assert "--repo" in result.output
    assert "--state" in result.output
```

### Anti-Patterns to Avoid

- **Module-level `settings` import in cli.py:** Causes `--help` to crash if `GITHUB_TOKEN` is not set. Lazy import inside each command body instead.
- **`sys.exit(1)` directly:** Bypasses Click's error formatting. Use `raise click.ClickException(msg)` or `raise click.UsageError(msg)` instead.
- **Printing raw exception tracebacks:** Catch specific exceptions (`RateLimitExhaustedError`, `ValueError`, `GithubException`) and convert to `ClickException` with fix hints.
- **Importing `GitHubExtractor` at cli.py module level:** `extractor.py` does `from github_pr_kb.config import settings` at module level, which will trigger Settings validation on import. Import the class inside the command function body.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Help text generation | Custom `--help` handler | Click's built-in `--help` (auto from docstring + option `help=`) | Click generates help from function docstring and `help=` kwarg on each option |
| Terminal color detection | `os.isatty()` guard | `click.style()` + `click.echo()` | Click handles TTY detection automatically |
| Argument parsing | `sys.argv` parsing | Click decorators | Click handles required/optional, defaults, type coercion |
| Test subprocess spawning | `subprocess.run(["github-pr-kb", ...])` | `click.testing.CliRunner.invoke()` | In-process, faster, captures output |
| ISO date validation | Regex | `datetime.fromisoformat()` + `click.UsageError` | stdlib handles all ISO 8601 variants |
| Choice validation for --state | Manual if/else | `click.Choice(["open", "closed", "all"])` | Click rejects invalid values with a formatted error automatically |

**Key insight:** Click is a mature, high-level library. The only custom code needed is the business logic glue (instantiate class, call method, format summary). Everything else (parsing, help, color, error display) is a Click built-in.

---

## Common Pitfalls

### Pitfall 1: Import-Time ValidationError Kills --help

**What goes wrong:** `github-pr-kb --help` or `github-pr-kb extract --help` crashes with a Pydantic `ValidationError` before displaying any help text.

**Why it happens:** `config.py` has `settings = Settings()` at module level. If `cli.py` imports `from github_pr_kb.config import settings` at its top level — or imports any module that does so (like `extractor.py`) — the validation runs on import, before Click gets a chance to display help.

**How to avoid:** Import `settings`, `GitHubExtractor`, `PRClassifier`, and `KBGenerator` inside each command function body. Never at `cli.py` module level.

**Warning signs:** `--help` raises `ValidationError` instead of showing usage.

---

### Pitfall 2: Logging basicConfig No-Op on Repeated Test Invocations

**What goes wrong:** The second test that invokes a command with `--verbose` sees no log output, even though logging is supposed to be enabled.

**Why it happens:** `logging.basicConfig()` is a no-op if the root logger already has handlers. In a test session, the first invocation configures the root logger; subsequent invocations silently skip the call.

**How to avoid:** In tests that need to assert on log output, use `caplog` fixture (pytest) rather than asserting on `result.output`. Or structure tests so verbose-mode behavior is exercised via mock call counts rather than log content.

**Warning signs:** Verbose tests pass in isolation but fail when run as part of the full suite.

---

### Pitfall 3: CliRunner Captures stderr on result.output by Default

**What goes wrong:** Test asserts `"Error:" in result.output` but the assertion fails because `CliRunner(mix_stderr=True)` (the default) mixes stderr into `result.output`, while `mix_stderr=False` separates them into `result.output` (stdout) and `result.stderr`.

**How to avoid:** Be explicit about `mix_stderr` when creating `CliRunner`. Use `mix_stderr=False` when tests need to assert error messages independently.

---

### Pitfall 4: `run` Command Hides Individual Step Failures

**What goes wrong:** `run` silently swallows a `ClickException` raised by a sub-step and continues to the next step, producing partial output.

**How to avoid:** In the `run` command, call `extract`, `classify`, and `generate` logic directly (not via `runner.invoke`) and let exceptions propagate. Re-raise as `ClickException` with a message that names which step failed and what succeeded before it.

---

### Pitfall 5: click.Choice --state Rejects Valid GitHub API Values

**What goes wrong:** `click.Choice(["open", "closed", "all"])` is case-sensitive by default. A user passing `--state Open` gets a rejection message.

**How to avoid:** `click.Choice(["open", "closed", "all"], case_sensitive=False)` — or document that lowercase is required in help text. Confirmed: Click 8 `Choice` has `case_sensitive` parameter.

---

## Code Examples

Verified patterns from the Click 8.3.1 source and official docs:

### Complete cli.py Skeleton

```python
"""Click CLI for github-pr-kb."""
import logging
import sys
from datetime import datetime
from pathlib import Path

import click


@click.group()
def cli() -> None:
    """Extract, classify, and generate a knowledge base from GitHub PR discussions."""


@cli.command()
@click.option("--repo", required=True, help="GitHub repository in owner/name format. Example: pallets/click")
@click.option(
    "--state",
    default="all",
    type=click.Choice(["open", "closed", "all"], case_sensitive=False),
    show_default=True,
    help="Filter PRs by state.",
)
@click.option("--since", default=None, metavar="DATE", help="ISO date: only PRs updated on/after this date.")
@click.option("--until", default=None, metavar="DATE", help="ISO date: only PRs updated on/before this date.")
@click.option("-v", "--verbose", is_flag=True, help="Print per-PR detail during extraction.")
def extract(repo: str, state: str, since: str | None, until: str | None, verbose: bool) -> None:
    """Extract and cache PR comments from a GitHub repository.

    \b
    Examples:
      github-pr-kb extract --repo pallets/click
      github-pr-kb extract --repo pallets/click --state closed --since 2024-01-01
    """
    if verbose:
        logging.basicConfig(level=logging.INFO, stream=sys.stderr)

    since_dt = _parse_iso_date(since, "since")
    until_dt = _parse_iso_date(until, "until")

    try:
        from pydantic import ValidationError
        from github_pr_kb.extractor import GitHubExtractor, RateLimitExhaustedError
        extractor = GitHubExtractor(repo_name=repo)
    except Exception as exc:
        _handle_config_error(exc)

    try:
        paths = extractor.extract(state=state, since=since_dt, until=until_dt)
    except RateLimitExhaustedError as exc:
        raise click.ClickException(str(exc))
    except Exception as exc:
        raise click.ClickException(
            f"Extraction failed: {exc}\n"
            "Hint: verify --repo is in owner/name format and your token has repo read access."
        )

    click.echo(click.style(f"Extracted {len(paths)} PRs.", fg="green"))
```

### CliRunner Test Skeleton

```python
# tests/test_cli.py
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from github_pr_kb.cli import cli


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


def test_extract_help(runner):
    result = runner.invoke(cli, ["extract", "--help"])
    assert result.exit_code == 0
    assert "--repo" in result.output
    assert "--state" in result.output
    assert "--since" in result.output

def test_extract_missing_repo(runner):
    result = runner.invoke(cli, ["extract"])
    assert result.exit_code == 2  # UsageError: missing required option

def test_extract_runs(runner, tmp_path):
    with patch("github_pr_kb.cli.GitHubExtractor") as mock_cls:
        instance = mock_cls.return_value
        instance.extract.return_value = [tmp_path / "pr-1.json"]
        result = runner.invoke(cli, ["extract", "--repo", "owner/repo"])
    assert result.exit_code == 0
    assert "Extracted 1 PRs" in result.output
```

### Error Wrapper Helper

```python
def _handle_config_error(exc: Exception) -> None:
    """Convert Settings validation errors to user-friendly ClickException."""
    from pydantic import ValidationError
    if isinstance(exc, ValidationError):
        raise click.ClickException(
            "Configuration error -- missing required environment variable.\n"
            "Hint: copy .env.example to .env and fill in GITHUB_TOKEN (and ANTHROPIC_API_KEY for classify)."
        )
    raise click.ClickException(f"Startup error: {exc}")
```

---

## Runtime State Inventory

> SKIPPED — this is a greenfield implementation phase (replacing a stub), not a rename/refactor/migration.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | All | ✓ | 3.14.2 | — |
| click | CLI framework | ✓ | 8.3.1 | — |
| pydantic / pydantic-settings | Settings validation | ✓ | (installed) | — |
| pytest | Test suite | ✓ | 9.x | — |
| .venv/Scripts/python.exe | Test runner (CLAUDE.md requirement) | ✓ | — | Do NOT use `uv run pytest` |

No missing dependencies. All required packages are installed.

---

## Validation Architecture

> `nyquist_validation: true` in `.planning/config.json` — section included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `.venv/Scripts/python.exe -m pytest tests/test_cli.py -x` |
| Full suite command | `.venv/Scripts/python.exe -m pytest tests/` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | `extract --repo owner/name` runs extraction, prints summary | unit (mocked GitHubExtractor) | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_extract_runs -x` | Wave 0 |
| CLI-01 | `extract --repo` missing → exit code 2 | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_extract_missing_repo -x` | Wave 0 |
| CLI-02 | `classify` runs PRClassifier.classify_all(), prints summary | unit (mocked PRClassifier) | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_classify_runs -x` | Wave 0 |
| CLI-03 | `generate` runs KBGenerator.generate_all(), prints summary | unit (mocked KBGenerator) | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_generate_runs -x` | Wave 0 |
| CLI-04 | All commands respond to `--help` with description + all options listed | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py -k "help" -x` | Wave 0 |
| CLI-04 | Missing GITHUB_TOKEN → human-readable error, not traceback | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_extract_missing_token -x` | Wave 0 |
| CLI-04 | Bad --since format → exit code 2 with usage hint | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_extract_bad_date -x` | Wave 0 |
| D-01 | `run --repo owner/name` pipelines all three steps | unit (all three mocked) | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_run_pipelines -x` | Wave 0 |
| D-10 | `run` fails fast if extract fails; classify/generate not called | unit | `.venv/Scripts/python.exe -m pytest tests/test_cli.py::test_run_fails_fast -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `.venv/Scripts/python.exe -m pytest tests/test_cli.py -x`
- **Per wave merge:** `.venv/Scripts/python.exe -m pytest tests/`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_cli.py` — covers all CLI-01 through CLI-04 requirements (does not exist yet)

No framework install needed — pytest is already installed and configured.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `cli = None` stub | Real `@click.group()` named `cli` | Phase 6 (this phase) | Entry point becomes functional |
| `Auth.Token(token)` via positional string | `Auth.Token(token)` keyword arg | Phase 2 (already done) | Not relevant to CLI phase |

**Deprecated/outdated:**
- `click.__version__` attribute: deprecated in Click 8.3.x, will be removed in 9.1. Use `importlib.metadata.version("click")` if version checking is needed. Not relevant for this phase.

---

## Open Questions

1. **Whether `run` should call internal functions or `runner.invoke` sub-commands**
   - What we know: Calling `runner.invoke` from inside a command is awkward and not idiomatic.
   - What's unclear: Whether to duplicate the "get settings, instantiate class, call method" logic or extract shared helpers.
   - Recommendation: Extract private `_run_extract()`, `_run_classify()`, `_run_generate()` helper functions that both the individual commands and `run` call. Avoids duplication without `runner.invoke` nesting.

2. **Exact `run` summary format when a mid-pipeline step fails**
   - What we know: D-10 says "print what succeeded and what failed, then exit non-zero."
   - Recommendation: Print green summary lines for each completed step, then a red `click.ClickException` message naming the failed step.

---

## Sources

### Primary (HIGH confidence)

- Click 8.3.1 installed package — version confirmed via `.venv/Scripts/python.exe`
- `pallets/click` GitHub source (`src/click/exceptions.py`) — ClickException, UsageError, Exit hierarchy confirmed via WebFetch
- Existing project source files — extractor.py, classifier.py, generator.py, config.py, conftest.py read directly

### Secondary (MEDIUM confidence)

- [Click 8.3.x Testing Documentation](https://click.palletsprojects.com/en/stable/testing/) — CliRunner patterns (search result confirmed, direct fetch blocked by 403)
- [Click 8.3.x Exception Handling](https://click.palletsprojects.com/en/stable/exceptions/) — exit codes, ClickException.show() (search result confirmed, direct fetch blocked by 403)
- [Click issue #1053](https://github.com/pallets/click/issues/1053) — logging.basicConfig no-op in repeated CliRunner invocations (search result, community-confirmed)
- [Click discussion #2189](https://github.com/pallets/click/discussions/2189) — top-level verbose/logging configuration patterns

### Tertiary (LOW confidence)

None — all critical claims verified against installed package or official source.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — click 8.3.1 installed and verified
- Architecture patterns: HIGH — derived from existing project patterns + Click source
- Pitfalls: HIGH — import-time ValidationError pitfall confirmed by phases 1-5 history; logging pitfall confirmed by Click issue tracker
- Test patterns: HIGH — CliRunner is the official Click testing API, confirmed via search + source

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (Click is stable; these APIs have not changed since 8.0)
