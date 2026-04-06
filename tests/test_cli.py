"""CliRunner-based tests for the github-pr-kb CLI.

All tests use click.testing.CliRunner with mix_stderr=False to keep
stdout and stderr separate for independent assertion.
"""
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from github_pr_kb.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    # mix_stderr was removed in Click 8.2 — stderr is always separate now.
    return CliRunner()


# ---------------------------------------------------------------------------
# Help text tests (CLI-04)
# ---------------------------------------------------------------------------


def test_extract_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["extract", "--help"])
    assert result.exit_code == 0
    assert "--repo" in result.output
    assert "--state" in result.output
    assert "--since" in result.output
    assert "--until" in result.output
    assert "--verbose" in result.output
    assert "Extract and cache PR comments" in result.output


def test_classify_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["classify", "--help"])
    assert result.exit_code == 0
    assert "--verbose" in result.output
    assert "Classify cached PR comments" in result.output


def test_generate_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["generate", "--help"])
    assert result.exit_code == 0
    assert "--verbose" in result.output
    assert "Generate markdown" in result.output


def test_run_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    assert "--repo" in result.output
    assert "--verbose" in result.output
    assert "pipeline" in result.output.lower()


# ---------------------------------------------------------------------------
# Usage error tests (CLI-04)
# ---------------------------------------------------------------------------


def test_extract_missing_repo(runner: CliRunner) -> None:
    """Missing required --repo option should exit 2."""
    result = runner.invoke(cli, ["extract"])
    assert result.exit_code == 2


def test_extract_bad_date(runner: CliRunner) -> None:
    """Bad ISO date for --since should exit 2 with a hint about ISO date."""
    result = runner.invoke(
        cli,
        ["extract", "--repo", "owner/repo", "--since", "not-a-date"],
        env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
    )
    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "ISO date" in combined


# ---------------------------------------------------------------------------
# Happy path tests (CLI-01, CLI-02, CLI-03)
# ---------------------------------------------------------------------------


def test_extract_runs(runner: CliRunner) -> None:
    """extract command mocked: should exit 0 and print 'Extracted'."""
    with patch("github_pr_kb.extractor.GitHubExtractor") as mock_cls:
        instance = mock_cls.return_value
        instance.extract.return_value = []
        result = runner.invoke(
            cli,
            ["extract", "--repo", "owner/repo"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )
    assert result.exit_code == 0, result.output
    assert "Extracted" in result.output


def test_classify_runs(runner: CliRunner) -> None:
    """classify command mocked: should exit 0, print 'Classified', not duplicate print_summary output."""
    with patch("github_pr_kb.classifier.PRClassifier") as mock_cls:
        instance = mock_cls.return_value
        instance.classify_all.return_value = []
        instance._classified_count = 3
        instance._cache_hit_count = 2
        result = runner.invoke(
            cli,
            ["classify"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )
    assert result.exit_code == 0, result.output
    assert "Classified" in result.output
    # Verify classifier's own print_summary is suppressed — no "Classification complete:" in output
    assert "Classification complete:" not in result.output


def test_generate_runs(runner: CliRunner) -> None:
    """generate command mocked: should exit 0 and print 'Generated'."""
    from github_pr_kb.generator import GenerateResult

    with patch("github_pr_kb.generator.KBGenerator") as mock_cls:
        instance = mock_cls.return_value
        instance.generate_all.return_value = GenerateResult(written=5, skipped=2, failed=[])
        result = runner.invoke(
            cli,
            ["generate"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )
    assert result.exit_code == 0, result.output
    assert "Generated" in result.output


# ---------------------------------------------------------------------------
# Run pipeline test (D-01)
# ---------------------------------------------------------------------------


def test_run_pipelines(runner: CliRunner) -> None:
    """run command should pipeline all three steps and print all three summaries."""
    from github_pr_kb.generator import GenerateResult

    with (
        patch("github_pr_kb.extractor.GitHubExtractor") as mock_extract_cls,
        patch("github_pr_kb.classifier.PRClassifier") as mock_classify_cls,
        patch("github_pr_kb.generator.KBGenerator") as mock_generate_cls,
    ):
        ext_inst = mock_extract_cls.return_value
        ext_inst.extract.return_value = []

        cls_inst = mock_classify_cls.return_value
        cls_inst.classify_all.return_value = []
        cls_inst._classified_count = 2
        cls_inst._cache_hit_count = 1

        gen_inst = mock_generate_cls.return_value
        gen_inst.generate_all.return_value = GenerateResult(written=3, skipped=0, failed=[])

        result = runner.invoke(
            cli,
            ["run", "--repo", "owner/repo"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 0, result.output
    assert "Extracted" in result.output
    assert "Classified" in result.output
    assert "Generated" in result.output


# ---------------------------------------------------------------------------
# Run fail-fast test (D-10)
# ---------------------------------------------------------------------------


def test_run_fails_fast(runner: CliRunner) -> None:
    """run command should fail fast if extract raises — classify and generate must not be called."""
    with (
        patch("github_pr_kb.extractor.GitHubExtractor") as mock_extract_cls,
        patch("github_pr_kb.classifier.PRClassifier") as mock_classify_cls,
        patch("github_pr_kb.generator.KBGenerator") as mock_generate_cls,
    ):
        ext_inst = mock_extract_cls.return_value
        ext_inst.extract.side_effect = Exception("boom")

        result = runner.invoke(
            cli,
            ["run", "--repo", "owner/repo"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 1
    combined = result.output.lower() + (result.stderr or "").lower()
    assert "pipeline" in combined or "failed" in combined

    # classify and generate must not have been instantiated
    mock_classify_cls.assert_not_called()
    mock_generate_cls.assert_not_called()


# ---------------------------------------------------------------------------
# Config error test (CLI-04)
# ---------------------------------------------------------------------------


def test_extract_missing_token(runner: CliRunner) -> None:
    """Missing GITHUB_TOKEN should exit 1 with a config error message.

    Uses mock to simulate ValidationError at GitHubExtractor construction time,
    because the settings singleton is cached at module level and CliRunner's
    env= kwarg cannot trigger a fresh Settings() construction.
    """
    from pydantic import ValidationError as PydanticValidationError

    # Build a minimal ValidationError to use as a side_effect.
    # Simulate missing GITHUB_TOKEN by patching GitHubExtractor to raise it.
    with patch("github_pr_kb.extractor.GitHubExtractor") as mock_cls:
        mock_cls.side_effect = PydanticValidationError.from_exception_data(
            title="Settings",
            input_type="python",
            line_errors=[
                {
                    "type": "missing",
                    "loc": ("github_token",),
                    "msg": "Field required",
                    "input": {},
                    "url": "https://errors.pydantic.dev/2.0/v/missing",
                }
            ],
        )
        result = runner.invoke(
            cli,
            ["extract", "--repo", "owner/repo"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    # Should contain config error hint, not a raw traceback
    assert "Configuration error" in combined or "GITHUB_TOKEN" in combined
