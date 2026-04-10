import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from github_pr_kb.action_state import decide_action_run


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def test_merged_pr_event_uses_event_updated_at() -> None:
    decision = decide_action_run(
        event_name="pull_request",
        merged=True,
        event_updated_at=_dt("2026-04-10T12:00:00Z"),
        stored_cursor=_dt("2026-04-09T12:00:00Z"),
    )

    assert decision.should_run is True
    assert decision.extract_since == "2026-04-09T12:00:00Z"
    assert decision.next_cursor == "2026-04-10T12:00:00Z"
    assert decision.reason == "new_merged_pr_event"


def test_repeated_auto_event_is_no_op_when_cursor_matches() -> None:
    decision = decide_action_run(
        event_name="pull_request",
        merged=True,
        event_updated_at=_dt("2026-04-10T12:00:00Z"),
        stored_cursor=_dt("2026-04-10T12:00:00Z"),
    )

    assert decision.should_run is False
    assert decision.extract_since == "2026-04-10T12:00:00Z"
    assert decision.next_cursor == "2026-04-10T12:00:00Z"
    assert decision.reason == "already_processed_auto_event"


def test_manual_dispatch_skips_when_cursor_is_current() -> None:
    decision = decide_action_run(
        event_name="workflow_dispatch",
        stored_cursor=_dt("2026-04-10T12:00:00Z"),
        latest_merged_at=_dt("2026-04-10T11:00:00Z"),
    )

    assert decision.should_run is False
    assert decision.extract_since == "2026-04-10T12:00:00Z"
    assert decision.next_cursor == "2026-04-10T12:00:00Z"
    assert decision.reason == "no_new_closed_prs"


def test_manual_since_override_wins_over_stored_cursor() -> None:
    decision = decide_action_run(
        event_name="workflow_dispatch",
        stored_cursor=_dt("2026-04-10T12:00:00Z"),
        latest_merged_at=_dt("2026-04-12T09:00:00Z"),
        manual_since=_dt("2026-04-01T00:00:00Z"),
    )

    assert decision.should_run is True
    assert decision.extract_since == "2026-04-01T00:00:00Z"
    assert decision.next_cursor == "2026-04-12T09:00:00Z"
    assert decision.reason == "new_closed_prs_available"


def test_manual_next_cursor_never_regresses_past_stored_cursor() -> None:
    decision = decide_action_run(
        event_name="workflow_dispatch",
        stored_cursor=_dt("2026-04-15T12:00:00Z"),
        latest_merged_at=_dt("2026-04-12T09:00:00Z"),
        manual_since=_dt("2026-04-01T00:00:00Z"),
    )

    assert decision.should_run is True
    assert decision.extract_since == "2026-04-01T00:00:00Z"
    assert decision.next_cursor == "2026-04-15T12:00:00Z"
    assert decision.reason == "new_closed_prs_available"


def test_force_manual_run_bypasses_no_new_pr_guard() -> None:
    decision = decide_action_run(
        event_name="workflow_dispatch",
        stored_cursor=_dt("2026-04-10T12:00:00Z"),
        latest_merged_at=_dt("2026-04-10T11:00:00Z"),
        manual_since=_dt("2026-04-05T00:00:00Z"),
        force=True,
    )

    assert decision.should_run is True
    assert decision.extract_since == "2026-04-05T00:00:00Z"
    assert decision.next_cursor == "2026-04-10T12:00:00Z"
    assert decision.reason == "forced_manual_run"


def test_action_state_cli_runs_without_repo_or_api_secrets() -> None:
    env = os.environ.copy()
    env.pop("GITHUB_TOKEN", None)
    env.pop("ANTHROPIC_API_KEY", None)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "github_pr_kb.action_state",
            "--event-name",
            "workflow_dispatch",
            "--latest-merged-at",
            "2026-04-10T12:00:00Z",
            "--manual-since",
            "2026-04-01T00:00:00Z",
        ],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload == {
        "should_run": True,
        "extract_since": "2026-04-01T00:00:00Z",
        "next_cursor": "2026-04-10T12:00:00Z",
        "reason": "new_closed_prs_available",
    }


def test_action_state_cli_rejects_malformed_timestamp_input() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "github_pr_kb.action_state",
            "--event-name",
            "pull_request",
            "--merged",
            "--event-updated-at",
            "not-a-timestamp",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "Invalid input: --event-updated-at must be an ISO-8601 timestamp with timezone" in result.stderr
