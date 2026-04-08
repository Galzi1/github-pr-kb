import json
from pathlib import Path

import pytest

from github_pr_kb.classifier import LEGACY_FAILURE_SUMMARY
from tests.support.phase7_uat_envs import run_scenario, setup_all

pytestmark = pytest.mark.e2e


def test_setup_all_creates_phase7_scenarios(tmp_path: Path) -> None:
    paths = setup_all(output_root=tmp_path)

    assert {path.name for path in paths} == {
        "classify-output",
        "generated-article",
        "generate-summary",
        "regenerate-safe",
    }
    assert (tmp_path / "classify-output" / ".github-pr-kb" / "cache" / "pr-1.json").exists()
    assert (tmp_path / "generated-article" / "scenario.json").exists()
    assert (tmp_path / "regenerate-safe" / "kb" / "gotcha" / "old-article.md").exists()


def test_run_classify_output_scenario(tmp_path: Path) -> None:
    env_dir, result = run_scenario("classify-output", output_root=tmp_path)

    assert result.exit_code == 0, result.output
    assert "Classified 1 new, 1 cached, 2 need review, 1 failed." in result.output

    index = json.loads(
        (env_dir / ".github-pr-kb" / "cache" / "classification-index.json").read_text(
            encoding="utf-8"
        )
    )
    assert all(
        entry.get("summary") != LEGACY_FAILURE_SUMMARY for entry in index.values()
    )


def test_run_generate_summary_scenario(tmp_path: Path) -> None:
    env_dir, result = run_scenario("generate-summary", output_root=tmp_path)

    assert result.exit_code == 0, result.output
    assert "Generated 1 new, 0 skipped, 1 filtered, 1 failed." in result.output
    assert "Warning: 1 article(s) failed synthesis." in (result.stderr or "")
    assert (env_dir / "kb" / "gotcha").is_dir()


def test_run_generated_article_scenario(tmp_path: Path) -> None:
    env_dir, result = run_scenario("generated-article", output_root=tmp_path)

    assert result.exit_code == 0, result.output
    article = (
        env_dir
        / "kb"
        / "gotcha"
        / "copy-request-context-before-mutation.md"
    ).read_text(encoding="utf-8")
    assert "## Symptom" in article
    assert "## Root Cause" in article
    assert "## Fix or Workaround" in article
    assert (
        "Always copy the request context before mutating it so handlers do not share state."
        not in article
    )


def test_run_regenerate_success_scenario(tmp_path: Path) -> None:
    env_dir, result = run_scenario("regenerate-safe", output_root=tmp_path)

    assert result.exit_code == 0, result.output
    assert "Generated 1 new, 0 skipped, 0 filtered, 0 failed." in result.output
    assert not (env_dir / "kb" / "gotcha" / "old-article.md").exists()
    manifest = json.loads((env_dir / "kb" / ".manifest.json").read_text(encoding="utf-8"))
    assert manifest == {"3101": "gotcha/new-regenerated-article.md"}


def test_run_regenerate_abort_scenario_preserves_existing_kb(tmp_path: Path) -> None:
    env_dir, result = run_scenario(
        "regenerate-safe",
        output_root=tmp_path,
        mode="abort",
    )

    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "Generation failed: staged generation failed" in combined
    assert (env_dir / "kb" / "gotcha" / "old-article.md").exists()
