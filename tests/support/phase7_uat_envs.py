"""Build and run deterministic UAT environments for Phase 7."""

from __future__ import annotations

import argparse
import contextlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import anthropic
import httpx
from click.testing import CliRunner, Result

from github_pr_kb.classifier import body_hash
from github_pr_kb.cli import cli
from github_pr_kb.models import (
    ClassifiedComment,
    ClassifiedFile,
    CommentRecord,
    PRFile,
    PRRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "tests" / "uat" / "phase7" / "envs"
_NOW = datetime(2026, 4, 8, 9, 20, 52, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Scenario:
    name: str
    uat_test_number: int
    test_name: str
    command: list[str]
    expected: str


SCENARIOS: dict[str, Scenario] = {
    "classify-output": Scenario(
        name="classify-output",
        uat_test_number=1,
        test_name="Classify output reflects real outcomes",
        command=["classify"],
        expected="Classified 1 new, 1 cached, 2 need review, 1 failed.",
    ),
    "generated-article": Scenario(
        name="generated-article",
        uat_test_number=2,
        test_name="Generated article is synthesized instead of copied",
        command=["generate"],
        expected="Generated 1 new, 0 skipped, 0 filtered, 0 failed.",
    ),
    "generate-summary": Scenario(
        name="generate-summary",
        uat_test_number=3,
        test_name="Generate summary reports filtered and failed counts honestly",
        command=["generate"],
        expected="Generated 1 new, 0 skipped, 1 filtered, 1 failed.",
    ),
    "regenerate-safe": Scenario(
        name="regenerate-safe",
        uat_test_number=4,
        test_name="Regenerate rebuilds safely",
        command=["generate", "--regenerate"],
        expected="Generated 1 new, 0 skipped, 0 filtered, 0 failed.",
    ),
}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _comment_url(pr_number: int, comment_id: int) -> str:
    return f"https://github.com/test/repo/pull/{pr_number}#comment-{comment_id}"


def _pr_url(pr_number: int) -> str:
    return f"https://github.com/test/repo/pull/{pr_number}"


def _write_pr_file(
    env_dir: Path,
    *,
    pr_number: int,
    title: str,
    comment_id: int,
    body: str,
    comment_type: str = "review",
    author: str = "reviewer",
    diff_hunk: str | None = None,
) -> None:
    pr = PRRecord(
        number=pr_number,
        title=title,
        state="closed",
        url=_pr_url(pr_number),
    )
    comment = CommentRecord(
        comment_id=comment_id,
        comment_type=comment_type,
        author=author,
        body=body,
        created_at=_NOW,
        url=_comment_url(pr_number, comment_id),
        diff_hunk=diff_hunk,
    )
    pr_file = PRFile(pr=pr, comments=[comment], extracted_at=_NOW)
    _write_json(
        env_dir / ".github-pr-kb" / "cache" / f"pr-{pr_number}.json",
        pr_file.model_dump(mode="json"),
    )


def _write_classified_file(
    env_dir: Path,
    *,
    pr_number: int,
    title: str,
    comment_id: int,
    category: str,
    confidence: float,
    summary: str,
    needs_review: bool,
) -> None:
    pr = PRRecord(
        number=pr_number,
        title=title,
        state="closed",
        url=_pr_url(pr_number),
    )
    classified = ClassifiedComment(
        comment_id=comment_id,
        category=category,
        confidence=confidence,
        summary=summary,
        classified_at=_NOW,
        needs_review=needs_review,
    )
    classified_file = ClassifiedFile(
        pr=pr,
        classifications=[classified],
        classified_at=_NOW,
    )
    _write_json(
        env_dir / ".github-pr-kb" / "cache" / f"classified-pr-{pr_number}.json",
        classified_file.model_dump(mode="json"),
    )


def _write_env_file(env_dir: Path) -> None:
    _write_text(
        env_dir / ".env",
        "\n".join(
            [
                "GITHUB_TOKEN=ghp_test000000000000000000000000000fake",
                "ANTHROPIC_API_KEY=sk-ant-test000000000000000000000000000fake",
                "KB_OUTPUT_DIR=kb",
                "",
            ]
        ),
    )


def _write_scenario_metadata(env_dir: Path, scenario: Scenario) -> None:
    _write_json(
        env_dir / "scenario.json",
        {
            "scenario": scenario.name,
            "uat_test_number": scenario.uat_test_number,
            "test_name": scenario.test_name,
            "command": scenario.command,
            "expected": scenario.expected,
        },
    )


def _materialize_classify_output(env_dir: Path, scenario: Scenario) -> None:
    cached_body = "Cache this low confidence review insight."
    fresh_low_confidence_body = "Fresh low confidence review should still count as review."
    malformed_body = "This review response will be malformed on purpose."

    _write_pr_file(
        env_dir,
        pr_number=1,
        title="Cached review PR",
        comment_id=101,
        body=cached_body,
    )
    _write_pr_file(
        env_dir,
        pr_number=2,
        title="Fresh review PR",
        comment_id=202,
        body=fresh_low_confidence_body,
    )
    _write_pr_file(
        env_dir,
        pr_number=3,
        title="Malformed review PR",
        comment_id=303,
        body=malformed_body,
    )

    _write_json(
        env_dir / ".github-pr-kb" / "cache" / "classification-index.json",
        {
            body_hash(cached_body): {
                "category": "gotcha",
                "confidence": 0.60,
                "summary": "Cached low confidence review insight",
                "classified_at": _NOW.isoformat(),
            },
            "stale-failed-entry": {
                "category": "other",
                "confidence": 0.0,
                "summary": "classification failed",
                "classified_at": _NOW.isoformat(),
            },
        },
    )
    _write_scenario_metadata(env_dir, scenario)


def _materialize_generated_article(env_dir: Path, scenario: Scenario) -> None:
    source_body = (
        "Always copy the request context before mutating it so handlers do not share state."
    )
    _write_pr_file(
        env_dir,
        pr_number=11,
        title="Context safety improvements",
        comment_id=1101,
        body=source_body,
        diff_hunk="@@ -10,1 +10,1 @@\n-ctx.user = user\n+ctx = ctx.copy(update={'user': user})",
    )
    _write_classified_file(
        env_dir,
        pr_number=11,
        title="Context safety improvements",
        comment_id=1101,
        category="gotcha",
        confidence=0.91,
        summary="Copy request context before mutation",
        needs_review=False,
    )
    _write_scenario_metadata(env_dir, scenario)


def _materialize_generate_summary(env_dir: Path, scenario: Scenario) -> None:
    _write_pr_file(
        env_dir,
        pr_number=21,
        title="One successful article",
        comment_id=2101,
        body="This article should generate successfully.",
        diff_hunk=None,
    )
    _write_classified_file(
        env_dir,
        pr_number=21,
        title="One successful article",
        comment_id=2101,
        category="gotcha",
        confidence=0.95,
        summary="Successful synthesized article",
        needs_review=False,
    )

    _write_pr_file(
        env_dir,
        pr_number=22,
        title="Filtered article",
        comment_id=2201,
        body="This item is too low confidence to generate.",
        diff_hunk=None,
    )
    _write_classified_file(
        env_dir,
        pr_number=22,
        title="Filtered article",
        comment_id=2201,
        category="other",
        confidence=0.20,
        summary="Filtered out low confidence article",
        needs_review=True,
    )

    _write_pr_file(
        env_dir,
        pr_number=23,
        title="Failed article",
        comment_id=2301,
        body="This item should trigger a synthesis failure.",
        diff_hunk=None,
    )
    _write_classified_file(
        env_dir,
        pr_number=23,
        title="Failed article",
        comment_id=2301,
        category="code_pattern",
        confidence=0.90,
        summary="This synthesis will fail",
        needs_review=False,
    )
    _write_scenario_metadata(env_dir, scenario)


def _materialize_regenerate_safe(env_dir: Path, scenario: Scenario) -> None:
    _write_pr_file(
        env_dir,
        pr_number=31,
        title="Regenerated article",
        comment_id=3101,
        body="Fresh regenerate content should replace the old KB entry.",
        diff_hunk=None,
    )
    _write_classified_file(
        env_dir,
        pr_number=31,
        title="Regenerated article",
        comment_id=3101,
        category="gotcha",
        confidence=0.93,
        summary="New regenerated article",
        needs_review=False,
    )

    _write_text(
        env_dir / "kb" / "gotcha" / "old-article.md",
        "---\ncomment_id: 999\n---\n\n# Old article\n\nThis should be replaced.\n",
    )
    _write_json(
        env_dir / "kb" / ".manifest.json",
        {"999": "gotcha/old-article.md"},
    )
    _write_text(env_dir / "kb" / "INDEX.md", "# Old Index\n")
    _write_scenario_metadata(env_dir, scenario)


def setup_scenario(name: str, output_root: Path = DEFAULT_OUTPUT_ROOT) -> Path:
    scenario = SCENARIOS[name]
    env_dir = output_root / scenario.name
    if env_dir.exists():
        shutil.rmtree(env_dir)
    env_dir.mkdir(parents=True, exist_ok=True)
    _write_env_file(env_dir)

    if name == "classify-output":
        _materialize_classify_output(env_dir, scenario)
    elif name == "generated-article":
        _materialize_generated_article(env_dir, scenario)
    elif name == "generate-summary":
        _materialize_generate_summary(env_dir, scenario)
    elif name == "regenerate-safe":
        _materialize_regenerate_safe(env_dir, scenario)
    else:
        raise ValueError(f"Unknown scenario: {name}")

    return env_dir


def setup_all(output_root: Path = DEFAULT_OUTPUT_ROOT) -> list[Path]:
    return [setup_scenario(name, output_root=output_root) for name in SCENARIOS]


def _classify_anthropic_factory():
    class FakeAnthropicClient:
        def __init__(self, *args, **kwargs) -> None:
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            prompt = kwargs["messages"][0]["content"]
            if "Fresh low confidence review" in prompt:
                return SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            type="text",
                            text=json.dumps(
                                {
                                    "category": "gotcha",
                                    "confidence": 0.61,
                                    "summary": "Fresh low confidence review insight",
                                }
                            ),
                        )
                    ]
                )
            if "malformed on purpose" in prompt:
                return SimpleNamespace(
                    content=[SimpleNamespace(type="text", text="NOT VALID JSON {{{")]
                )
            raise AssertionError(f"Unexpected classify prompt: {prompt}")

    return FakeAnthropicClient


