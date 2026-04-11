"""Workflow decision helper for GitHub Action skip/cursor logic.

This module is intentionally stdlib-only and import-safe: it does not import
repo settings or any other env-bound surfaces, so workflow consumers can run
`python -m github_pr_kb.action_state` before any repository secrets or local
CLI configuration are available.

`next_cursor` is a candidate value only. The workflow must persist it
monotonically against the freshest repository variable value after successful
publication so overlapping runs cannot move state backward.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

TimestampInput = datetime | str | None


@dataclass(frozen=True, slots=True)
class ActionRunDecision:
    should_run: bool
    extract_since: str | None
    next_cursor: str | None
    reason: str

    def to_json_dict(self) -> dict[str, bool | str | None]:
        return asdict(self)


def _normalize_timestamp(value: TimestampInput, field_name: str) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO-8601 timestamp with timezone") from exc

    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp with timezone")
    return dt.astimezone(timezone.utc)


def _isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def decide_action_run(
    *,  # keyword-only: all arguments below must be passed by name
    event_name: str,
    merged: bool = False,
    event_updated_at: TimestampInput = None,
    stored_cursor: TimestampInput = None,
    latest_merged_at: TimestampInput = None,
    manual_since: TimestampInput = None,
    force: bool = False,
) -> ActionRunDecision:
    """Decide whether the workflow should run and which cursor values to emit.

    Auto merged-event path:
    - compare `event_updated_at` to `stored_cursor`
    - use `stored_cursor` as `extract_since`
    - emit `event_updated_at` as the next successful cursor candidate

    Manual workflow-dispatch path:
    - use `manual_since` if provided, otherwise `stored_cursor`, as `extract_since`
    - unless forced, skip when `latest_merged_at` is not newer than that effective cursor
    - emit `max(stored_cursor, manual_since, latest_merged_at)` as the next cursor candidate
    """

    stored = _normalize_timestamp(stored_cursor, "--stored-cursor")
    manual = _normalize_timestamp(manual_since, "--manual-since")
    latest = _normalize_timestamp(latest_merged_at, "--latest-merged-at")
    event_updated = _normalize_timestamp(event_updated_at, "--event-updated-at")

    if event_name == "pull_request":
        if not merged:
            return ActionRunDecision(
                should_run=False,
                extract_since=_isoformat_utc(stored),
                next_cursor=_isoformat_utc(stored),
                reason="pull_request_not_merged",
            )
        if event_updated is None:
            raise ValueError("--event-updated-at is required for merged pull_request events")
        if stored is not None and event_updated <= stored:
            return ActionRunDecision(
                should_run=False,
                extract_since=_isoformat_utc(stored),
                next_cursor=_isoformat_utc(max(stored, event_updated)),
                reason="already_processed_auto_event",
            )
        return ActionRunDecision(
            should_run=True,
            extract_since=_isoformat_utc(stored),
            next_cursor=_isoformat_utc(event_updated),
            reason="new_merged_pr_event",
        )

    if event_name != "workflow_dispatch":
        raise ValueError("--event-name must be pull_request or workflow_dispatch")

    effective_cursor = manual if manual is not None else stored
    cursor_candidates = [dt for dt in (stored, manual, latest) if dt is not None]
    next_cursor = max(cursor_candidates) if cursor_candidates else None

    if force:
        return ActionRunDecision(
            should_run=True,
            extract_since=_isoformat_utc(effective_cursor),
            next_cursor=_isoformat_utc(next_cursor),
            reason="forced_manual_run",
        )

    if latest is None:
        return ActionRunDecision(
            should_run=False,
            extract_since=_isoformat_utc(effective_cursor),
            next_cursor=_isoformat_utc(next_cursor),
            reason="no_new_closed_prs",
        )

    if effective_cursor is not None and latest <= effective_cursor:
        return ActionRunDecision(
            should_run=False,
            extract_since=_isoformat_utc(effective_cursor),
            next_cursor=_isoformat_utc(next_cursor),
            reason="no_new_closed_prs",
        )

    return ActionRunDecision(
        should_run=True,
        extract_since=_isoformat_utc(effective_cursor),
        next_cursor=_isoformat_utc(next_cursor),
        reason="new_closed_prs_available",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Emit workflow skip/cursor decisions as JSON.")
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--merged", action="store_true")
    parser.add_argument("--event-updated-at")
    parser.add_argument("--stored-cursor")
    parser.add_argument("--latest-merged-at")
    parser.add_argument("--manual-since")
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        decision = decide_action_run(
            event_name=args.event_name,
            merged=args.merged,
            event_updated_at=args.event_updated_at,
            stored_cursor=args.stored_cursor,
            latest_merged_at=args.latest_merged_at,
            manual_since=args.manual_since,
            force=args.force,
        )
    except ValueError as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(decision.to_json_dict()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
