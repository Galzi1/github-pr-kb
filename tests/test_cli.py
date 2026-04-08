"""CliRunner-based tests for the github-pr-kb CLI."""

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from github_pr_kb.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _classified_cache_dir(*paths: str) -> MagicMock:
    cache_dir = MagicMock()
    cache_dir.glob.return_value = [Path(path) for path in paths]
    return cache_dir


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
    assert "--regenerate" in result.output
    assert "--verbose" in result.output
    assert "Generate markdown" in result.output


def test_run_help(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    assert "--repo" in result.output
    assert "--verbose" in result.output
    assert "pipeline" in result.output.lower()


def test_extract_missing_repo(runner: CliRunner) -> None:
    result = runner.invoke(cli, ["extract"])
    assert result.exit_code == 2


def test_extract_bad_date(runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["extract", "--repo", "owner/repo", "--since", "not-a-date"],
        env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
    )
    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "ISO date" in combined


def test_extract_runs(runner: CliRunner) -> None:
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
    with patch("github_pr_kb.classifier.PRClassifier") as mock_cls:
        instance = mock_cls.return_value
        instance.classify_all.return_value = []
        instance.get_summary_counts.return_value = {
            "new": 3,
            "cached": 2,
            "need_review": 1,
            "failed": 0,
        }
        result = runner.invoke(
            cli,
            ["classify"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 0, result.output
    assert "Classified 3 new, 2 cached, 1 need review, 0 failed." in result.output
    assert "Classification complete:" not in result.output


def test_classify_review_label_matches_metric(runner: CliRunner) -> None:
    with patch("github_pr_kb.classifier.PRClassifier") as mock_cls:
        instance = mock_cls.return_value
        instance.classify_all.return_value = []
        instance.get_summary_counts.return_value = {
            "new": 0,
            "cached": 4,
            "need_review": 4,
            "failed": 1,
        }
        result = runner.invoke(
            cli,
            ["classify"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 0
    assert "4 need review" in result.output
    assert "new need review" not in result.output


def test_generate_runs(runner: CliRunner) -> None:
    from github_pr_kb.generator import GenerateResult

    with (
        patch("github_pr_kb.generator.DEFAULT_CACHE_DIR", _classified_cache_dir("classified-pr-1.json")),
        patch("github_pr_kb.generator.KBGenerator") as mock_cls,
    ):
        instance = mock_cls.return_value
        instance.generate_all.return_value = GenerateResult(
            written=5,
            skipped=2,
            filtered=3,
            failed=[],
        )
        result = runner.invoke(
            cli,
            ["generate"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 0, result.output
    assert "Generated 5 new, 2 skipped, 3 filtered, 0 failed." in result.output


def test_generate_regenerate_flag(runner: CliRunner) -> None:
    from github_pr_kb.generator import GenerateResult

    with (
        patch("github_pr_kb.generator.DEFAULT_CACHE_DIR", _classified_cache_dir("classified-pr-1.json")),
        patch("github_pr_kb.generator.KBGenerator") as mock_cls,
    ):
        instance = mock_cls.return_value
        instance.generate_all.return_value = GenerateResult(
            written=1,
            skipped=0,
            filtered=0,
            failed=[],
        )
        result = runner.invoke(
            cli,
            ["generate", "--regenerate"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 0, result.output
    instance.generate_all.assert_called_once_with(regenerate=True)


def test_generate_no_classified_input_exit_code(runner: CliRunner) -> None:
    with patch("github_pr_kb.generator.DEFAULT_CACHE_DIR", _classified_cache_dir()):
        result = runner.invoke(
            cli,
            ["generate"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "run `github-pr-kb classify` before `github-pr-kb generate`" in combined


def test_generate_missing_api_key(runner: CliRunner) -> None:
    with (
        patch("github_pr_kb.generator.DEFAULT_CACHE_DIR", _classified_cache_dir("classified-pr-1.json")),
        patch("github_pr_kb.generator.KBGenerator", side_effect=ValueError("ANTHROPIC_API_KEY is required for article generation.")),
    ):
        result = runner.invoke(
            cli,
            ["generate"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "ANTHROPIC_API_KEY for article generation" in combined


def test_generate_partial_failure_warning(runner: CliRunner) -> None:
    from github_pr_kb.generator import GenerateResult

    with (
        patch("github_pr_kb.generator.DEFAULT_CACHE_DIR", _classified_cache_dir("classified-pr-1.json")),
        patch("github_pr_kb.generator.KBGenerator") as mock_cls,
    ):
        instance = mock_cls.return_value
        instance.generate_all.return_value = GenerateResult(
            written=1,
            skipped=0,
            filtered=0,
            failed=[{"file": "gotcha/test.md", "reason": "APIError", "detail": "boom"}],
        )
        result = runner.invoke(
            cli,
            ["generate"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 0, result.output
    assert "Generated 1 new, 0 skipped, 0 filtered, 1 failed." in result.output
    assert "Warning: 1 article(s) failed synthesis." in (result.stderr or "")


def test_generate_total_failure_exit_code(runner: CliRunner) -> None:
    from github_pr_kb.generator import GenerateResult

    with (
        patch("github_pr_kb.generator.DEFAULT_CACHE_DIR", _classified_cache_dir("classified-pr-1.json")),
        patch("github_pr_kb.generator.KBGenerator") as mock_cls,
    ):
        instance = mock_cls.return_value
        instance.generate_all.return_value = GenerateResult(
            written=0,
            skipped=0,
            filtered=0,
            failed=[{"file": "gotcha/test.md", "reason": "APIError", "detail": "boom"}],
        )
        result = runner.invoke(
            cli,
            ["generate"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "no output was produced" in combined


def test_generate_unexpected_exception_surfaces_clear_error(runner: CliRunner) -> None:
    with (
        patch("github_pr_kb.generator.DEFAULT_CACHE_DIR", _classified_cache_dir("classified-pr-1.json")),
        patch("github_pr_kb.generator.KBGenerator") as mock_cls,
    ):
        instance = mock_cls.return_value
        instance.generate_all.side_effect = RuntimeError("staged generation failed")
        result = runner.invoke(
            cli,
            ["generate", "--regenerate"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "Generation failed: staged generation failed" in combined


def test_generate_unrelated_value_error_not_rewritten(runner: CliRunner) -> None:
    with (
        patch("github_pr_kb.generator.DEFAULT_CACHE_DIR", _classified_cache_dir("classified-pr-1.json")),
        patch("github_pr_kb.generator.KBGenerator", side_effect=ValueError("bad threshold")),
    ):
        result = runner.invoke(
            cli,
            ["generate"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "bad threshold" in combined
    assert "ANTHROPIC_API_KEY for article generation" not in combined


def test_run_pipelines(runner: CliRunner) -> None:
    from github_pr_kb.generator import GenerateResult

    with (
        patch("github_pr_kb.extractor.GitHubExtractor") as mock_extract_cls,
        patch("github_pr_kb.classifier.PRClassifier") as mock_classify_cls,
        patch("github_pr_kb.generator.DEFAULT_CACHE_DIR", _classified_cache_dir("classified-pr-1.json")),
        patch("github_pr_kb.generator.KBGenerator") as mock_generate_cls,
    ):
        ext_inst = mock_extract_cls.return_value
        ext_inst.extract.return_value = []

        cls_inst = mock_classify_cls.return_value
        cls_inst.classify_all.return_value = []
        cls_inst.get_summary_counts.return_value = {
            "new": 2,
            "cached": 1,
            "need_review": 1,
            "failed": 0,
        }

        gen_inst = mock_generate_cls.return_value
        gen_inst.generate_all.return_value = GenerateResult(
            written=3,
            skipped=0,
            filtered=0,
            failed=[],
        )

        result = runner.invoke(
            cli,
            ["run", "--repo", "owner/repo"],
            env={"GITHUB_TOKEN": "fake", "ANTHROPIC_API_KEY": "fake"},
        )

    assert result.exit_code == 0, result.output
    assert "Extracted" in result.output
    assert "Classified 2 new, 1 cached, 1 need review, 0 failed." in result.output
    assert "Generated 3 new, 0 skipped, 0 filtered, 0 failed." in result.output
    gen_inst.generate_all.assert_called_once_with(regenerate=False)


def test_run_fails_fast(runner: CliRunner) -> None:
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
    mock_classify_cls.assert_not_called()
    mock_generate_cls.assert_not_called()


def test_extract_missing_token(runner: CliRunner) -> None:
    from pydantic import ValidationError as PydanticValidationError

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
    assert "Configuration error" in combined or "GITHUB_TOKEN" in combined


def test_cli_contract_matches_upstream_interfaces() -> None:
    from github_pr_kb.classifier import PRClassifier
    from github_pr_kb.generator import GenerateResult, KBGenerator

    assert "filtered" in GenerateResult.model_fields
    assert "regenerate" in inspect.signature(KBGenerator.generate_all).parameters
    assert hasattr(PRClassifier, "get_summary_counts")