def _generate_anthropic_factory(scenario_name: str):
    class FakeAnthropicClient:
        def __init__(self, *args, **kwargs) -> None:
            self.messages = SimpleNamespace(create=self._create)

        def _create(self, **kwargs):
            prompt = kwargs["messages"][0]["content"]
            if scenario_name == "generated-article":
                return SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            type="text",
                            text=(
                                "## Symptom\nState leaks between handlers.\n\n"
                                "## Root Cause\nThe shared context object is mutated directly.\n\n"
                                "## Fix or Workaround\nClone the context before applying per-request changes."
                            ),
                        )
                    ]
                )
            if scenario_name == "generate-summary":
                if "trigger a synthesis failure" in prompt:
                    raise anthropic.APIError(
                        "forced synthesis failure",
                        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
                        body=None,
                    )
                return SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            type="text",
                            text=(
                                "## Symptom\nGenerated successfully.\n\n"
                                "## Root Cause\nNot stated in the source comment.\n\n"
                                "## Fix or Workaround\nCapture the pattern in the KB."
                            ),
                        )
                    ]
                )
            if scenario_name == "regenerate-safe":
                return SimpleNamespace(
                    content=[
                        SimpleNamespace(
                            type="text",
                            text=(
                                "## Symptom\nOld KB content is outdated.\n\n"
                                "## Root Cause\nThe previous article predates the new synthesis prompt.\n\n"
                                "## Fix or Workaround\nRegenerate the KB from the classified cache."
                            ),
                        )
                    ]
                )
            raise AssertionError(f"Unexpected generate scenario: {scenario_name}")

    return FakeAnthropicClient


