import json
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "github-pr-kb.yml"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def _assert_pinned_action(text: str, action: str) -> None:
    pattern = rf"uses:\s+{re.escape(action)}@[0-9a-f]{{40}}(?:\s+#.*)?"
    assert re.search(pattern, text), f"{action} must be pinned by full commit SHA"


def test_workflow_has_merged_pr_and_dispatch_triggers() -> None:
    text = _workflow_text()

    assert "pull_request:" in text
    assert "types: [closed]" in text
    assert "workflow_dispatch:" in text
    assert "since:" in text
    assert "force:" in text
    assert "schedule:" not in text
    assert "github.event.pull_request.merged == true" in text
    assert "concurrency:" in text
    assert "cancel-in-progress: false" in text
    assert "KB_LAST_SUCCESSFUL_CURSOR" in text


def test_workflow_bootstraps_tool_checkout_for_copyable_repos() -> None:
    text = _workflow_text()

    assert "KB_TOOL_REPOSITORY" in text
    assert "KB_TOOL_REF" in text
    assert "galzi/github-pr-kb" in text
    assert "refs/heads/main" not in text
    assert "KB_TOOL_REF: main" not in text
    assert "KB_TOOL_REF: master" not in text
    assert "uv sync --project .github-pr-kb-tool --all-groups --frozen" in text
    assert "uv run --project .github-pr-kb-tool python -m github_pr_kb.action_state" in text
    assert "uv run --project .github-pr-kb-tool github-pr-kb extract" in text
    assert "uv run --project .github-pr-kb-tool github-pr-kb classify" in text
    assert "uv run --project .github-pr-kb-tool github-pr-kb generate" in text
    assert ".github-pr-kb/cache/" in text
    assert "--event-updated-at" in text
    assert "--stored-cursor" in text
    assert "--latest-merged-at" in text
    assert "--manual-since" in text
    assert "--force" in text
    assert "already_processed_auto_event" in text
    assert "GITHUB_TOKEN:" in text
    assert "ANTHROPIC_API_KEY:" in text
    assert "GH_TOKEN:" in text
    assert "KB_VARIABLES_TOKEN" in text
    assert "KB_VARIABLES_APP_ID" in text
    assert "KB_VARIABLES_APP_PRIVATE_KEY" in text
    assert "if: ${{ secrets." not in text
    assert "env.KB_VARIABLES_TOKEN" in text
    assert "env.KB_VARIABLES_APP_ID" in text
    assert "actions/create-github-app-token" in text

    for action in (
        "actions/checkout",
        "astral-sh/setup-uv",
        "actions/cache",
        "actions/upload-artifact",
        "actions/create-github-app-token",
    ):
        _assert_pinned_action(text, action)


def test_workflow_publishes_rolling_pr_and_persists_cursor_monotonically() -> None:
    text = _workflow_text()

    assert "automation/github-pr-kb" in text
    assert "chore: update PR knowledge base" in text
    assert "gh api" in text
    assert "gh pr" in text
    assert "kb/INDEX.md" in text
    assert "kb/.manifest.json" in text
    assert ":(glob)kb/**/*.md" in text
    git_add_line = next(line for line in text.splitlines() if "git add --" in line)
    assert ".github-pr-kb/cache" not in git_add_line
    assert "actions/variables/${KB_VARIABLE_NAME}" in text
    assert "KB_LAST_SUCCESSFUL_CURSOR" in text
    assert "max(" in text or "python - <<'PY'" in text


def test_action_state_helper_command_runs_from_project_checkout() -> None:
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(REPO_ROOT),
            "python",
            "-m",
            "github_pr_kb.action_state",
            "--event-name",
            "pull_request",
            "--merged",
            "--event-updated-at",
            "2026-04-10T12:00:00Z",
            "--stored-cursor",
            "2026-04-09T12:00:00Z",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload) == {"should_run", "extract_since", "next_cursor", "reason"}
    assert payload["should_run"] is True
