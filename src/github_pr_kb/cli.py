"""Click CLI for github-pr-kb.

Entry point: github-pr-kb = "github_pr_kb.cli:cli"

All imports of settings, GitHubExtractor, PRClassifier, and KBGenerator
are lazy (inside function bodies) to prevent import-time ValidationError
when GITHUB_TOKEN is missing — critical for --help to work without env vars.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import click

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_iso_date(value: str | None, flag_name: str) -> datetime | None:
    """Parse an ISO date string, raising UsageError on bad format."""
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise click.UsageError(
            f"--{flag_name} must be an ISO date (e.g. 2024-01-01). Got: {value!r}"
        ) from exc


def _configure_logging(verbose: bool) -> None:
    """Enable INFO-level logging to stderr when verbose flag is set."""
    if verbose:
        logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")


class ConfigurationError(click.ClickException):
    """Raised when a required environment variable or config value is missing."""

    def __init__(self, detail: str = "") -> None:
        hint = (
            "Configuration error -- missing required environment variable.\n"
            "Hint: copy .env.example to .env and fill in GITHUB_TOKEN"
            " (and ANTHROPIC_API_KEY for classify/generate)."
        )
        message = f"{hint}\nDetail: {detail}" if detail else hint
        super().__init__(message)


# ---------------------------------------------------------------------------
# Private pipeline helpers — shared by individual commands and run
# ---------------------------------------------------------------------------


def _run_extract(
    repo: str,
    state: str,
    since_dt: datetime | None,
    until_dt: datetime | None,
) -> str:
    """Instantiate GitHubExtractor, run extract, return green summary string."""
    try:
        from github_pr_kb.extractor import GitHubExtractor, RateLimitExhaustedError

        extractor = GitHubExtractor(repo_name=repo)
    except Exception as exc:
        raise ConfigurationError(str(exc)) from exc

    try:
        paths: list[Path] = extractor.extract(state=state, since=since_dt, until=until_dt)
    except RateLimitExhaustedError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:
        raise click.ClickException(
            f"Extraction failed: {exc}\n"
            "Hint: verify --repo is in owner/name format and your token has"
            " repo read access."
        ) from exc

    total_comments = 0
    for p in paths:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            total_comments += len(data.get("comments", []))
        except Exception:
            logging.debug("Skipping unreadable cache file: %s", p)

    return f"Extracted {len(paths)} PRs, {total_comments} comments cached."


def _run_classify() -> str:
    """Instantiate PRClassifier, run classify_all (suppressing its own summary), return summary string."""
    try:
        from github_pr_kb.classifier import PRClassifier

        classifier = PRClassifier()
    except ValueError as exc:
        raise click.ClickException(
            "Configuration error -- missing required environment variable.\n"
            "Hint: copy .env.example to .env and fill in ANTHROPIC_API_KEY."
        ) from exc
    except Exception as exc:
        raise ConfigurationError(str(exc)) from exc

    # Suppress classifier's built-in print_summary() — it uses bare print()
    # and would duplicate/pollute the CLI's own green summary line.
    classifier.print_summary = lambda: None  # type: ignore[method-assign]

    classifier.classify_all()
    counts = classifier.get_summary_counts()
    return (
        f"Classified {counts['new']} new, {counts['cached']} cached, "
        f"{counts['need_review']} need review, {counts['failed']} failed."
    )


def _run_generate(regenerate: bool = False) -> str:
    """Instantiate KBGenerator, run generate_all, return summary string."""
    from github_pr_kb.generator import DEFAULT_CACHE_DIR, KBGenerator

    if not list(DEFAULT_CACHE_DIR.glob("classified-pr-*.json")):
        raise click.ClickException(
            "Generation failed: no classified PR cache found.\n"
            "Hint: run `github-pr-kb classify` before `github-pr-kb generate`."
        )

    try:
        generator = KBGenerator()
    except ValueError as exc:
        detail = str(exc)
        if "ANTHROPIC_API_KEY" in detail and "required" in detail:
            raise click.ClickException(
                "Configuration error -- missing required environment variable.\n"
                "Hint: copy .env.example to .env and fill in ANTHROPIC_API_KEY for article generation."
            ) from exc
        raise ConfigurationError(detail) from exc
    except Exception as exc:
        raise ConfigurationError(str(exc)) from exc

    try:
        result = generator.generate_all(regenerate=regenerate)
    except Exception as exc:
        raise click.ClickException(f"Generation failed: {exc}") from exc

    successful_outcomes = result.written + result.skipped + result.filtered
    if result.failed and successful_outcomes == 0:
        raise click.ClickException(
            f"Generation failed: {len(result.failed)} article(s) failed and no output was produced."
        )
    if result.failed:
        click.echo(
            click.style(
                f"Warning: {len(result.failed)} article(s) failed synthesis.",
                fg="yellow",
            ),
            err=True,
        )
    return (
        f"Generated {result.written} new, {result.skipped} skipped, "
        f"{result.filtered} filtered, {len(result.failed)} failed."
    )


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """Extract, classify, and generate a knowledge base from GitHub PR discussions."""


# ---------------------------------------------------------------------------
# extract command
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--repo",
    required=True,
    help="GitHub repository in owner/name format. Example: pallets/click",
)
@click.option(
    "--state",
    default="all",
    type=click.Choice(["open", "closed", "all"], case_sensitive=False),
    show_default=True,
    help="Filter PRs by state.",
)
@click.option(
    "--since",
    default=None,
    metavar="DATE",
    help="Only PRs updated on or after this ISO date. Example: 2024-01-01",
)
@click.option(
    "--until",
    default=None,
    metavar="DATE",
    help="Only PRs updated on or before this ISO date. Example: 2024-12-31",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Print per-PR detail during extraction.",
)
def extract(
    repo: str,
    state: str,
    since: str | None,
    until: str | None,
    verbose: bool,
) -> None:
    """Extract and cache PR comments from a GitHub repository.

    \b
    Examples:
      github-pr-kb extract --repo pallets/click
      github-pr-kb extract --repo pallets/click --state closed --since 2024-01-01
    """
    _configure_logging(verbose)
    since_dt = _parse_iso_date(since, "since")
    until_dt = _parse_iso_date(until, "until")
    summary = _run_extract(repo, state, since_dt, until_dt)
    click.echo(click.style(summary, fg="green"))


# ---------------------------------------------------------------------------
# classify command
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Print per-comment detail during classification.",
)
def classify(verbose: bool) -> None:
    """Classify cached PR comments into knowledge categories using Claude.

    \b
    Examples:
      github-pr-kb classify
      github-pr-kb classify --verbose
    """
    _configure_logging(verbose)
    summary = _run_classify()
    click.echo(click.style(summary, fg="green"))


# ---------------------------------------------------------------------------
# generate command
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--regenerate",
    is_flag=True,
    help="Re-synthesize all articles from scratch after prompt/model/threshold changes.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Print per-article detail during generation.",
)
def generate(regenerate: bool, verbose: bool) -> None:
    """Generate markdown knowledge base articles from classified comments.

    \b
    Examples:
      github-pr-kb generate
      github-pr-kb generate --verbose
    """
    _configure_logging(verbose)
    summary = _run_generate(regenerate=regenerate)
    click.echo(click.style(summary, fg="green"))


# ---------------------------------------------------------------------------
# run command (full pipeline)
# ---------------------------------------------------------------------------


@cli.command()
@click.option(
    "--repo",
    required=True,
    help="GitHub repository in owner/name format. Example: pallets/click",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Print per-item detail for each pipeline step.",
)
def run(repo: str, verbose: bool) -> None:
    """Run the full extract -> classify -> generate pipeline in one command.

    \b
    Examples:
      github-pr-kb run --repo pallets/click
    """
    _configure_logging(verbose)

    # Extract
    try:
        extract_summary = _run_extract(repo, state="all", since_dt=None, until_dt=None)
    except click.ClickException as exc:
        raise click.ClickException(f"Pipeline failed at extract step: {exc.format_message()}")
    click.echo(click.style(extract_summary, fg="green"))

    # Classify
    try:
        classify_summary = _run_classify()
    except click.ClickException as exc:
        raise click.ClickException(f"Pipeline failed at classify step: {exc.format_message()}")
    click.echo(click.style(classify_summary, fg="green"))

    # Generate
    try:
        generate_summary = _run_generate(regenerate=False)
    except click.ClickException as exc:
        raise click.ClickException(f"Pipeline failed at generate step: {exc.format_message()}")
    click.echo(click.style(generate_summary, fg="green"))