def run_scenario(
    name: str,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    *,
    mode: str = "success",
) -> tuple[Path, Result]:
    env_dir = setup_scenario(name, output_root=output_root)
    scenario = SCENARIOS[name]
    runner = CliRunner()
    env = {
        "GITHUB_TOKEN": "ghp_test000000000000000000000000000fake",
        "ANTHROPIC_API_KEY": "sk-ant-test000000000000000000000000000fake",
        "KB_OUTPUT_DIR": "kb",
    }

    patch_stack = contextlib.ExitStack()
    try:
        if name == "classify-output":
            patch_stack.enter_context(
                patch("github_pr_kb.classifier.Anthropic", _classify_anthropic_factory())
            )
        else:
            patch_stack.enter_context(
                patch(
                    "github_pr_kb.generator.Anthropic",
                    _generate_anthropic_factory(name),
                )
            )
            if name == "regenerate-safe" and mode == "abort":
                from github_pr_kb.generator import KBGenerator

                original_generate_index = KBGenerator._generate_index
                live_kb_dir = env_dir / "kb"

                def explode_during_staging(self) -> None:
                    if self._kb_dir != live_kb_dir:
                        raise RuntimeError("staged generation failed")
                    original_generate_index(self)

                patch_stack.enter_context(
                    patch.object(KBGenerator, "_generate_index", explode_during_staging)
                )

        with contextlib.chdir(env_dir):
            result = runner.invoke(
                cli,
                scenario.command,
                env=env,
                catch_exceptions=True,
            )
    finally:
        patch_stack.close()

    return env_dir, result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build and run deterministic UAT environments for Phase 7.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List available scenarios")
    list_parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Directory where environments are created",
    )

    setup_parser = subparsers.add_parser("setup", help="Materialize scenario environments")
    setup_parser.add_argument(
        "scenario",
        choices=[*SCENARIOS.keys(), "all"],
        help="Scenario name or 'all'",
    )
    setup_parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Directory where environments are created",
    )

    run_parser = subparsers.add_parser("run", help="Materialize and run a scenario")
    run_parser.add_argument("scenario", choices=SCENARIOS.keys(), help="Scenario name")
    run_parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Directory where environments are created",
    )
    run_parser.add_argument(
        "--mode",
        choices=["success", "abort"],
        default="success",
        help="Execution mode for scenarios that support multiple paths",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    output_root = Path(args.output_root)

    if args.command == "list":
        print(f"Output root: {output_root}")
        for scenario in SCENARIOS.values():
            print(
                f"- {scenario.name}: test {scenario.uat_test_number} -> "
                f"{scenario.test_name}"
            )
        return 0

    if args.command == "setup":
        paths = (
            setup_all(output_root=output_root)
            if args.scenario == "all"
            else [setup_scenario(args.scenario, output_root=output_root)]
        )
        for path in paths:
            print(path)
        return 0

    env_dir, result = run_scenario(
        args.scenario,
        output_root=output_root,
        mode=args.mode,
    )
    print(f"Environment: {env_dir}")
    print("--- stdout ---")
    print(result.output.rstrip())
    if result.stderr:
        print("--- stderr ---")
        print(result.stderr.rstrip())
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
